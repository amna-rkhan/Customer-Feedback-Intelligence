import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import re
import numpy as np
import faiss

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RETRIEVAL_BACKEND = "all-MiniLM-L6-v2 embeddings + FAISS IndexFlatIP (cosine)"
MAX_CHARS = 1000
MAX_TOP_K = 20

_model = None


def get_model():
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model


def clean_text(text):
    """Remove control characters, collapse spaces, limit length."""
    text = str(text)
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]


def embed(texts):
    """Texts -> normalized float32 vectors (384 numbers each)."""
    vecs = get_model().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.ascontiguousarray(vecs, dtype="float32")


class ReviewIndex:
    """FAISS index plus a separate metadata list (same order)."""

    def __init__(self, df):
        self.records = []
        for _, row in df.iterrows():
            text = clean_text(row.get("feedback", ""))
            if not text:
                continue
            self.records.append({
                "ref": "R" + str(len(self.records) + 1),
                "product": str(row.get("product", "Unknown")).strip() or "Unknown",
                "feedback": text,
                "sentiment": str(row.get("sentiment", "")),
            })

        self.index = None
        self.dimensions = 0
        if self.records:
            vectors = embed([r["feedback"] for r in self.records])
            self.dimensions = int(vectors.shape[1])
            self.index = faiss.IndexFlatIP(self.dimensions)
            self.index.add(vectors)

    @property
    def size(self):
        return 0 if self.index is None else int(self.index.ntotal)

    def products(self):
        return sorted({r["product"] for r in self.records})

    def search(self, question, top_k=5, min_score=0.25, product=None):
        """Return the best matching reviews, highest similarity first."""
        question = clean_text(question)
        if not question or self.size == 0:
            return []

        top_k = max(1, min(int(top_k), MAX_TOP_K))
        min_score = float(min_score)
        wanted = (product or "").strip().lower()

        scores, ids = self.index.search(embed([question]), self.size)
        hits = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            if score < min_score:
                break                       # results are sorted, so the rest are lower
            rec = self.records[int(idx)]
            if wanted and rec["product"].lower() != wanted:
                continue
            hit = dict(rec)
            hit["score"] = round(float(score), 3)
            hits.append(hit)
            if len(hits) >= top_k:
                break
        return hits
class ReviewIndex:
    """FAISS index plus a separate metadata list (same order)."""

    def __init__(self, df):
        self.records = []
        for _, row in df.iterrows():
            text = clean_text(row.get("feedback", ""))
            if not text:
                continue
            self.records.append({
                "ref": "R" + str(len(self.records) + 1),
                "product": str(row.get("product", "Unknown")).strip() or "Unknown",
                "feedback": text,
                "sentiment": str(row.get("sentiment", "")),
            })

        self.index = None
        self.dimensions = 0
        if self.records:
            vectors = embed([r["feedback"] for r in self.records])
            self.dimensions = int(vectors.shape[1])
            self.index = faiss.IndexFlatIP(self.dimensions)
            self.index.add(vectors)

    @property
    def size(self):
        return 0 if self.index is None else int(self.index.ntotal)

    def products(self):
        return sorted({r["product"] for r in self.records})

    def search(self, question, top_k=5, min_score=0.25, product=None):
        """Return the best matching reviews, highest similarity first."""
        question = clean_text(question)
        if not question or self.size == 0:
            return []

        top_k = max(1, min(int(top_k), MAX_TOP_K))
        min_score = float(min_score)
        wanted = (product or "").strip().lower()

        scores, ids = self.index.search(embed([question]), self.size)
        hits = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            if score < min_score:
                break                       # results are sorted, so the rest are lower
            rec = self.records[int(idx)]
            if wanted and rec["product"].lower() != wanted:
                continue
            hit = dict(rec)
            hit["score"] = round(float(score), 3)
            hits.append(hit)
            if len(hits) >= top_k:
                break
        return hits
