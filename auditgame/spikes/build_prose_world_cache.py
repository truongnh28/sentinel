"""Cham DIEM moi chuoi co the xuat hien trong the gioi van xuoi -- offline, mot lan."""
from __future__ import annotations
import concurrent.futures, json, pathlib, sys, threading

HERE = pathlib.Path(__file__).resolve().parent
AUDITGAME = HERE.parent
sys.path.insert(0, str(AUDITGAME))
import importlib.util as _u
_sp = _u.spec_from_file_location("_scale", AUDITGAME / "payloads" / "gen_payload_scale.py")
_scale = _u.module_from_spec(_sp); _sp.loader.exec_module(_scale)
from spikes.gen_attacker_llm_a1a2 import Usage, _complete_json   # noqa: E402
from analysis import content_judge as J                          # noqa: E402
import prose_world as PW                                         # noqa: E402

BATCH, WORKERS, COST_CAP = 20, 8, 4.0


def main() -> int:
    pos, neg = PW.judgeable_texts()
    cache = J.load_cache()
    todo = sorted({t for t in pos + neg if J.key(t) not in cache})
    print(f"the gioi: {len(pos)} payload + {len(neg)} lanh | can cham {len(todo)}")
    if not todo:
        print("cache da du"); return 0
    client = _scale.make_client()
    usage, lock = Usage(), threading.Lock()
    chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]

    def run(ch):
        items = "\n".join(f"{i+1}. {t}" for i, t in enumerate(ch))
        return ch, _complete_json(client, J.JUDGE_PROMPT.format(n=len(ch), items=items),
                                  "judge", usage, _scale.MAX_TOKENS_CONTENT, 0.0)

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for ch, (parsed, why) in ex.map(run, chunks):
            if parsed and len(parsed) == len(ch):
                with lock:
                    for t, v in zip(ch, parsed):
                        try:
                            cache[J.key(t)] = float(v)
                        except (TypeError, ValueError):
                            pass
            done += 1
            with lock:
                c = usage.totals()["cost_usd_est"]
            if done % 20 == 0:
                print(f"  {done}/{len(chunks)} lo (USD {c:.4f})", flush=True)
            if c >= COST_CAP:
                print("  DUNG: cham tran", flush=True); break
    pathlib.Path(J.CACHE_PATH).write_text(json.dumps(cache, ensure_ascii=False),
                                          encoding="utf-8")
    print(f"cache {len(cache)} khoa, USD {usage.totals()['cost_usd_est']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
