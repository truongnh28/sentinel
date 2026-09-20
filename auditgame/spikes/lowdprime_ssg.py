"""Cau hoi song con: o d' ~ 0, minimax LP co thang baseline khong?

VI SAO CAU HOI NAY PHAN DINH HUONG LUAN VAN.  Phep do noi dung 20/09 cho:
duoi tan cong NGAM voi ten ham trung tinh, ca D_lex lan D_llm o muc ngau
nhien (0,479 / 0,518) => d' ~ 0,06.  Tuc trong che do de doa thuc te nhat,
detector KHONG cho tin hieu nao.

O d' = 0 khong con tin hieu, nen phong thu thuan tuy la CAM KET + NGAU NHIEN
HOA truoc mot doi thu chien luoc -- dung cho ly thuyet tro choi phai manh
nhat.  Hai ket cuc, ca hai deu la ket qua:

  B7 thang  => co luan diem SSG that su, dung o che do de doa thuc te
  B1 da toi uu => baseline ngay tho da la minimax-optimal cho cau truc nay,
                  mot ket qua PHU DINH nhung la dinh ly, va cung dang mot chuong

Doi thu: worst_case lay MAX qua (Delta, carrier) -- dung nghia minimax cua
ben tan cong, khong phai trung binh.
"""
from __future__ import annotations
import json, pathlib, sys, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agent, attacks, detector as DT, metrics, runner   # noqa: E402
import dprime_sweep as DS                                # noqa: E402

D_PRIMES = (0.0, 0.2, 0.5, 1.0, 2.2)
POLICIES = ("B1 audit-at-commit", "B5 risk-score", "Sentinel",
            "B7 minimax-lp", "B7U minimax-lp upstream")
DELTAS = (0, 2, 4)
CARRIERS = tuple(sorted(attacks.CARRIERS_ALL))
SEEDS = (1, 2, 3)
BUDGET = 17.95
SETTING = "mid"
N_WF = 40
H = 8


def main() -> int:
    wfs = DS.make_corpus(N_WF, H, seed=DS.CORPUS_SEED)
    ag = agent.MockAgent()
    out = {"meta": {"d_primes": list(D_PRIMES), "policies": list(POLICIES),
                    "deltas": list(DELTAS), "seeds": list(SEEDS),
                    "budget": BUDGET, "n_wf": len(wfs), "setting": SETTING,
                    "attacker": "worst_case = MAX qua (Delta, carrier)"},
           "cells": []}
    for dp in D_PRIMES:
        det = DS.make_detector(dp)
        row = {}
        for pol in POLICIES:
            runner.reset_survivor_cache()
            t0 = time.time()
            c = runner.worst_case(pol, wfs, DELTAS, CARRIERS, det, ag,
                                  BUDGET, SEEDS, SETTING)
            row[pol] = {"harm": c.harm, "q_false": c.q_false,
                        "t_lost": c.t_lost, "spent": c.spent_mean,
                        "n_feasible": c.n_feasible, "n_total": c.n_total,
                        "L0": metrics.loss(c.harm, c.q_false, c.t_lost,
                                           lambda_Q=0.0, lambda_T=0.0),
                        "L10": metrics.loss(c.harm, c.q_false, c.t_lost,
                                            lambda_Q=0.10, lambda_T=0.0)}
            print("  d'=%.1f %-26s harm=%.4f L0=%.4f L10=%.4f (%.0fs)"
                  % (dp, pol, c.harm, row[pol]["L0"], row[pol]["L10"],
                     time.time() - t0), flush=True)
        out["cells"].append({"d_prime": dp, "policies": row})
    (HERE / "lowdprime-ssg.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> spikes/lowdprime-ssg.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
