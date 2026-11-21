import os
import pandas as pd
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

load_dotenv()

_vader = SentimentIntensityAnalyzer()

REQUIRED_COLUMNS = ["customer_id", "product", "feedback"]
PLACEHOLDERS = ("your-resource-name", "your-key-here")
BATCH_SIZE = 10      # Azure accepts up to 10 documents per sentiment request
MAX_ROWS = 200       # keeps a learning project fast and cheap
MAX_CHARS = 5000     # per review


def azure_configured():
    endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT", "").strip()
    key = os.getenv("AZURE_LANGUAGE_KEY", "").strip()
    if not endpoint or not key:
        return False
    return not any(p in endpoint or p in key for p in PLACEHOLDERS)


def get_client():
    from azure.ai.textanalytics import TextAnalyticsClient
    from azure.core.credentials import AzureKeyCredential
    return TextAnalyticsClient(
        endpoint=os.getenv("AZURE_LANGUAGE_ENDPOINT").strip(),
        credential=AzureKeyCredential(os.getenv("AZURE_LANGUAGE_KEY").strip()),
    )


def load_reviews(source):
    """Read a CSV (file path or uploaded file) and validate it."""
    df = pd.read_csv(source, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("CSV is missing column(s): " + ", ".join(missing)
                         + ". Required: " + ", ".join(REQUIRED_COLUMNS))

    has_date = "date" in df.columns
    df = df[REQUIRED_COLUMNS + (["date"] if has_date else [])].copy()
    if has_date:
        parsed = pd.to_datetime(df["date"], errors="coerce")
        df["date"] = parsed.dt.strftime("%Y-%m-%d").fillna("")
    df["feedback"] = df["feedback"].fillna("").astype(str).str.strip().str.slice(0, MAX_CHARS)
    df["product"] = df["product"].fillna("Unknown").astype(str).str.strip()
    df = df[df["feedback"] != ""].reset_index(drop=True)

    if df.empty:
        raise ValueError("The CSV has no feedback text to analyze.")
    if len(df) > MAX_ROWS:
        raise ValueError("Too many rows (" + str(len(df)) + "). Maximum is " + str(MAX_ROWS) + ".")
    return df


def vader_one(text):
    compound = _vader.polarity_scores(text)["compound"]
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"
    return label, round(compound, 3)


def analyze_with_vader(df):
    out = df.copy()
    results = [vader_one(t) for t in out["feedback"]]
    out["sentiment"] = [r[0] for r in results]
    out["score"] = [r[1] for r in results]
    out["key_phrases"] = ""
    out["backend"] = "VADER (fallback)"
    return out


def analyze_with_azure(df):
    client = get_client()
    texts = df["feedback"].tolist()
    sentiments, scores, phrases, backends = [], [], [], []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        sent_results = client.analyze_sentiment(documents=batch)
        phrase_results = client.extract_key_phrases(documents=batch)

        for text, s, p in zip(batch, sent_results, phrase_results):
            if s.is_error:
                label, score = vader_one(text)
                sentiments.append(label)
                scores.append(score)
                backends.append("VADER (fallback)")
            else:
                label = "neutral" if s.sentiment == "mixed" else s.sentiment
                sentiments.append(label)
                scores.append(round(s.confidence_scores.positive - s.confidence_scores.negative, 3))
                backends.append("Azure AI Language")
            phrases.append("" if p.is_error else ", ".join(p.key_phrases))

    out = df.copy()
    out["sentiment"] = sentiments
    out["score"] = scores
    out["key_phrases"] = phrases
    out["backend"] = backends
    return out


def analyze_dataframe(df):
    """Returns (results_dataframe, note). Note is empty when Azure worked."""
    if not azure_configured():
        return analyze_with_vader(df), "Azure is not configured, so VADER was used."
    try:
        return analyze_with_azure(df), ""
    except Exception as exc:
        return analyze_with_vader(df), "Azure failed (" + type(exc).__name__ + "), so VADER was used."

