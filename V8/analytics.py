def product_stats(results):
    """Per-product numbers, calculated in Python (never by the LLM)."""
    rows = []
    for product, g in results.groupby("product"):
        total = len(g)
        counts = g["sentiment"].value_counts()
        pos = int(counts.get("positive", 0))
        neg = int(counts.get("negative", 0))
        neu = int(counts.get("neutral", 0))
        rows.append({
            "product": product,
            "total": total,
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "negative_pct": round(neg * 100 / total, 1),
            "avg_score": round(float(g["score"].mean()), 2) + 0.0,
        })
    rows.sort(key=lambda r: r["avg_score"], reverse=True)
    return rows
