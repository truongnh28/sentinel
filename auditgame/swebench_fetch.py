"""
swebench_fetch.py -- Download SWE-bench metadata into a local JSONL file.

Network I/O only, no analysis -- kept separate so every later step runs OFFLINE and
reproducibly, and so no test ever depends on the network.

Uses HuggingFace's datasets-server rather than the `datasets` library: that library
pulls in pyarrow + numpy, which the measurement core deliberately does not have.
"""
from __future__ import annotations
import json, pathlib, sys, time, urllib.parse, urllib.request

API = "https://datasets-server.huggingface.co/rows"
PAGE = 100                                   # datasets-server ceiling (verified)

DATASETS = {
    "verified": ("princeton-nlp/SWE-bench_Verified", "test"),
    "full":     ("princeton-nlp/SWE-bench", "test"),
}

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"


def _get(url: str, tries: int = 4) -> dict:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)
    raise RuntimeError("unreachable")


def fetch(dataset: str, split: str, out: pathlib.Path) -> int:
    """Download a whole split to JSONL, one instance per line. Returns the line count."""
    out.parent.mkdir(parents=True, exist_ok=True)
    n, offset = 0, 0
    with out.open("w", encoding="utf-8") as f:
        while True:
            q = urllib.parse.urlencode(
                {"dataset": dataset, "config": "default", "split": split,
                 "offset": offset, "length": PAGE})
            rows = _get(f"{API}?{q}").get("rows", [])
            if not rows:
                break
            for r in rows:
                f.write(json.dumps(r["row"], ensure_ascii=False) + "\n")
                n += 1
            offset += PAGE
    return n


def main() -> int:
    for label, (ds, split) in DATASETS.items():
        out = DATA / f"swebench_{label}.jsonl"
        print(f"  {label:9s} {fetch(ds, split, out):>5d} instances -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
