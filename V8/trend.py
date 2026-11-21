import numpy as np
import pandas as pd

MIN_DATED = 20
MIN_WEEKS = 5
METHOD = ("Straight-line trend (numpy least squares) through weekly negative-review percentages. "
          "It extends the recent direction by one week. It is an estimate, not a guarantee.")


def weekly_series(df, min_per_week):
    d = df[df["date"].astype(str) != ""].copy()
    d["week"] = pd.to_datetime(d["date"]).dt.to_period("W-SUN").dt.start_time
    out = []
    for week, grp in d.groupby("week"):
        n = len(grp)
        if n < min_per_week:
            continue
        neg = int((grp["sentiment"] == "negative").sum())
        out.append({"week": week.strftime("%Y-%m-%d"), "reviews": n,
                    "negative_pct": round(neg * 100 / n, 1)})
    return out


def forecast(df, product=None, min_per_week=3):
    """Returns (result_dict_or_None, reason). Never raises for missing or thin data."""
    if "date" not in df.columns:
        return None, "No 'date' column in the CSV, so a trend cannot be calculated."
    d = df if not product else df[df["product"] == product]
    dated = int((d["date"].astype(str) != "").sum())
    if dated < MIN_DATED:
        return None, "Only %d dated reviews, need at least %d." % (dated, MIN_DATED)
    series = weekly_series(d, min_per_week)
    if len(series) < MIN_WEEKS:
        return None, "Only %d weeks have %d+ reviews, need at least %d weeks." % (
            len(series), min_per_week, MIN_WEEKS)

    weeks = pd.to_datetime([s["week"] for s in series])
    x = np.array([(w - weeks[0]).days / 7 for w in weeks], dtype=float)
    y = np.array([s["negative_pct"] for s in series], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    ss_res = float(((y - fitted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    spread = float(np.std(y - fitted, ddof=2))
    nxt_x = x[-1] + 1
    nxt = float(np.clip(slope * nxt_x + intercept, 0, 100))
    low = float(np.clip(nxt - 1.5 * spread, 0, 100))
    high = float(np.clip(nxt + 1.5 * spread, 0, 100))
    direction = "no clear trend" if r2 < 0.3 else ("flat" if abs(slope) < 1 else ("rising" if slope > 0 else "falling"))
    return {
        "product": product or "All products",
        "weeks_used": len(series),
        "series": series,
        "slope_per_week": round(float(slope), 2),
        "direction": direction,
        "r_squared": round(r2, 2),
        "trend_strength": "weak" if r2 < 0.3 else "moderate" if r2 < 0.6 else "stronger",
        "next_week_negative_pct": round(nxt, 1),
        "rough_range": [round(low, 1), round(high, 1)],
        "method": METHOD,
    }, ""

