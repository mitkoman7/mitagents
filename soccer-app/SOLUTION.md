# Soccer AI — Multi-Agent Prediction System

## Overview

A Flask + React application that predicts football match outcomes using a **5-agent LangGraph pipeline** powered by Azure OpenAI o4-mini.

```
User question
     │
     ▼
┌─────────────┐
│ Orchestrator│  extracts team names, fetches web context + last-5 form for each team
└──────┬──────┘
       │
       ▼ (parallel via ThreadPoolExecutor)
┌──────┴────────────────────────────────────────────┐
│  ⚽ 1X2 Agent  🎯 Goals Agent  🔺 Corners Agent  🃏 Cards Agent │
│  (each searches web, analyses, returns JSON)       │
└──────┬────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ Synthesizer │  reads all 4 JSON reports, picks highest confidence_score
└─────────────┘
       │
       ▼
  Final prediction streamed to UI via SSE
```

---

## Architecture

### Backend (`soccer-app/`)

| File | Role |
|------|------|
| `app.py` | Flask API — `/api/chat` (SSE), `/api/fixtures`, `/api/predictions` CRUD, `/api/health` |
| `multi_agent.py` | LangGraph graph: 5 nodes, ThreadPoolExecutor parallel specialists, Queue-based SSE streaming |
| `tools.py` | Shared tools: `web_search`, `team_form`, `get_fixtures`, ESPN/TheSportsDB helpers |

### Frontend (`react-ui/`)

| File | Role |
|------|------|
| `src/App.jsx` | Main chat UI — SSE streaming, competition fixture tabs, per-agent live indicator |
| `src/components/ChatMessage.jsx` | Message bubbles — parses prediction JSON, `💾 Save` button |
| `src/components/StatsPanel.jsx` | Prediction tracker — Won/Lost balance, streak, history |
| `src/App.css` | Dark pitch theme, per-agent colour coding |

Built output → `static/react/` (served by Flask).

---

## Agent Pipeline (`multi_agent.py`)

### State

```python
class MatchState(TypedDict):
    question:       str
    base_context:   str          # populated by orchestrator
    report_1x2:     str          # JSON from 1X2 agent
    report_goals:   str          # JSON from Goals agent
    report_corners: str          # JSON from Corners agent
    report_cards:   str          # JSON from Cards agent
    final_answer:   str          # final markdown from synthesizer
    activities:     Annotated[list, operator.add]
    _queue:         Any          # threading.Queue for SSE — never merged by LangGraph
```

### Node 1 — Orchestrator
- Calls o4-mini to extract team names from the question (`max_completion_tokens=1000`)
- Falls back to regex split on `vs` if LLM returns empty
- Fetches: `web_search(team_a vs team_b ...)` + `team_form(team_a)` + `team_form(team_b)`
- `team_form` uses TheSportsDB free API (key=3) → last **5 matches** per team

### Node 2 — Parallel Specialists
Four agents run concurrently via `ThreadPoolExecutor(max_workers=4)`:

| Agent | Market | Extra searches |
|-------|--------|---------------|
| 1X2 | Home/Draw/Away | H2H record, home/away win rate |
| Goals | Over/Under 2.5, BTTS | Goals scored/conceded stats, BTTS history |
| Corners | Over/Under 9.5 corners | Avg corners/game (low confidence if no real stats) |
| Cards | Over/Under 3.5 cards | Avg bookings/game, referee tendency |

Each specialist returns JSON:
```json
{"market":"1X2","bet":"Away Win","probability":"55%","confidence_score":7,"reasoning":"..."}
```

### Node 3 — Synthesizer
- Reads all 4 JSON reports
- Picks market with highest `confidence_score`
- Returns formatted markdown with best bet, probability, form summary, and runner-up markets

---

## Web Search (`tools.py`)

1. **DuckDuckGo HTML scraping** (primary) — no API key needed
2. **Google News RSS** (fallback) — used when DDG returns 202 / bot-detection

```python
def web_search(query: str, max_results: int = 6) -> str:
    results = _ddg_search(query, max_results) or _gnews_search(query, max_results)
```

---

## Fixtures (`/api/fixtures`)

Chain of fallbacks:
1. **ESPN scoreboard API** (`site.api.espn.com`) — no key, today's games only
2. **TheSportsDB** `eventsday.php` — free API key=3
3. **web_search** — last resort, returns raw text

Competition tabs: Europa League, Champions League, Conference League, Premier League, La Liga, Bundesliga.

---

## SSE Streaming

Flask streams events to the React UI using Server-Sent Events:

```
data: {"type":"activity","agent":"orchestrator","query":"Collecting base data…"}
data: {"type":"activity","agent":"1x2","query":"⚽ 1X2 Agent: searching…"}
...
data: {"type":"done","reply":"🎯 BEST BET: ...","activities":[...],"reports":{...}}
```

Pattern — `threading.Thread + Queue` so Flask can yield while LangGraph runs in background:

```python
q = Queue()
t = threading.Thread(target=lambda: run_prediction(msg, event_callback=lambda e: q.put(e)))
t.start()
while True:
    event = q.get(timeout=180)
    if event["type"] == "__done__": break
    yield f"data: {json.dumps(event)}\n\n"
```

---

## Prediction Tracker

- Saved to `predictions.json` (file-based, no DB needed)
- REST endpoints: `GET/POST /api/predictions`, `PATCH/DELETE /api/predictions/<id>`
- Frontend: `StatsPanel.jsx` shows Won/Lost balance, win %, 🔥 streak, full history

---

## Key Lessons / Bugs Fixed

### o4-mini requires large `max_completion_tokens`
o4-mini uses hidden reasoning tokens **before** writing output. With `max_completion_tokens=500`, all tokens were consumed by internal thinking → `content = null` → empty response.

| Call | Tokens |
|------|--------|
| Team extraction | 1 000 |
| Each specialist | 4 000 |
| Synthesizer | 8 000 |

### Team name extraction fallback
If the LLM returns malformed/empty JSON, a regex splits on `" vs "`:
```python
parts = re.split(r'\s+vs\.?\s+|\s+v\.?\s+', question, maxsplit=1, flags=re.IGNORECASE)
```

### DuckDuckGo bot-detection
DDG returns HTTP 202 when it detects bots. Google News RSS is used as fallback automatically.

### TheSportsDB score parsing
`int("?")` throws — wrapped in try/except, unknown scores default to `0`.

---

## Environment Variables (`.env`)

```
AZURE_OPENAI_ENDPOINT=https://...openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=o4-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
FLASK_PORT=5010
```

---

## Run Locally

```bash
cd soccer-app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd react-ui && npm install && npm run build && cd ..
python app.py
# → http://localhost:5010
```
