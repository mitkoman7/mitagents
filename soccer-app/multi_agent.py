"""
Multi-agent soccer prediction system using LangGraph.

Graph:  START → orchestrator → [1x2 | goals | corners | cards] (parallel) → synthesizer → END

- Orchestrator: deterministic data fetcher (web_search + team_form x2)
- 4 Specialists run in parallel via ThreadPoolExecutor, each focused on one market
- Synthesizer: reads all 4 reports, picks highest-confidence market
"""

import os, json, re, threading
from typing import TypedDict, Annotated, Any
import operator
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty

from openai import AzureOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from tools import web_search, team_form

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)
DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# ── Shared state ──────────────────────────────────────────────────────────────

class MatchState(TypedDict):
    question:       str
    base_context:   str
    report_1x2:     str
    report_goals:   str
    report_corners: str
    report_cards:   str
    final_answer:   str
    activities:     Annotated[list, operator.add]
    _queue:         Any   # threading.Queue for SSE events — never merged


# ── LLM helper ────────────────────────────────────────────────────────────────

def _llm(messages: list, max_tokens: int = 4000) -> str:
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        messages=messages,
        max_completion_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def _emit(state: MatchState, agent: str, query: str):
    q = state.get("_queue")
    if q:
        q.put({"type": "activity", "agent": agent, "query": query})


# ── Node 1: Orchestrator (data fetcher, no LLM) ───────────────────────────────

def orchestrator_node(state: MatchState) -> dict:
    _emit(state, "orchestrator", "Collecting base data…")

    question = state["question"]

    # Use a small LLM call just to parse team names cleanly
    raw = _llm([
        {"role": "system", "content": 'Extract the two football team names from the question. Return ONLY valid JSON: {"team_a": "...", "team_b": "..."}'},
        {"role": "user",   "content": question},
    ], max_tokens=1000)

    team_a = team_b = ""
    try:
        m = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if m:
            teams = json.loads(m.group(0))
            team_a = teams.get("team_a", "").strip()
            team_b = teams.get("team_b", "").strip()
    except Exception:
        pass

    # Regex fallback: split on " vs " or " v "
    if not team_a or not team_b:
        parts = re.split(r'\s+vs\.?\s+|\s+v\.?\s+', question, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            team_a = parts[0].strip().rstrip('?.,')
            # strip any trailing context from team_b (e.g. "second leg best bet?")
            team_b = re.split(r'\s+(?:second|first|leg|best|prediction|match|today)', parts[1], maxsplit=1, flags=re.IGNORECASE)[0].strip().rstrip('?.,')


    _emit(state, "orchestrator", f"Fetching data for {team_a} vs {team_b}…")

    match_ctx = web_search(f"{team_a} vs {team_b} 2026 result first leg", max_results=5)
    form_a    = team_form(team_a) if team_a else "Team not identified."
    form_b    = team_form(team_b) if team_b else "Team not identified."

    base = (
        f"QUESTION: {question}\n\n"
        f"TEAMS: {team_a} vs {team_b}\n\n"
        f"MATCH CONTEXT (web):\n{match_ctx}\n\n"
        f"{team_a} FORM:\n{form_a}\n\n"
        f"{team_b} FORM:\n{form_b}"
    )

    _emit(state, "orchestrator", f"Base data ready ✓")
    return {"base_context": base, "activities": [f"orchestrator: {team_a} vs {team_b}"]}


# ── Specialist agent runner ───────────────────────────────────────────────────

def _run_specialist(name: str, icon: str, system_prompt: str,
                    extra_queries: list, state: MatchState) -> str:
    _emit(state, name, f"{icon} {name.upper()} Agent: searching…")

    extra = ""
    for q in extra_queries:
        res = web_search(q, max_results=3)
        extra += f"\nSearch: {q}\n{res}\n"

    _emit(state, name, f"{icon} {name.upper()} Agent: analysing…")

    answer = _llm([
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": (
            f"BASE CONTEXT:\n{state['base_context']}\n\n"
            f"SPECIALIST RESEARCH:\n{extra or 'None.'}\n\n"
            f"QUESTION: {state['question']}"
        )},
    ], max_tokens=4000)

    _emit(state, name, f"{icon} {name.upper()} Agent: done ✓")
    return answer


# ── Specialist system prompts ─────────────────────────────────────────────────

_PROMPT_1X2 = """You are a 1X2 market specialist. Analyse ONLY the match result market.
Consider: current form (W/D/L), head-to-head, home/away advantage, aggregate score if 2nd leg.
Return ONLY valid JSON (no extra text):
{"market":"1X2","bet":"Home Win|Draw|Away Win","probability":"XX%","confidence_score":1-10,"reasoning":"2-3 sentences"}"""

_PROMPT_GOALS = """You are a goals market specialist. Analyse ONLY goals markets.
Consider: avg goals scored/conceded per game from form data, BTTS history, must-win context.
Return ONLY valid JSON:
{"market":"Goals","bet":"Over 2.5 Goals|Under 2.5 Goals|BTTS Yes|BTTS No|Over 1.5|Over 3.5","probability":"XX%","confidence_score":1-10,"reasoning":"2-3 sentences"}"""

_PROMPT_CORNERS = """You are a corners market specialist. Analyse ONLY corners markets.
IMPORTANT: Only give a high confidence_score if the research contains ACTUAL corners-per-game stats.
If stats are missing set confidence_score to 2 and explain why.
Return ONLY valid JSON:
{"market":"Corners","bet":"Over 9.5 Corners|Under 9.5 Corners|Over 10.5|Under 8.5","probability":"XX%","confidence_score":1-10,"reasoning":"2-3 sentences"}"""

