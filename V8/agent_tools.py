import json
import math
import time
from collections import Counter

from analytics import product_stats

MAX_VALUES = 1000

CATEGORY_KEYWORDS = {
    "delivery": ["deliver", "late", "shipping", "shipped", "parcel", "package", "arrive"],
    "customer support": ["support", "service", "refund", "staff", "helpdesk", "nobody helped", "response"],
    "battery": ["battery", "charge", "charging"],
    "overheating": ["hot", "heat", "overheat", "warm"],
    "durability / defects": ["stopped working", "broke", "cracked", "crack", "defect", "faulty", "died", "damaged"],
    "performance": ["laggy", "lag ", "freez", "crash", "hang"],
    "price / value": ["expensive", "overpriced", "waste of money", "not worth", "price"],
}


def categorize(text):
    lower = str(text).lower()
    found = [cat for cat, words in CATEGORY_KEYWORDS.items() if any(w in lower for w in words)]
    return found or ["other"]


class ToolBox:
    """The five tools. Every number is calculated here in Python."""

    def __init__(self, results, index):
        self.results = results
        self.index = index
        self.products = sorted({str(p) for p in results["product"]})

    def _check_product(self, product):
        if not product:
            return None
        for p in self.products:
            if p.lower() == str(product).strip().lower():
                return p
        raise ValueError("Unknown product '" + str(product)[:40] + "'. Known products: " + ", ".join(self.products))

    def calculate_average(self, values):
        if not isinstance(values, list) or not values:
            raise ValueError("values must be a non-empty list of numbers")
        if len(values) > MAX_VALUES:
            raise ValueError("Too many values (max " + str(MAX_VALUES) + ")")
        nums = []
        for v in values:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError("values must contain only finite numbers")
            nums.append(float(v))
        return {"average": round(sum(nums) / len(nums), 3), "count": len(nums)}

    def get_business_kpis(self):
        df = self.results
        total = len(df)
        counts = df["sentiment"].value_counts()
        out = {"total_reviews": total}
        for label in ("positive", "negative", "neutral"):
            n = int(counts.get(label, 0))
            out[label + "_count"] = n
            out[label + "_pct"] = round(n * 100 / total, 1)
        out["average_score"] = round(float(df["score"].mean()), 2) + 0.0
        return out

    def get_product_performance(self, product=None):
        product = self._check_product(product)
        rows = product_stats(self.results)
        if product:
            rows = [r for r in rows if r["product"] == product]
        return {"products": rows}

    def get_complaint_analysis(self, product=None):
        product = self._check_product(product)
        df = self.results
        neg = df[df["sentiment"] == "negative"]
        if product:
            neg = neg[neg["product"] == product]
        counter = Counter()
        by_product = {}
        examples = {}
        for _, row in neg.iterrows():
            for cat in categorize(row["feedback"]):
                counter[cat] += 1
                by_product.setdefault(cat, Counter())[str(row["product"])] += 1
                examples.setdefault(cat, [])
                if len(examples[cat]) < 2:
                    examples[cat].append(str(row["feedback"])[:160])
        cats = [{"category": c, "negative_reviews": n,
                 "by_product": dict(by_product[c]), "examples": examples[c]}
                for c, n in counter.most_common()]
        return {"negative_reviews_analyzed": int(len(neg)), "categories": cats,
                "method": "rule-based keywords; one review can fall in several categories"}

    def search_customer_feedback(self, query, product=None, top_k=5, min_score=0.25):
        product = self._check_product(product)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        top_k = min(max(int(top_k), 1), 10)
        min_score = min(max(float(min_score), 0.0), 1.0)
        hits = self.index.search(query, top_k=top_k, min_score=min_score, product=product)
        return {"retrieval_backend": "all-MiniLM-L6-v2 + FAISS IndexFlatIP",
                "matches": [{"ref": h["ref"], "product": h["product"], "sentiment": h["sentiment"],
                             "similarity": h["score"], "review": h["feedback"]} for h in hits],
                "note": "Similarity measures topic, not whether a review is a complaint."}


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "calculate_average",
        "description": "Average of a list of numbers. Use this instead of doing arithmetic yourself.",
        "parameters": {"type": "object", "properties": {
            "values": {"type": "array", "items": {"type": "number"}, "description": "Numbers to average"}},
            "required": ["values"]}}},
    {"type": "function", "function": {
        "name": "get_business_kpis",
        "description": "Overall KPIs: review count, positive/negative/neutral counts and percentages, average sentiment score.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_product_performance",
        "description": "Per-product sentiment counts, percent negative and average score. Optional product filter.",
        "parameters": {"type": "object", "properties": {
            "product": {"type": "string", "description": "Optional product name"}}}}},
    {"type": "function", "function": {
        "name": "get_complaint_analysis",
        "description": "Groups negative reviews into complaint categories (delivery, support, battery, etc.) with counts and example reviews. Optional product filter.",
        "parameters": {"type": "object", "properties": {
            "product": {"type": "string", "description": "Optional product name"}}}}},
    {"type": "function", "function": {
        "name": "search_customer_feedback",
        "description": "Semantic search over review text. Returns matching reviews with reference ids, sentiment and similarity. Use for quotes and evidence.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "What to look for"},
            "product": {"type": "string", "description": "Optional product name"},
            "top_k": {"type": "integer", "description": "1 to 10, default 5"},
            "min_score": {"type": "number", "description": "Minimum cosine similarity 0 to 1, default 0.25"}},
            "required": ["query"]}}},
]

TOOL_NAMES = [t["function"]["name"] for t in TOOL_SCHEMAS]


def run_tool(toolbox, name, raw_args):
    """Run one tool. Returns (result_dict, trace_entry). Never raises."""
    start = time.perf_counter()
    status = "ok"
    try:
        if name not in TOOL_NAMES:
            raise ValueError("Unknown tool '" + str(name)[:40] + "'")
        if isinstance(raw_args, str):
            args = json.loads(raw_args) if raw_args.strip() else {}
        else:
            args = raw_args or {}
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be a JSON object")
        result = getattr(toolbox, name)(**args)
    except json.JSONDecodeError:
        status, result = "error", {"error": "Arguments were not valid JSON"}
    except TypeError as exc:
        status, result = "error", {"error": "Bad arguments: " + str(exc)[:120]}
    except ValueError as exc:
        status, result = "error", {"error": str(exc)[:200]}
    except Exception as exc:
        status, result = "error", {"error": "Tool failed (" + type(exc).__name__ + ")"}
    ms = round((time.perf_counter() - start) * 1000, 1)
    shown = raw_args if isinstance(raw_args, str) else json.dumps(raw_args or {})
    trace = {"tool": str(name)[:60], "status": status, "duration_ms": ms, "arguments": shown[:200]}
    return result, trace
