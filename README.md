# Customer Feedback Intelligence

A student project that turns customer reviews into insights. Upload a CSV of reviews, analyse sentiment, view KPIs and charts, generate AI-written executive insights, ask questions with RAG, use an AI analyst agent with tools, and explore predictive analytics.

**CSV columns:** `customer_id, product, feedback` (optional `date` column for trend forecasts)

## Features

- **Sentiment and key phrases** with Azure AI Language. If Azure is missing or fails, the app falls back to VADER. The backend used is shown on every row.
- **KPIs and charts** (Chart.js), product performance table, CSV and PowerPoint download.
- **Executive insights and chatbot** with Azure AI Foundry. All numbers are calculated in Python, not by the LLM.
- **RAG assistant:** all-MiniLM-L6-v2 embeddings, FAISS IndexFlatIP (cosine similarity), product filter, Top-K, similarity threshold, and source reviews.
- **AI analyst agent:** a function-calling loop with 5 Python tools and an execution trace (tool, status, duration).
- **Predictions:** heuristic product risk score, TF-IDF + Logistic Regression sentiment predictor, and a weekly trend forecast.
- **Responsive interface** with selectable themes.

## Architecture

CSV -> `analysis.py` (Azure Language or VADER) -> results DataFrame -> `analytics.py`, `risk.py`, `trend.py`, `predictor.py`, `rag_engine.py`, `agent_tools.py` -> Flask routes -> HTML and Chart.js.

The LLM (Azure AI Foundry) only writes text from tool results or retrieved reviews.

## Run locally (Windows PowerShell, Python 3.11)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python app.py
```

Open http://127.0.0.1:5000 and upload `sample_data/reviews_big.csv`.

## Environment variables

Copy `.env.example` to `.env` and fill in your own values. **Never commit `.env`.**

| Variable | Purpose |
|---|---|
| `AZURE_LANGUAGE_ENDPOINT`, `AZURE_LANGUAGE_KEY` | Azure AI Language |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_INFERENCE_CREDENTIAL` | Azure AI Foundry model deployment |

Without Azure values, the app uses VADER for sentiment and Foundry features show a clear "not configured" message.

## Notes

- The app runs on the Flask development server and has no login. Do not expose it publicly, because anyone could use your Azure quota.
- The first run downloads the embedding model (about 90 MB).

## Limitations

- VADER is lexicon-based and can mark clear complaints as neutral. Azure and VADER give different KPIs.
- Complaint categories are keyword rules. One review can fall into several categories, and unmatched ones go to "other".
- Embedding similarity measures topic, not whether a review is a complaint.
- The agent is non-deterministic. Its evaluation (7 questions) is small and checks only tool names, keywords and cited references. Tool calls above the per-round limit are dropped.
- The predictor learns Azure or VADER labels, including their mistakes. With few unique reviews its accuracy is only a rough guide. Risk score weights are my own choice, not a standard.
- The trend forecast is a straight line. With few reviews per week it is weak, and the app says so.
- `sample_data/reviews_big.csv` is synthetic (made by `make_sample_big.py`), not real customers.
- Not built: YAKE key phrases, a DistilBERT SST-2 route (English binary only), a Gemini or Ollama report route, and Azure AI Foundry Agents with `DefaultAzureCredential`.
