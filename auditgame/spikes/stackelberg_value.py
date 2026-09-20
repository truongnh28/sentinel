"""Gia tri Stackelberg that su: attacker CAM KET mot chien luoc thuan.

VI SAO KHAC `runner.worst_case`.  worst_case lay MAX qua (Delta, carrier)
RIENG TUNG WORKFLOW -- tuc attacker duoc nhin tung workflow roi moi chon, 64
lan thu moi workflow.  Cho ai do 64 lan thu thi hau nhu luc nao cung co mot
lo, va do la ly do moi con so o do deu sat 1,0.

Mo hinh Stackelberg o Phu luc F.1 noi khac: follower best-respond bang mot
CHIEN LUOC THUAN, cam ket MOT (Delta, carrier) cho ca tap workflow.  Quy uoc
nay da co san trong repo -- `runner.best_response_gap` trung binh qua workflow
BEN TRONG moi cau hinh roi moi lay max:

    V(pi) = max_{(Delta,k)}  E_wf[ harm(pi, Delta, k, wf) ]

Do la gia tri ma ben phong thu that su phai chiu truoc mot attacker chien
luoc, va la con so dung de so sanh cac chinh sach.

LUAT MAU SO (van ban detector SS7.1): mau so phai nam cung LOP CAM KET voi dai
luong dang do.  O day ca nam chinh sach deu bi do bang cung mot lop cam ket
cua attacker, nen so sanh la cong bang.
"""
from __future__ import annotations
import json, pathlib, random, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agent, attacks, build, metrics, runner   # noqa: E402
import dprime_sweep as DS                       # noqa: E402
from runner import seed_of, paired              # noqa: E402

D_PRIMES = (0.0, 0.2, 0.5, 1.0, 2.2)
POLICIES = ("B1 audit-at-commit", "B5 risk-score", "Sentinel",
            "B7 minimax-lp", "B7U minimax-lp upstream")
DELTAS = (0, 2, 4)
CARRIERS = tuple(sorted(attacks.CARRIERS_ALL))
SEEDS = (1, 2, 3)
BUDGET, SETTING, N_WF, H = 17.95, "mid", 40, 8


def stackelberg_value(policy_name, wfs, det, ag) -> dict:
    """max qua cau hinh cua TRUNG BINH qua workflow -- cam ket chien luoc thuan."""
    best = None
    per_cfg = {}
    for d in DELTAS:
        for k in CARRIERS:
            hs, qs, ts = [], [], []
            for wf in wfs:
                ps = build.plan_poison(wf, k, d, random.Random(seed_of(wf.wf_id, d, k)))
                if ps is None:
                    continue
                for s in SEEDS:
                    r = paired(wf, ps, policy_name, det, ag, s, BUDGET, SETTING)
                    if r is None:
                        continue
                    hs.append(r.harm); qs.append(r.false_quarantine); ts.append(r.t_lost)
            if not hs:                      # N3: khong cau hinh nao dung duoc
                per_cfg[f"{k}|{d}"] = None
                continue
            m = sum(hs) / len(hs)
            cell = {"harm": m, "q_false": sum(qs) / len(qs),
                    "t_lost": sum(ts) / len(ts), "n": len(hs)}
            per_cfg[f"{k}|{d}"] = cell
            if best is None or m > best["harm"]:
                best = dict(cell, carrier=k, delta=d)
    if best is None:
        return {"value": None, "reason": "khong cau hinh nao kha thi"}
    return {"value": best["harm"], "carrier": best["carrier"],
            "delta": best["delta"], "q_false": best["q_false"],
            "t_lost": best["t_lost"], "n": best["n"], "per_config": per_cfg}


def main() -> int:
    wfs = DS.make_corpus(N_WF, H, seed=DS.CORPUS_SEED)
    ag = agent.MockAgent()
    out = {"meta": {"d_primes": list(D_PRIMES), "policies": list(POLICIES),
                    "deltas": list(DELTAS), "seeds": list(SEEDS),
                    "budget": BUDGET, "n_wf": len(wfs),
                    "attacker": "CAM KET chien luoc thuan: max_cfg E_wf[harm]"},
           "cells": []}
    for dp in D_PRIMES:
        det = DS.make_detector(dp)
        row = {}
        for pol in POLICIES:
            runner.reset_survivor_cache()
            t0 = time.time()
            v = stackelberg_value(pol, wfs, det, ag)
            v["L0"] = metrics.loss(v["value"], v["q_false"], v["t_lost"],
                                   lambda_Q=0.0, lambda_T=0.0)
            v["L10"] = metrics.loss(v["value"], v["q_false"], v["t_lost"],
                                    lambda_Q=0.10, lambda_T=0.0)
            row[pol] = v
            print("  d'=%.1f %-26s V=%.4f L10=%.4f  BR=(%s,D=%d)  (%.0fs)"
                  % (dp, pol, v["value"], v["L10"], v["carrier"], v["delta"],
                     time.time() - t0), flush=True)
        out["cells"].append({"d_prime": dp, "policies": row})
    (HERE / "stackelberg-value.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> spikes/stackelberg-value.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
