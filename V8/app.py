import os
import uuid
import pandas as pd
from flask import Flask, render_template, request, send_file, abort, jsonify
from analysis import load_reviews, analyze_dataframe
from analytics import product_stats
from executive_report import generate_report
from chatbot import build_context, chat
from executive_deck import build_deck
from rag_routes import register_rag
from agent_routes import register_agent
from predict_routes import register_predict

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # reject uploads over 1 MB

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.errorhandler(413)
def too_large(e):
    return render_template("index.html", error="File is too large (max 1 MB).", kpis=None, rows=None), 413


def valid_id(value):
    return len(value) == 32 and all(c in "0123456789abcdef" for c in value)


def build_kpis(results):
    total = len(results)
    counts = results["sentiment"].value_counts()
    kpis = {"total": total}
    for label in ("positive", "negative", "neutral"):
        n = int(counts.get(label, 0))
        kpis[label] = n
        kpis[label + "_pct"] = round(n * 100 / total, 1)
    kpis["avg_score"] = round(float(results["score"].mean()), 2) + 0.0
    return kpis


def build_chart_data(kpis, products):
    return {
        "sentiment": [kpis["positive"], kpis["negative"], kpis["neutral"]],
        "products": [p["product"] for p in products],
        "positive": [p["positive"] for p in products],
        "negative": [p["negative"] for p in products],
        "neutral": [p["neutral"] for p in products],
    }


def safe_for_excel(value):
    """Stop Excel from treating text that starts with = + - @ as a formula."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def save_results(results):
    download_id = uuid.uuid4().hex
    # raw copy: used later by the report and chat features
    results.to_csv(os.path.join(OUTPUT_DIR, download_id + "_raw.csv"), index=False, encoding="utf-8")
    # Excel-safe copy: used by the download button
    export = results.copy()
    for col in ("product", "feedback", "key_phrases"):
        export[col] = export[col].map(safe_for_excel)
    export.to_csv(os.path.join(OUTPUT_DIR, download_id + ".csv"), index=False, encoding="utf-8-sig")
    return download_id


def load_raw(download_id):
    raw_path = os.path.join(OUTPUT_DIR, download_id + "_raw.csv")
    if not os.path.exists(raw_path):
        return None
    return pd.read_csv(raw_path, keep_default_na=False)


@app.route("/", methods=["GET", "POST"])
def index():
    error = ""
    note = ""
    kpis = None
    rows = None
    products = None
    chart_data = None
    download_id = None

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            error = "Please choose a CSV file first."
        elif not file.filename.lower().endswith(".csv"):
            error = "The file must be a .csv file."
        else:
            try:
                df = load_reviews(file)
                results, note = analyze_dataframe(df)
                kpis = build_kpis(results)
                products = product_stats(results)
                chart_data = build_chart_data(kpis, products)
                rows = results.to_dict("records")
                download_id = save_results(results)
            except ValueError as exc:
                error = str(exc)
            except Exception as exc:
                error = "Could not read this file (" + type(exc).__name__ + "). Check that it is a valid CSV."

    return render_template("index.html", error=error, note=note, kpis=kpis, rows=rows,
                           products=products, chart_data=chart_data, download_id=download_id)


@app.route("/download/<download_id>")
def download(download_id):
    if not valid_id(download_id):
        abort(404)
    path = os.path.join(OUTPUT_DIR, download_id + ".csv")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True,
                     download_name="feedback_analysis.csv", mimetype="text/csv")


@app.route("/report/<download_id>", methods=["POST"])
def report(download_id):
    if not valid_id(download_id):
        abort(404)
    results = load_raw(download_id)
    if results is None:
        return jsonify({"error": "Results not found. Please upload the CSV again."}), 404
    kpis = build_kpis(results)
    products = product_stats(results)
    rep, err = generate_report(kpis, products, results)
    if err:
        return jsonify({"error": err}), 502
    return jsonify(rep)


@app.route("/chat/<download_id>", methods=["POST"])
def chat_route(download_id):
    if not valid_id(download_id):
        abort(404)
    results = load_raw(download_id)
    if results is None:
        return jsonify({"error": "Results not found. Please upload the CSV again."}), 404
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    history = data.get("history", [])
    if not isinstance(question, str) or not isinstance(history, list):
        return jsonify({"error": "Invalid request."}), 400
    kpis = build_kpis(results)
    products = product_stats(results)
    facts = build_context(kpis, products, results)
    answer, err = chat(question, history, facts)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"answer": answer})


@app.route("/deck/<download_id>")
def deck(download_id):
    if not valid_id(download_id):
        abort(404)
    results = load_raw(download_id)
    if results is None:
        abort(404)
    kpis = build_kpis(results)
    products = product_stats(results)
    rep, err = generate_report(kpis, products, results)
    buf = build_deck(kpis, products, rep)
    return send_file(buf, as_attachment=True, download_name="executive_report.pptx",
                     mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")

register_rag(app, load_raw, valid_id)
register_agent(app, load_raw, valid_id)
register_predict(app, load_raw, valid_id)

if __name__ == "__main__":
    app.run(debug=True)