_PROMPT_CARDS = """You are a cards/bookings market specialist. Analyse ONLY cards markets.
Consider: referee tendency, rivalry intensity, competition stakes, avg bookings per game.
Return ONLY valid JSON:
{"market":"Cards","bet":"Over 3.5 Cards|Under 3.5 Cards|Over 4.5 Cards|Under 4.5 Cards","probability":"XX%","confidence_score":1-10,"reasoning":"2-3 sentences"}"""

_SYNTH_PROMPT = """You are a betting intelligence synthesizer. You receive 4 specialist reports as JSON.
Each has a confidence_score (1–10). Pick the ONE market with the highest score.
If two tie, prefer the market with more real data behind it.

Return the final prediction in this EXACT format:
🎯 **BEST BET:** [bet]
📊 **Estimated probability:** [XX%]
💪 **Confidence:** [Low / Medium / High]

**Form (last 5):**
• [Team A]: extracted from base context
• [Team B]: extracted from base context

**Match context:**
[first leg score / H2H / competition context]

**Analysis:**
[3–4 sentences: why this market wins, what the data says]

**Why this market over others?**
[1–2 sentences comparing to the runners-up]

**Other angles:**
• [2nd best market — agent name + bet]
• [3rd best market — agent name + bet]"""


# ── Parallel specialist node (wraps all 4 agents) ────────────────────────────

def parallel_specialists_node(state: MatchState) -> dict:
    _emit(state, "specialists", "4 market agents running in parallel…")

    question = state["question"]

    tasks = {
        "1x2": (
            "1x2", "⚽", _PROMPT_1X2,
            [f"{question} head to head record", f"{question} home away win rate 2026"],
        ),
        "goals": (
            "goals", "🎯", _PROMPT_GOALS,
            [f"{question} goals scored conceded stats 2026", f"{question} BTTS both teams score history"],
        ),
        "corners": (
            "corners", "🔺", _PROMPT_CORNERS,
            [f"{question} average corners per game 2026", f"{question} corners statistics"],
        ),
        "cards": (
            "cards", "🃏", _PROMPT_CARDS,
            [f"{question} yellow cards bookings per game 2026", f"{question} referee cards average"],
        ),
    }

    reports: dict = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_run_specialist, *args, state): key
            for key, args in tasks.items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                reports[key] = future.result()
            except Exception as e:
                reports[key] = json.dumps({"market": key, "bet": "N/A", "probability": "?",
                                           "confidence_score": 1, "reasoning": str(e)})

    return {
        "report_1x2":     reports.get("1x2", ""),
        "report_goals":   reports.get("goals", ""),
        "report_corners": reports.get("corners", ""),
        "report_cards":   reports.get("cards", ""),
        "activities":     ["1x2", "goals", "corners", "cards"],
    }


# ── Synthesizer node ──────────────────────────────────────────────────────────

def synthesizer_node(state: MatchState) -> dict:
    _emit(state, "synthesizer", "🧪 Synthesizer: picking best market…")

    content = (
        f"BASE CONTEXT:\n{state['base_context']}\n\n"
        f"1X2 AGENT:\n{state.get('report_1x2','N/A')}\n\n"
        f"GOALS AGENT:\n{state.get('report_goals','N/A')}\n\n"
        f"CORNERS AGENT:\n{state.get('report_corners','N/A')}\n\n"
        f"CARDS AGENT:\n{state.get('report_cards','N/A')}\n\n"
        f"QUESTION: {state['question']}"
    )

    answer = _llm([
        {"role": "system", "content": _SYNTH_PROMPT},
        {"role": "user",   "content": content},
    ], max_tokens=8000)

    _emit(state, "synthesizer", "🧪 Synthesizer: done ✓")
    return {"final_answer": answer, "activities": ["synthesizer"]}


# ── Build the LangGraph ───────────────────────────────────────────────────────

def _build_graph():
    builder = StateGraph(MatchState)
    builder.add_node("orchestrator",  orchestrator_node)
    builder.add_node("specialists",   parallel_specialists_node)
    builder.add_node("synthesizer",   synthesizer_node)
    builder.add_edge(START,           "orchestrator")
    builder.add_edge("orchestrator",  "specialists")
    builder.add_edge("specialists",   "synthesizer")
    builder.add_edge("synthesizer",   END)
    return builder.compile()

_graph = _build_graph()


# ── Public API ────────────────────────────────────────────────────────────────

def run_prediction(question: str, event_callback=None):
    """
    Run the 5-agent prediction pipeline.
    event_callback(dict) receives SSE-style activity events in real time.
    Returns (final_answer: str, all_reports: dict).
    """
    eq = Queue() if event_callback else None
    result_holder: list = [None, {}]

    initial: MatchState = {
        "question":       question,
        "base_context":   "",
        "report_1x2":     "",
        "report_goals":   "",
        "report_corners": "",
        "report_cards":   "",
        "final_answer":   "",
        "activities":     [],
        "_queue":         eq,
    }

    def _run():
        final_state = _graph.invoke(initial)
        result_holder[0] = final_state["final_answer"]
        result_holder[1] = {
            "1x2":     final_state.get("report_1x2", ""),
            "goals":   final_state.get("report_goals", ""),
            "corners": final_state.get("report_corners", ""),
            "cards":   final_state.get("report_cards", ""),
        }
        if eq:
            eq.put({"type": "__done__"})

    if event_callback and eq:
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        while True:
            try:
                event = eq.get(timeout=180)
                if event.get("type") == "__done__":
                    break
                event_callback(event)
            except Empty:
                break
        t.join(timeout=10)
    else:
        _run()

    answer = result_holder[0]
    return (answer if answer is not None and answer.strip() else "Error: no answer generated."), result_holder[1]
