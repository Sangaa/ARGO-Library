"""Local deterministic lexical retrieval; no network, no learning claim."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def tokens(s):
    return set(re.findall(r"\w+", s.casefold()))

def search(query, root=ROOT, limit=5):
    q = tokens(query)
    results = []
    for p in sorted((root / "cards").glob("*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        score = 3 * len(q & tokens(" ".join(c["mechanisms"]))) + 2 * len(q & tokens(c["title"])) + len(q & tokens(" ".join(c[k] for k in ("problem", "failure", "correction", "transfer"))))
        if score:
            results.append((score, c))
    return sorted(results, key=lambda x: (-x[0], x[1]["id"]))[:limit]

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("query")
    a.add_argument("--limit", type=int, default=5)
    args = a.parse_args()
    for score, card in search(args.query, limit=args.limit):
        print(json.dumps({"score": score, **card}, ensure_ascii=False))
