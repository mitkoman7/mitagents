#!/usr/bin/env python3
"""
Databricks Chat UI - Flask server for React frontend
"""

import os
import uuid
import json
import queue
import threading
from flask import Flask, send_from_directory, request, jsonify, session, Response, stream_with_context
from dotenv import load_dotenv

load_dotenv()

REACT_BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "react")

app = Flask(__name__, static_folder=REACT_BUILD)
app.secret_key = os.getenv("FLASK_SECRET_KEY", uuid.uuid4().hex)

from app import agent_executor, memory, check_mcp_server, refresh_tools

sessions = {}


def get_or_create_memory(sid):
    if sid not in sessions:
        from langchain.memory import ConversationBufferMemory
        sessions[sid] = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return sessions[sid]


# Serve React app for all non-API routes
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join(REACT_BUILD, path)):
        return send_from_directory(REACT_BUILD, path)
    return send_from_directory(REACT_BUILD, "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mcp_connected": check_mcp_server()})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    sid = session.get("sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["sid"] = sid
    sess_memory = get_or_create_memory(sid)

    q = queue.Queue()

    def run_agent():
        try:
            refresh_tools()
            from langchain.agents import AgentExecutor, create_openai_functions_agent
            from langchain.callbacks.base import BaseCallbackHandler
            from app import llm, tools, prompt

            class StreamingToolTracker(BaseCallbackHandler):
                def __init__(self):
                    self.tools_used = []

                def on_agent_action(self, action, color=None, **kwargs):
                    name = getattr(action, "tool", "") or ""
                    if name:
                        if name not in self.tools_used:
                            self.tools_used.append(name)
                        q.put({"type": "activity", "tool": name})

                def on_tool_end(self, output, **kwargs):
                    q.put({"type": "activity_done"})

            tracker = StreamingToolTracker()
            agent = create_openai_functions_agent(llm, tools, prompt)
            executor = AgentExecutor(
                agent=agent, tools=tools, memory=sess_memory,
                verbose=False, handle_parsing_errors=True,
                callbacks=[tracker],
            )
            response = executor.invoke({"input": user_message})
            refresh_tools()
            q.put({"type": "done", "reply": response.get("output", "No response"), "activities": tracker.tools_used})
        except Exception as e:
            q.put({"type": "error", "reply": f"Error: {str(e)}", "activities": []})

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                event = q.get(timeout=120)
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ("done", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'reply': 'Timeout', 'activities': []})}\n\n"
                break

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/clear", methods=["POST"])
def clear():
    sid = session.get("sid")
    if sid and sid in sessions:
        del sessions[sid]
    memory.clear()
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    print("=" * 50)
    print("  DXC Databricks Assistant - Web UI")
    print("  http://localhost:5055")
    print("=" * 50)
    port = int(os.getenv("PORT", 5055))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
