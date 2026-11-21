import threading
from flask import jsonify, request, render_template, abort
from rag_engine import ReviewIndex, RETRIEVAL_BACKEND
from rag_answer import answer_question

_CACHE = {}
_MAX_CACHED = 5
_lock = threading.Lock()


def get_index(download_id, load_raw):
    """Build the FAISS index once per upload, then reuse it."""
    with _lock:
        if download_id in _CACHE:
            return _CACHE[download_id]
    results = load_raw(download_id)
    if results is None:
        return None
    idx = ReviewIndex(results)
    with _lock:
        if len(_CACHE) >= _MAX_CACHED:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[download_id] = idx
    return idx


def register_rag(app, load_raw, valid_id):
    @app.route("/rag/<download_id>")
    def rag_page(download_id):
        if not valid_id(download_id):
            abort(404)
        idx = get_index(download_id, load_raw)
        if idx is None:
            abort(404)
        return render_template("rag.html", download_id=download_id,
                               products=idx.products(), size=idx.size,
                               dimensions=idx.dimensions, backend=RETRIEVAL_BACKEND)

    @app.route("/rag/<download_id>/ask", methods=["POST"])
    def rag_ask(download_id):
        if not valid_id(download_id):
            abort(404)
        idx = get_index(download_id, load_raw)
        if idx is None:
            return jsonify({"error": "Results not found. Please upload the CSV again."}), 404

        body = request.get_json(silent=True) or {}
        question = str(body.get("question", "")).strip()
        if not question:
            return jsonify({"error": "Please type a question."}), 400

        product = str(body.get("product", "")).strip()
        if product and product not in idx.products():
            return jsonify({"error": "Unknown product filter."}), 400
        try:
            min_score = min(max(float(body.get("min_score", 0.25)), 0.0), 1.0)
            top_k = min(max(int(body.get("top_k", 5)), 1), 10)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid threshold or Top-K."}), 400

        hits = idx.search(question, top_k=top_k, min_score=min_score, product=product or None)
        res, err = answer_question(question, hits)
        if err:
            return jsonify({"error": err, "retrieved": len(hits)}), 502
        return jsonify({
            "answer": res["answer"],
            "sources": res["sources"],
            "enough_evidence": res["enough_evidence"],
            "llm_used": res["llm_used"],
            "retrieval_backend": RETRIEVAL_BACKEND,
            "hits": hits,
        })
