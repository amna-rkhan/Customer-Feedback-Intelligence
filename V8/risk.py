from agent_tools import categorize
from analytics import product_stats

WEIGHTS = {"negative_share": 50, "weak_score": 30, "complaint_variety": 20}
MIN_REVIEWS = 5
METHOD = ("Heuristic risk score (0-100) = 50% negative share + 30% weak average sentiment + "
          "20% variety of complaint categories. It is an estimate, not a trained model.")


def risk_level(score):
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def product_risk(results):
    """Returns a list of dicts, highest risk first. All numbers are calculated in Python."""
    stats = {s["product"]: s for s in product_stats(results)}
    rows = []
    for product, g in results.groupby("product"):
        s = stats.get(product)
        if s is None:
            continue
        cats = set()
        for text in g[g["sentiment"] == "negative"]["feedback"]:
            for c in categorize(text):
                if c != "other":
                    cats.add(c)
        neg_part = s["negative_pct"] / 100 * WEIGHTS["negative_share"]
        score_part = (1 - s["avg_score"]) / 2 * WEIGHTS["weak_score"]
        variety_part = min(len(cats), 4) / 4 * WEIGHTS["complaint_variety"]
        total = round(neg_part + score_part + variety_part, 1)
        rows.append({
            "product": str(product),
            "reviews": s["total"],
            "negative_pct": s["negative_pct"],
            "avg_score": s["avg_score"],
            "complaint_categories": sorted(cats),
            "risk_score": total,
            "risk_level": risk_level(total),
            "confidence": "low (fewer than %d reviews)" % MIN_REVIEWS if s["total"] < MIN_REVIEWS else "ok",
        })
    rows.sort(key=lambda r: r["risk_score"], reverse=True)
    return rows
