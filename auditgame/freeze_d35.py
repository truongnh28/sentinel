"""freeze_d35.py -- the D35 addendum's own freeze (preregistration D35).

The base freeze (freeze.py, frozen/MANIFEST.json, sha256:c789fa7362e0) must stay clean; this
manifest pins what the addendum adds on top of it: its module, its dev-tuned table and its names.
    python3 -c "import costs, policies as P, freeze_d35; costs.install(P); print(freeze_d35.write())"
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import freeze

ROOT = pathlib.Path(__file__).resolve().parent
PATH = ROOT / "frozen" / "MANIFEST-D35.json"
FILES = ("addendum_d35.py", "reference/d35_tuned.json", "tools/run_d35.py")
KEYS = ("base_digest", "arms", "fixed_library", "dhat", "p_grid")


def manifest() -> dict:
    import addendum_d35 as X
    base = freeze.load()
    return {"base_digest": base["digest"] if base else None,
            "files": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES},
            "arms": sorted(X.ARMS),
            "fixed_library": sorted(X.FIXED_LIBRARY),
            "dhat": {n: {str(k): v for k, v in sorted(m.items())} for n, m in sorted(X.DHAT.items())},
            "p_grid": list(X.P_GRID)}


def digest(man: dict) -> str:
    return hashlib.sha256(json.dumps(man, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write(path: pathlib.Path = PATH) -> str:
    man = manifest()
    man["digest"] = digest(man)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return man["digest"]


def load(path: pathlib.Path = PATH) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def drift(path: pathlib.Path = PATH) -> list:
    frozen = load(path)
    if frozen is None:
        return ["no D35 manifest: nothing has been frozen"]
    live, out = manifest(), []
    for key in KEYS:
        if frozen.get(key) != live.get(key):
            out.append(f"{key}: changed")
    for f in sorted(set(frozen.get("files", {})) | set(live["files"])):
        if frozen.get("files", {}).get(f) != live["files"].get(f):
            out.append(f"files/{f}: changed")
    return out


def header_line(path: pathlib.Path = PATH) -> str:
    """Both freezes in one line; call costs.install(policies) first, as every run does."""
    base = freeze.header_line()
    frozen = load(path)
    if frozen is None:
        return f"freeze-d35: NONE  |  base {base}"
    d = drift(path)
    if d:
        return (f"freeze-d35: DRIFTED from sha256:{frozen['digest'][:12]} in {len(d)} place(s): "
                f"{'; '.join(d[:3])}  |  base {base}")
    return f"freeze-d35: clean sha256:{frozen['digest'][:12]}  |  base {base}"


def clean(line: str) -> bool:
    return (line.startswith("freeze-d35: clean") and "base freeze: clean" in line
            and "PIN CONFLICT" not in line)
