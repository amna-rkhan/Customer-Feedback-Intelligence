import threading
from flask import jsonify, request, render_template, abort
from risk import product_risk, METHOD as RISK_METHOD
from predictor import train_predictor, predict_sentiment
from trend import forecast

_CACHE = {}
_MAX_CACHED = 5
_lock = threading.Lock()


def get_bundle(download_id, load_raw):
    """Compute risk, trends and the predictor once per upload, then reuse."""
    with _lock:
        if download_id in _CACHE:
            return _CACHE[download_id]
    results = load_raw(download_id)
    if results is None:
        return None
    pred, reason = train_predictor(results)
    products = sorted({str(p) for p in results["product"]})
    trends = {}
    for p in [None] + products:
        res, why = forecast(results, p, min_per_week=2 if p else 3)
        trends[p or "All products"] = {"result": res, "reason": why}
    bundle = {"results": results, "risk": product_risk(results), "pred": pred,
              "pred_reason": reason, "trends": trends}
    with _lock:
        if len(_CACHE) >= _MAX_CACHED:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[download_id] = bundle
    return bundle


def register_predict(app, load_raw, valid_id):
    @app.route("/predict/<download_id>")
    def predict_page(download_id):
        if not valid_id(download_id):
            abort(404)
        b = get_bundle(download_id, load_raw)
        if b is None:
            abort(404)
        p = b["pred"]
        info = None
        if p:
            info = {k: p[k] for k in ("classes", "dropped_classes", "unique_reviews", "cv_folds",
                                      "cv_accuracy", "baseline_accuracy", "method")}
        backends = sorted({str(x) for x in b["results"]["backend"]})
        return render_template("predict.html", download_id=download_id, risk=b["risk"],
                               risk_method=RISK_METHOD, trends=b["trends"], info=info,
                               pred_reason=b["pred_reason"], backends=backends)

    @app.route("/predict/<download_id>/review", methods=["POST"])
    def predict_review(download_id):
        if not valid_id(download_id):
            abort(404)
        b = get_bundle(download_id, load_raw)
        if b is None:
            return jsonify({"error": "Results not found. Please upload the CSV again."}), 404
        if b["pred"] is None:
            return jsonify({"error": "Predictor not available: " + b["pred_reason"]}), 400
        body = request.get_json(silent=True) or {}
        res, err = predict_sentiment(b["pred"], body.get("text", ""))
        if err:
            return jsonify({"error": err}), 400
        return jsonify(res)
