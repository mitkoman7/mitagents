#!/usr/bin/env python3
"""Generate Soccer AI infographic using gpt-image-1-5."""

import os, base64, requests, time
from dotenv import load_dotenv

load_dotenv()

ENDPOINT   = os.environ["IMAGE_ENDPOINT"].rstrip("/")
API_KEY    = os.environ["IMAGE_KEY"]
DEPLOYMENT = os.environ["IMAGE_DEPLOYMENT"]
API_VER    = os.environ["IMAGE_API_VERSION"]

URL = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/images/generations?api-version={API_VER}"

PROMPT = """
A professional dark-themed technical infographic poster for a soccer match prediction AI system.
Clean vector-style design, dark navy/charcoal background, electric green and cyan accents,
modern sans-serif typography, no photography.

Layout (top to bottom):

HEADER: Bold title "SOCCER AI" with a football icon ⚽.
Subtitle: "Multi-Agent Prediction System · Azure OpenAI o4-mini · LangGraph"

SECTION 1 — blue glowing rounded rectangle labelled "🧭 ORCHESTRATOR":
Text inside: "Extract teams · Web search · TheSportsDB form (last 5 matches)"
Arrow pointing down, splitting into 4 parallel columns.

SECTION 2 — Four side-by-side glowing agent cards:
Card 1 (green glow): "⚽ 1X2 AGENT" — "Home / Draw / Away"
Card 2 (amber glow): "🎯 GOALS AGENT" — "Over 2.5 · BTTS"
Card 3 (orange glow): "🔺 CORNERS AGENT" — "Over 9.5 corners"
Card 4 (purple glow): "🃏 CARDS AGENT" — "Bookings market"
Below each card: small label "JSON → confidence_score 1-10"

Arrow pointing down from all 4 cards converging.

SECTION 3 — teal glowing rounded rectangle labelled "🧪 SYNTHESIZER":
Text: "Picks highest confidence_score → Best Bet + Probability + Reasoning"

SECTION 4 — Two side-by-side info boxes:
Left box (dark): "Search Stack" — "DuckDuckGo HTML → Google News RSS fallback"
Right box (dark): "SSE Streaming" — "Flask · Thread+Queue · Real-time agent events"

FOOTER: small text "ThreadPoolExecutor · 4 parallel agents · LangGraph StateGraph"

Style: premium sports analytics dashboard, subtle dot-grid background, neon glow on node borders,
connecting arrows with gradient glow, each section clearly separated.
No human figures. No photographs. Pure infographic illustration.
"""

def post_with_retry(url, headers, payload, tries=3):
    for attempt in range(tries):
        r = requests.post(url, headers=headers, json=payload, timeout=300)
        if r.status_code == 429 and attempt < tries - 1:
            wait = min(int(r.headers.get("retry-after", 20)) + 1, 60)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        return r
    return r

print("Generating infographic with gpt-image-1-5...")

r = post_with_retry(
    URL,
    headers={"api-key": API_KEY, "Content-Type": "application/json"},
    payload={
        "prompt": PROMPT,
        "n": 1,
        "size": "1024x1536",
        "quality": "high",
        "moderation": "low",
    },
)

if r.status_code != 200:
    print(f"Error {r.status_code}: {r.text[:500]}")
    exit(1)

image_bytes = base64.b64decode(r.json()["data"][0]["b64_json"])

out = os.path.join(os.path.dirname(__file__), "static", "soccer_ai_infographic.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "wb") as f:
    f.write(image_bytes)

print(f"Saved → {out}  ({len(image_bytes)//1024} KB)")
