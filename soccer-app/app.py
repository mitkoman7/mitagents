#!/usr/bin/env python3
"""
Soccer AI — Flask API.
/api/chat uses the LangGraph multi-agent pipeline (multi_agent.py).
"""

import os, json, uuid
from datetime import date, datetime
from flask import Flask, request, Response, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from tools import web_search, team_form, get_fixtures, _espn_fixtures, _ESPN_LEAGUES, _TSDB_BASE
import requests as _req
from multi_agent import run_prediction

load_dotenv()

STATIC = os.path.join(os.path.dirname(__file__), "static", "react")
app = Flask(__name__, static_folder=STATIC, static_url_path="")
CORS(app)


# ── Fixtures endpoint ─────────────────────────────────────────────────────────

@app.route("/api/fixtures")
def fixtures_endpoint():
    competition = request.args.get("competition", "")
    today = date.today().isoformat()
    ck = competition.lower().strip()
    matches = []

    slug = next((s for n, s in _ESPN_LEAGUES.items() if n in ck or ck in n), None)
    if slug:
        try:
            matches = _espn_fixtures(slug)
        except Exception:
            pass

    if not matches:
        try:
            r = _req.get(f"{_TSDB_BASE}/eventsday.php?d={today}&s=Soccer", timeout=10)
            events = r.json().get("events") or []
            if ck:
                events = [e for e in events if ck in e.get("strLeague", "").lower()]
            for ev in events:
                matches.append({"home": ev.get("strHomeTeam", ""), "away": ev.get("strAwayTeam", ""),
                                 "status": "Scheduled", "time": ev.get("strTime", ""),
                                 "league": ev.get("strLeague", "")})
        except Exception:
            pass

    web_fallback = None
    if not matches:
        web_fallback = web_search(f"{competition} fixtures today {today}", max_results=5)

    return jsonify({"date": today, "competition": competition,
                    "matches": matches, "web_fallback": web_fallback})


# ── Predictions store ─────────────────────────────────────────────────────────

PREDICTIONS_FILE = os.path.join(os.path.dirname(__file__), "predictions.json")

def _load_preds():
    try:
        with open(PREDICTIONS_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def _save_preds(preds):
    with open(PREDICTIONS_FILE, "w") as f:
        json.dump(preds, f, indent=2)

@app.route("/api/predictions", methods=["GET"])
def get_predictions_route():
    return jsonify(_load_preds())

@app.route("/api/predictions", methods=["POST"])
def add_prediction():
    data = request.get_json() or {}
    pred = {"id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat(),
            "question": data.get("question", ""), "reply": data.get("reply", ""),
            "best_bet": data.get("best_bet", ""), "probability": data.get("probability", ""),
            "confidence": data.get("confidence", ""), "result": None}
    preds = _load_preds(); preds.insert(0, pred); _save_preds(preds)
    return jsonify(pred), 201

@app.route("/api/predictions/<pred_id>", methods=["PATCH"])
def update_prediction(pred_id):
    data = request.get_json() or {}
    preds = _load_preds()
    for p in preds:
        if p["id"] == pred_id:
            p["result"] = data.get("result"); break
    _save_preds(preds)
    return jsonify({"ok": True})

@app.route("/api/predictions/<pred_id>", methods=["DELETE"])
def delete_prediction(pred_id):
    _save_preds([p for p in _load_preds() if p["id"] != pred_id])
    return jsonify({"ok": True})


# ── Health / clear ────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "mcp_connected": True, "model": "o4-mini multi-agent"})

@app.route("/api/clear", methods=["POST"])
def clear():
    return jsonify({"status": "cleared"})


# ── Chat: multi-agent pipeline ────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400

    def generate():
        activities = []
        try:
            def on_event(event):
                activities.append(event.get("query", ""))
                yield f"data: {json.dumps({'type': 'activity', 'agent': event.get('agent',''), 'query': event.get('query','')})}\n\n"

            # on_event is a generator inside a closure — collect via callback
            sse_events = []
            def callback(event):
                sse_events.append(event)

            # Run in current thread but stream events via a list + flush trick
            # We use a simpler approach: collect all events, then yield them
            # For true streaming, use the thread+queue pattern from multi_agent.py
            import queue as _queue_mod
            import threading

            q = _queue_mod.Queue()
            result_box = [None]

            def _worker():
                from multi_agent import run_prediction as rp
                answer, reports = rp(message, event_callback=lambda e: q.put(e))
                result_box[0] = (answer, reports)
                q.put({"type": "__done__"})

            t = threading.Thread(target=_worker, daemon=True)
            t.start()

            while True:
                try:
                    event = q.get(timeout=180)
                    if event.get("type") == "__done__":
                        break
                    activities.append(event.get("query", ""))
                    yield f"data: {json.dumps({'type': 'activity', 'agent': event.get('agent',''), 'query': event.get('query','')})}\n\n"
                except _queue_mod.Empty:
                    break

            t.join(timeout=10)

            if result_box[0]:
                answer, reports = result_box[0]
                yield f"data: {json.dumps({'type': 'done', 'reply': answer, 'activities': activities, 'reports': reports})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'reply': 'No answer generated.', 'activities': activities})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'reply': f'Error: {str(e)}', 'activities': activities})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(STATIC, path)):
        return send_from_directory(STATIC, path)
    return send_from_directory(STATIC, "index.html")


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5010))
    print(f"⚽  Soccer AI Multi-Agent → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
