"""Xay cache cho D_llm -- OFFLINE, mot lan, roi dong bang."""
from __future__ import annotations
import concurrent.futures, json, pathlib, random, sys, threading

HERE = pathlib.Path(__file__).resolve().parent
AUDITGAME = HERE.parent
sys.path.insert(0, str(AUDITGAME))
import importlib.util as _u
_sp = _u.spec_from_file_location("_scale", AUDITGAME / "payloads" / "gen_payload_scale.py")
_scale = _u.module_from_spec(_sp); _sp.loader.exec_module(_scale)
from spikes.gen_attacker_llm_a1a2 import Usage, _complete_json   # noqa: E402
from analysis import content_judge as J, prose_corpus as PC      # noqa: E402

N_SAMPLE = 300          # moi lop moi dieu kien
BATCH = 20
WORKERS = 8
COST_CAP = 3.0


def main() -> int:
    client = _scale.make_client()
    usage, lock = Usage(), threading.Lock()
    cache = J.load_cache()
    rng = random.Random(20260920)
    todo = []
    for cond in ("paired", "covert"):
        pos, neg = PC.pair(cond)
        for xs in (pos, neg):
            for t in rng.sample(xs, min(N_SAMPLE, len(xs))):
                if J.key(t) not in cache:
                    todo.append(t)
    todo = sorted(set(todo))
    print(f"can cham {len(todo)} ban ghi")
    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]

    def run(ch):
        items = "\n".join(f"{i+1}. {t}" for i, t in enumerate(ch))
        p = J.JUDGE_PROMPT.format(n=len(ch), items=items)
        return ch, _complete_json(client, p, "judge", usage,
                                  _scale.MAX_TOKENS_CONTENT, 0.0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for ch, (parsed, why) in ex.map(run, chunks):
            if not parsed or len(parsed) != len(ch):
                print(f"  lo hong ({why}), bo qua {len(ch)}", flush=True)
                continue
            with lock:
                for t, v in zip(ch, parsed):
                    try:
                        cache[J.key(t)] = float(v)
                    except (TypeError, ValueError):
                        pass
            with lock:
                c = usage.totals()["cost_usd_est"]
            if c >= COST_CAP:
                print("  DUNG: cham tran", flush=True); break
    pathlib.Path(J.CACHE_PATH).write_text(
        json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"cache {len(cache)} khoa, USD {usage.totals()['cost_usd_est']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
