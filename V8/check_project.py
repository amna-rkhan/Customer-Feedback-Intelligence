import os
import re

ROOT = os.path.abspath("..")
checks = []


def record(name, ok, detail=""):
    checks.append(ok)
    print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail))


needed = ["app.py", "analysis.py", "analytics.py", "executive_report.py", "chatbot.py",
          "executive_deck.py", "rag_engine.py", "rag_answer.py", "rag_routes.py",
          "agent_tools.py", "agent.py", "agent_routes.py", "requirements.txt",
          ".env", ".env.example", "sample_data/reviews_big.csv",
          "templates/index.html", "templates/rag.html", "templates/agent.html",
          "static/chart.umd.min.js"]
missing = [f for f in needed if not os.path.exists(f)]
record("Required files exist", not missing, ("missing: " + ", ".join(missing)) if missing else "")

gi_path = os.path.join(ROOT, ".gitignore")
gi = open(gi_path, encoding="utf-8-sig").read() if os.path.exists(gi_path) else ""
record(".gitignore has .env", re.search(r"^\.env\s*$", gi, re.M) is not None)
record(".gitignore has .venv", ".venv" in gi)

example = open(".env.example", encoding="utf-8-sig").read()
bad_example = []
for line in example.splitlines():
    if "=" in line and not line.strip().startswith("#"):
        value = line.split("=", 1)[1].strip()
        if value and not ("your-" in value or "placeholder" in value.lower()):
            bad_example.append(line.split("=", 1)[0])
record(".env.example has placeholders only", not bad_example,
       ("check: " + ", ".join(bad_example)) if bad_example else "")

secrets = []
for line in open(".env", encoding="utf-8-sig").read().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        v = line.split("=", 1)[1].strip().strip('"').strip("'")
        if len(v) >= 20 and "your-" not in v:
            secrets.append(v)

leaks = []
for folder, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".venv", "__pycache__", "outputs", "index_cache")]
    for f in files:
        if f == ".env" or not f.endswith((".py", ".html", ".txt", ".example", ".bak", ".csv")):
            continue
        try:
            text = open(os.path.join(folder, f), encoding="utf-8-sig", errors="ignore").read()
        except OSError:
            continue
        if any(s in text for s in secrets):
            leaks.append(os.path.join(folder, f))
record("No .env value copied into other files", not leaks,
       ("found in: " + ", ".join(leaks)) if leaks else "(checked %d secret value(s))" % len(secrets))

import app as flask_app

rules = sorted(str(r.rule) for r in flask_app.app.url_map.iter_rules() if r.endpoint != "static")
wanted = ["/", "/download/<download_id>", "/report/<download_id>", "/chat/<download_id>",
          "/deck/<download_id>", "/rag/<download_id>", "/rag/<download_id>/ask",
          "/agent/<download_id>", "/agent/<download_id>/ask"]
absent = [w for w in wanted if w not in rules]
record("All Flask routes registered", not absent, ("missing: " + ", ".join(absent)) if absent else "")

print("\nSUMMARY: %d of %d checks passed" % (sum(checks), len(checks)))

