import threading
from flask import jsonify, request, render_template, abort
from rag_routes import get_index
from agent_tools import ToolBox
from agent import run_agent, agent_backend_label

_TOOLBOXES = {}
_MAX_CACHED = 5
_lock = threading.Lock()


def get_toolbox(download_id, load_raw):
    """Build the toolbox (data + FAISS index) once per upload, then reuse it."""
    with _lock:
        if download_id in _TOOLBOXES:
            return _TOOLBOXES[download_id]
    idx = get_index(download_id, load_raw)
    results = load_raw(download_id)
    if idx is None or results is None:
        return None
    tb = ToolBox(results, idx)
    with _lock:
        if len(_TOOLBOXES) >= _MAX_CACHED:
            _TOOLBOXES.pop(next(iter(_TOOLBOXES)))
        _TOOLBOXES[download_id] = tb
    return tb


def register_agent(app, load_raw, valid_id):
    @app.route("/agent/<download_id>")
    def agent_page(download_id):
        if not valid_id(download_id):
            abort(404)
        tb = get_toolbox(download_id, load_raw)
        if tb is None:
            abort(404)
        return render_template("agent.html", download_id=download_id,
                               products=tb.products, size=len(tb.results),
                               backend=agent_backend_label())

    @app.route("/agent/<download_id>/ask", methods=["POST"])
    def agent_ask(download_id):
        if not valid_id(download_id):
            abort(404)
        tb = get_toolbox(download_id, load_raw)
        if tb is None:
            return jsonify({"error": "Results not found. Please upload the CSV again."}), 404
        body = request.get_json(silent=True) or {}
        question = str(body.get("question", "")).strip()
        history = body.get("history", [])
        if not isinstance(history, list):
            history = []
        out = run_agent(tb, question, history)
        return jsonify(out), (502 if out["error"] else 200)
