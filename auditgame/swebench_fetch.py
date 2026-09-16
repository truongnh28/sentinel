"""
swebench_fetch.py -- Download SWE-bench metadata into a local JSONL file.

Network I/O only, no analysis -- kept separate so every later step runs OFFLINE and
reproducibly, and so no test ever depends on the network.

Uses HuggingFace's datasets-server rather than the `datasets` library: that library
pulls in pyarrow + numpy, which the measurement core deliberately does not have.
"""
from __future__ import annotations
import json, os, pathlib, sys, time, urllib.parse, urllib.request

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
    """Download a whole split to JSONL, one instance per line. Returns the line count.

    Two ways this silently produced a SHORT FILE that still parses, which is the
    worst shape of failure here: every consumer downstream (topics.distribution,
    SWEBenchDataset.stats, the pinned 500 / 12 / 10 / 58 / 42% numbers) reads the
    file without ever learning it is a truncation rather than the dataset.

      1. The output was opened with "w" BEFORE the download loop, so a failure at
         page 30 of 50 left a valid-looking 3000-line JSONL where the previous
         complete file used to be. Written to a sibling ".part" and moved into
         place with os.replace only after the last page, an interrupted download
         leaves the previous file untouched and the partial one obviously named.

      2. `_get(...).get("rows", [])` read an ERROR PAYLOAD as end-of-data: the
         datasets-server answers a rate-limited or malformed request with a JSON
         body carrying "error", no "rows", and the loop treated that as "the
         split ended here" and returned a short count as if it were the whole
         thing. A response with no "rows" key is now an exception. An EMPTY
         "rows" list still means end-of-split -- that is the real terminator.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_suffix(out.suffix + ".part")
    n, offset = 0, 0
    try:
        with part.open("w", encoding="utf-8") as f:
            while True:
                q = urllib.parse.urlencode(
                    {"dataset": dataset, "config": "default", "split": split,
                     "offset": offset, "length": PAGE})
                payload = _get(f"{API}?{q}")
                if "rows" not in payload:
                    raise RuntimeError(
                        f"datasets-server returned no 'rows' key at offset "
                        f"{offset} after {n} rows: {str(payload)[:300]}. That is "
                        f"an error payload, not the end of the split -- treating "
                        f"it as the end would write a SHORT file that still "
                        f"parses.")
                rows = payload["rows"]
                if not rows:
                    break
                for r in rows:
                    f.write(json.dumps(r["row"], ensure_ascii=False) + "\n")
                    n += 1
                offset += PAGE
        os.replace(part, out)          # atomic: out is complete or untouched
    finally:
        part.unlink(missing_ok=True)   # no-op once os.replace has moved it
    return n


def main() -> int:
    for label, (ds, split) in DATASETS.items():
        out = DATA / f"swebench_{label}.jsonl"
        print(f"  {label:9s} {fetch(ds, split, out):>5d} instances -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
