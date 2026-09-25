# D35 Addendum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the preregistered D35 addendum and run it exactly once on the eval split, under its own freeze, without changing any number of the main run. D35 has three secondary arms:
- a wrong Δ̂ given to line 1;
- B2 with its commit probability tuned to Sentinel's dev FQ;
- the best fixed-phase interleaved schedule.

**Architecture:** Everything new lives in new files:
- `addendum_d35.py`: the systems;
- `tools/tune_d35.py`: dev tuning into `reference/d35_tuned.json`;
- `freeze_d35.py`: a second manifest on top of the frozen base;
- `tools/run_d35.py`: records, reproduction check, summary.

These files import the frozen v2 code (`sentinel`, `carrier_policies`, `select_mixture`, `run_draft_eval`) and never edit it. So `freeze.header_line()` stays `freeze: clean sha256:c789fa7362e0`.

**Tech Stack:** Python 3.14 (`../.venv/bin/python` from `auditgame/`), unittest, scipy is not needed for the new code.

**Source of truth for the design:** decision D35 in `docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md` (EN mirror: `docs/preregistration/v2-preregistration-EN.md`). If this plan and D35 disagree, D35 governs; stop and report.

## Global Constraints

- **Frozen code.** Never edit a file in `freeze.SOURCE` or `freeze.TABLES`, and never edit `tools/run_draft_eval.py` or `tools/select_mixture.py`.
  - Their sha256 values are pinned. Import them only.
  - After every commit, `cd auditgame && ../.venv/bin/python -c "import costs, policies as P, freeze; costs.install(P); print(freeze.header_line())"` must print `freeze: clean sha256:c789fa7362e0`.
- **Frozen counts.** `len(sentinel.REGISTRY) == 13` and `len(carrier_policies.LIBRARY) == 28` stay true. Addendum names never enter those registries.
- **No eval before the freeze.** Nothing touches the eval split before Task 5. The dev split (django) is the only data used for tuning, tests and the pilot.
  - Never open `auditgame/spikes/v2-pilot/eval-touch-2509/`.
  - Never write into `auditgame/spikes/v2/`.
- **Outputs.** Record files go only to `auditgame/spikes/v2-addendum/` (eval) and `auditgame/spikes/v2-addendum-dev/` (dev). They are opened with mode `"x"` (never overwritten), and their `*.jsonl` are gitignored.
- **Record labels (exact):**
  - `"A1 dhat-swap"`, `"A1 dhat-down1"`, `"A1 dhat-down2"`, `"B2 FQ-matched"`, `"A1 fixed interleave"`;
  - tuning names `"B2p:<p>"` and `"FI-..."`.
- **Δ̂ table (exact):**
  - swap {4: 8, 8: 4};
  - down1 {4: 2, 8: 4};
  - down2 {4: 1, 8: 2}.
- **p grid:** 0.25, 0.30, …, 1.00 (16 values).
- **Fixed family (11):**
  - `FI-{c3,c4}-p{1,2}-d{2,3}`: RO with phase 0;
  - `FI-alt-m{2,3,4}`: commit review at depth 3 when `t % m == m - 1`; otherwise sweep memory → queue → skill in turn, at depth 3.
- **Statistics:**
  - 98.75% intervals (`alpha = 0.05 / 4`), 10,000 resamples (the `metrics_v2` default), repo-cluster bootstrap.
  - Each arm is its own family.
- **Commits.** Every commit message ends with the line `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. Commit only the files your task lists.
- **Running tests.** From `auditgame/`: `../.venv/bin/python -m unittest <module> -v`.

---

### Task 1: The addendum's systems (`addendum_d35.py`)

**Files:**
- Create: `auditgame/addendum_d35.py`
- Test: `auditgame/tests/tools/test_d35_policies.py`
- Modify: `.gitignore` (append two lines)

**Interfaces:**
- Consumes:
  - `sentinel.make_policy(name, *, budget, kappa, H, rng_seed, setting, tuned, rho_patch, delta, drift_match=..., attacked=None, eta_q=None)`;
  - `sentinel.cfg_for(tuned, rho)`;
  - `carrier_policies.CarrierPolicy`, `CarrierRotation`, `_Believer`.
- Produces:
  - `DHAT: dict[str, dict[int, int]]`, `B2_FQ: str`, `FIXED: str`, `ARMS: list[str]`, `P_GRID: tuple[float, ...]`, `B2P_PREFIX = "B2p:"`;
  - `FIXED_LIBRARY: dict[str, (cls, kwargs)]`, `D35_TUNED_PATH`, `load_d35(path=D35_TUNED_PATH) -> dict`;
  - `make_policy_d35(name, *, budget, kappa, H, rng_seed, setting, tuned, d35, rho_patch, delta, attacked=None, eta_q=None)`;
  - classes `B2CommitProb`, `FixedRotation`, `FixedAlternation`.
  - `d35` table shape (written by Task 2):
    ```json
    {"b2_fq": {"<rho:g>": {"<delta>": {"p": float, ...}}},
     "fixed": {"<rho:g>": {"<delta>": {"member": str, ...}}}}
    ```

- [ ] **Step 1: Write the failing tests** in `auditgame/tests/tools/test_d35_policies.py`:

```python
"""D35 addendum systems (addendum_d35.py).
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_policies -v"""
import unittest

import addendum_d35 as X
import carrier_policies as CP
import draft_setup as D
import sentinel as S

TUNED = S.load_tuned()
K = D.TARGET_KAPPA_DRAFT


def mk(name, *, seed=7, rho=0.0, delta=4, d35=None, H=14):
    return X.make_policy_d35(name, budget=D.budget_b1(H), kappa=K, H=H, rng_seed=seed,
                             setting="mid", tuned=TUNED, d35=d35 or {}, rho_patch=rho,
                             delta=delta)


class TestB2CommitProb(unittest.TestCase):
    def test_p1_always_commits_p0_never(self):
        one, zero = mk("B2p:1"), mk("B2p:0")
        for t in range(200):
            self.assertEqual(one.act(t), (D.COMMIT, D.MAX_DEPTH))
            k, d = zero.act(t)
            self.assertIn(k, D.SWEEP_CARRIERS)
            self.assertEqual(d, D.MAX_DEPTH)

    def test_commit_share_tracks_p(self):
        pol = mk("B2p:0.6")
        share = sum(pol.act(t)[0] == D.COMMIT for t in range(4000)) / 4000
        self.assertAlmostEqual(share, 0.6, delta=0.03)

    def test_sweeps_cover_all_three_carriers(self):
        pol = mk("B2p:0.25")
        seen = {pol.act(t)[0] for t in range(400)} - {D.COMMIT}
        self.assertEqual(seen, set(D.SWEEP_CARRIERS))

    def test_quarantines_every_firing_item(self):
        pol = mk("B2p:0.5")
        self.assertEqual(pol.remove(0, "memory", [("a", 1.0), ("b", 2.0)], None, []), ["a", "b"])

    def test_the_tuned_arm_reads_p_per_rho_and_delta(self):
        d35 = {"b2_fq": {"0.25": {"4": {"p": 0.7}, "8": {"p": 0.55}}}}
        self.assertEqual(mk(X.B2_FQ, rho=0.25, delta=4, d35=d35).p, 0.7)
        self.assertEqual(mk(X.B2_FQ, rho=0.25, delta=8, d35=d35).p, 0.55)

    def test_p_grid(self):
        self.assertEqual(len(X.P_GRID), 16)
        self.assertEqual(X.P_GRID[0], 0.25)
        self.assertEqual(X.P_GRID[-1], 1.0)
        self.assertIn(0.6, X.P_GRID)


class TestFixedSchedules(unittest.TestCase):
    def test_family_has_eleven_members(self):
        self.assertEqual(len(X.FIXED_LIBRARY), 11)
        self.assertIn("FI-c4-p1-d3", X.FIXED_LIBRARY)
        self.assertIn("FI-alt-m4", X.FIXED_LIBRARY)

    def test_rotation_phase_is_zero_for_every_seed(self):
        a, b = mk("FI-c4-p1-d3", seed=1), mk("FI-c4-p1-d3", seed=99)
        self.assertEqual([a.act(t) for t in range(12)], [b.act(t) for t in range(12)])
        self.assertEqual([a.act(t)[0] for t in range(4)], list(D.TARGETS))

    def test_alternation_m2(self):
        pol = mk("FI-alt-m2")
        self.assertEqual([pol.act(t)[0] for t in range(8)],
                         ["memory", "commit", "queue", "commit", "skill", "commit", "memory", "commit"])
        self.assertTrue(all(pol.act(t)[1] == D.MAX_DEPTH for t in range(8)))

    def test_alternation_m3(self):
        pol = mk("FI-alt-m3")
        self.assertEqual([pol.act(t)[0] for t in range(6)],
                         ["memory", "queue", "commit", "skill", "memory", "commit"])

    def test_fixed_members_use_the_rhos_line8_threshold(self):
        self.assertEqual(mk("FI-alt-m2", rho=1.0).eta_q, S.cfg_for(TUNED, 1.0)["eta_q"])
        self.assertEqual(mk("FI-c3-p2-d2", rho=0.0).eta_q, S.cfg_for(TUNED, 0.0)["eta_q"])

    def test_the_tuned_arm_reads_its_member(self):
        d35 = {"fixed": {"0": {"4": {"member": "FI-alt-m3"}, "8": {"member": "FI-c4-p2-d3"}}}}
        self.assertIsInstance(mk(X.FIXED, delta=4, d35=d35), X.FixedAlternation)
        self.assertIsInstance(mk(X.FIXED, delta=8, d35=d35), X.FixedRotation)


class TestWrongDelta(unittest.TestCase):
    def test_table(self):
        self.assertEqual(X.DHAT, {"A1 dhat-swap": {4: 8, 8: 4},
                                  "A1 dhat-down1": {4: 2, 8: 4},
                                  "A1 dhat-down2": {4: 1, 8: 2}})

    def test_plays_a_member_of_the_told_deltas_mixture(self):
        robust = S.cfg_for(TUNED, 0.0)["mix"]["mid|8"]["robust"]
        for seed in range(1, 30):
            self.assertIn(mk("A1 dhat-swap", seed=seed, delta=4).member_name, robust)

    def test_same_draw_as_sentinel_told_the_same_delta(self):
        for seed in range(1, 30):
            self.assertEqual(mk("A1 dhat-down1", seed=seed, delta=8).member_name,
                             mk("Sentinel-A1", seed=seed, delta=4).member_name)

    def test_undefined_off_the_headline(self):
        with self.assertRaises(ValueError):
            mk("A1 dhat-swap", delta=2)


class TestFallsThrough(unittest.TestCase):
    def test_study_systems_resolve_as_before(self):
        self.assertIsInstance(mk("B1 audit-at-commit"), CP.B1AuditAtCommit)
        self.assertIsInstance(mk("Sentinel-A1"), S.SentinelA1)

    def test_the_frozen_registries_are_untouched(self):
        self.assertEqual(len(S.REGISTRY), 13)
        self.assertEqual(len(CP.LIBRARY), 28)
        self.assertFalse(set(X.ARMS) & set(S.REGISTRY))
        self.assertEqual(X.ARMS, ["A1 dhat-swap", "A1 dhat-down1", "A1 dhat-down2",
                                  "B2 FQ-matched", "A1 fixed interleave"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd auditgame && ../.venv/bin/python -m unittest tests.tools.test_d35_policies -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'addendum_d35'`

- [ ] **Step 3: Implement** `auditgame/addendum_d35.py`:

```python
"""addendum_d35.py -- the systems of the D35 addendum (preregistration D35).

Not in freeze.SOURCE: the addendum has its own freeze (freeze_d35.py, frozen/MANIFEST-D35.json),
so the base freeze sha256:c789fa7362e0 stays clean.

Arm A  "A1 dhat-*": Sentinel-A1 told a WRONG Delta on the grid (a degraded line 1); it plays the
       frozen mixture of that Delta.  Defined at the headline Deltas only.
Arm B  "B2 FQ-matched": B2 with a commit probability p, tuned on dev per (rho, Delta) so that its
       FQ% does not exceed that of Sentinel's mixture (tools/tune_d35.py).
Arm C  "A1 fixed interleave": the best FIXED-PHASE schedule of an 11-member family on dev, per
       (rho, Delta), by the objective of `pure` (lowest worst-case harm with FQ% <= the cap).
"""
from __future__ import annotations

import json
import pathlib

import carrier_policies as CP
import draft_setup as D
import sentinel as S

D35_TUNED_PATH = pathlib.Path(__file__).resolve().parent / "reference" / "d35_tuned.json"

#: Arm A: the Delta line 1 is told, per true headline Delta (D35).
DHAT = {"A1 dhat-swap": {4: 8, 8: 4},
        "A1 dhat-down1": {4: 2, 8: 4},
        "A1 dhat-down2": {4: 1, 8: 2}}
B2_FQ = "B2 FQ-matched"
FIXED = "A1 fixed interleave"
ARMS = list(DHAT) + [B2_FQ, FIXED]
#: Arm B: commit probabilities from B2's own share (0.25) to B1 (1.0).
P_GRID = tuple(round(0.25 + 0.05 * i, 2) for i in range(16))
B2P_PREFIX = "B2p:"                          # tuning names, e.g. "B2p:0.6"


class B2CommitProb(CP.CarrierPolicy):
    """B2 with a commit probability: each task a depth-3 commit review with probability p,
    else a depth-3 sweep of a carrier drawn uniformly from D.SWEEP_CARRIERS.  Quarantines every
    firing item (the baseline rule)."""
    def __init__(self, *a, p=0.25, **kw):
        super().__init__(*a, **kw)
        self.p = p

    def act(self, t):
        g = self.rng(t, "b2p")
        if g.random() < self.p:
            return (D.COMMIT, D.MAX_DEPTH)
        return (g.choice(D.SWEEP_CARRIERS), D.MAX_DEPTH)


class FixedRotation(CP.CarrierRotation):
    """An RO schedule with its phase fixed at 0 for every workflow and seed."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.phase = 0


class FixedAlternation(CP._Believer):
    """A depth-3 commit review at every task t with t % m == m - 1; the other tasks sweep
    memory, queue, skill in turn, at depth 3.  Fixed phase."""
    def __init__(self, *a, m=2, **kw):
        super().__init__(*a, **kw)
        self.m = m

    def act(self, t):
        if t % self.m == self.m - 1:
            return (D.COMMIT, D.MAX_DEPTH)
        i = t - (t + 1) // self.m                   # index of t among the sweep tasks
        return (D.SWEEP_CARRIERS[i % len(D.SWEEP_CARRIERS)], D.MAX_DEPTH)


FIXED_LIBRARY = {}
for _o in ("c3", "c4"):
    for _p in (1, 2):
        for _d in (2, 3):
            FIXED_LIBRARY[f"FI-{_o}-p{_p}-d{_d}"] = (FixedRotation,
                                                     {"order": _o, "period": _p, "depth": _d})
for _m in (2, 3, 4):
    FIXED_LIBRARY[f"FI-alt-m{_m}"] = (FixedAlternation, {"m": _m})


def load_d35(path=D35_TUNED_PATH) -> dict:
    p = pathlib.Path(path)
    return json.loads(p.read_text()) if p.exists() else {}


def _cell(table: dict, rho: float, delta: int) -> dict:
    return table[f"{rho:g}"][str(delta)]


def make_policy_d35(name, *, budget, kappa, H, rng_seed, setting, tuned, d35, rho_patch, delta,
                    attacked=None, eta_q=None):
    """Every system of the addendum by name, and its tuning names (B2p:<p>, FI-*).  Any other
    name goes to sentinel.make_policy unchanged (B1, Sentinel-A1, ...)."""
    cfg = S.cfg_for(tuned, rho_patch)
    if name in DHAT:
        if delta not in DHAT[name]:
            raise ValueError(f"{name} is defined at Delta {sorted(DHAT[name])}, not {delta}")
        return S.make_policy("Sentinel-A1", budget=budget, kappa=kappa, H=H, rng_seed=rng_seed,
                             setting=setting, tuned=tuned, rho_patch=rho_patch,
                             delta=DHAT[name][delta], eta_q=eta_q)
    if name == B2_FQ or name.startswith(B2P_PREFIX):
        p = (_cell(d35["b2_fq"], rho_patch, delta)["p"] if name == B2_FQ
             else float(name[len(B2P_PREFIX):]))
        return B2CommitProb(budget, kappa, H, rng_seed, setting, cfg, p=p)
    if name == FIXED or name in FIXED_LIBRARY:
        member = _cell(d35["fixed"], rho_patch, delta)["member"] if name == FIXED else name
        cls, kw = FIXED_LIBRARY[member]
        eq = cfg.get("eta_q", D.ETA_Q_BAYES) if eta_q is None else eta_q
        return cls(budget, kappa, H, rng_seed, setting, cfg, betas=tuned.get("betas", {}),
                   eta_q=eq, **kw)
    return S.make_policy(name, budget=budget, kappa=kappa, H=H, rng_seed=rng_seed,
                         setting=setting, tuned=tuned, rho_patch=rho_patch, delta=delta,
                         attacked=attacked, eta_q=eta_q)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd auditgame && ../.venv/bin/python -m unittest tests.tools.test_d35_policies -v`
Expected: all tests OK (18 tests).

- [ ] **Step 5: Gitignore the addendum's raw records.** Append to the repo-root `.gitignore`, right after the line `auditgame/spikes/v2-smoke-dev/`:

```
# Raw D35 addendum records: regenerated by auditgame/tools/run_d35.py, pinned by d35-records.sha256.
auditgame/spikes/v2-addendum/*.jsonl
auditgame/spikes/v2-addendum-dev/*.jsonl
```

- [ ] **Step 6: Check the base freeze and the gate-1 v2 tests**

Run:
```bash
cd auditgame
../.venv/bin/python -c "import costs, policies as P, freeze; costs.install(P); print(freeze.header_line())"
../.venv/bin/python -m unittest tests.gate1_integrity.test_v2_sentinel tests.gate1_integrity.test_v2_policies tests.gate1_integrity.test_v2_freeze -v 2>&1 | tail -3
```
Expected: `freeze: clean sha256:c789fa7362e0`; the three test modules OK.

- [ ] **Step 7: Commit**

```bash
git add .gitignore auditgame/addendum_d35.py auditgame/tests/tools/test_d35_policies.py
git commit -m "feat(d35): the addendum's systems -- wrong Delta-hat, B2 with a commit probability, fixed-phase schedules

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Dev tuning of arms B and C (`tools/tune_d35.py`, `reference/d35_tuned.json`)

**Files:**
- Create: `auditgame/tools/tune_d35.py`
- Create (by running it): `auditgame/reference/d35_tuned.json`, `auditgame/spikes/v2-addendum-dev/tune-log.txt`
- Test: `auditgame/tests/tools/test_d35_tune.py`

**Interfaces:**
- Consumes:
  - from Task 1: `X.make_policy_d35`, `X.P_GRID`, `X.B2P_PREFIX`, `X.FIXED_LIBRARY`, `X.D35_TUNED_PATH`;
  - from the frozen tools: `select_mixture.KERNELS`, `dev_workflows()`, `make_world(setting, kernel, rho)`, `reduce_kernels(rows, kernels) -> (M, F, cols)`, where rows are 7-tuples `(name, setting, kernel, rho, eta_q, cols, fq)`.
- Produces:
  - `cell_d35(job) -> (name, setting, kernel, rho, None, {col: mean harm}, fq_pct)`, where `job = (name, setting, kernel, rho, deltas, seeds, tuned)`;
  - `choose_p(cands: dict[float, tuple[dict, float]], delta: int, target_fq: float) -> dict` with keys `p, dev_worst, dev_fq, target_fq`;
  - `choose_fixed(cands: dict[str, tuple[dict, float]], delta: int, cap: float) -> dict` with keys `member, dev_worst, dev_fq, cap_ok`;
  - the file `reference/d35_tuned.json`:
    ```json
    {"seeds": [1, 2], "p_grid": [...], "fixed_library": [...],
     "b2_fq": {"<rho:g>": {"4": {...}, "8": {...}}},
     "fixed": {"<rho:g>": {"4": {...}, "8": {...}}},
     "dev_rows": {"<rho:g>": {name: {"worst": {"4": x, "8": x}, "fq": x}}}}
    ```

- [ ] **Step 1: Write the failing tests** in `auditgame/tests/tools/test_d35_tune.py`:

```python
"""D35 tuning rules (tools/tune_d35.py).
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_tune -v"""
import unittest

import sentinel as S
from tools.tune_d35 import cell_d35, choose_fixed, choose_p


def cols(v4, v8):
    return {"a@4": v4, "b@4": v4 / 2, "a@8": v8, "b@8": v8 / 2, "a@0": 0.99}


class TestChooseP(unittest.TestCase):
    def test_lowest_worst_case_within_the_fq_target(self):
        cands = {0.25: (cols(0.30, 0.2), 14.0), 0.5: (cols(0.40, 0.2), 7.0),
                 0.75: (cols(0.60, 0.2), 3.0), 1.0: (cols(0.90, 0.9), 0.0)}
        got = choose_p(cands, 4, target_fq=8.0)
        self.assertEqual(got["p"], 0.5)
        self.assertAlmostEqual(got["dev_worst"], 0.40)
        self.assertEqual(got["target_fq"], 8.0)

    def test_reads_only_the_columns_of_its_delta(self):
        cands = {0.5: (cols(0.40, 0.10), 7.0), 0.75: (cols(0.35, 0.50), 3.0)}
        self.assertEqual(choose_p(cands, 4, 8.0)["p"], 0.75)
        self.assertEqual(choose_p(cands, 8, 8.0)["p"], 0.5)

    def test_ties_at_four_decimals_go_to_lower_fq_then_smaller_p(self):
        cands = {0.5: (cols(0.40001, 0.2), 7.0), 0.6: (cols(0.40002, 0.2), 5.0),
                 0.7: (cols(0.40, 0.2), 5.0)}
        self.assertEqual(choose_p(cands, 4, 8.0)["p"], 0.6)

    def test_p_one_is_always_feasible(self):
        cands = {0.5: (cols(0.1, 0.1), 9.0), 1.0: (cols(0.9, 0.9), 0.0)}
        self.assertEqual(choose_p(cands, 4, target_fq=2.0)["p"], 1.0)


class TestChooseFixed(unittest.TestCase):
    def test_lowest_worst_case_within_the_cap(self):
        cands = {"FI-a": (cols(0.2, 0.2), 12.0), "FI-b": (cols(0.3, 0.3), 6.0),
                 "FI-c": (cols(0.5, 0.1), 2.0)}
        got = choose_fixed(cands, 4, cap=10.0)
        self.assertEqual(got["member"], "FI-b")
        self.assertTrue(got["cap_ok"])

    def test_ties_go_to_lower_fq_then_name(self):
        cands = {"FI-b": (cols(0.3, 0.3), 6.0), "FI-a": (cols(0.3, 0.3), 6.0),
                 "FI-c": (cols(0.3, 0.3), 4.0)}
        self.assertEqual(choose_fixed(cands, 4, 10.0)["member"], "FI-c")
        del cands["FI-c"]
        self.assertEqual(choose_fixed(cands, 4, 10.0)["member"], "FI-a")

    def test_no_member_within_the_cap_is_flagged(self):
        cands = {"FI-a": (cols(0.2, 0.2), 12.0), "FI-b": (cols(0.3, 0.3), 11.0)}
        got = choose_fixed(cands, 4, 10.0)
        self.assertEqual(got["member"], "FI-a")
        self.assertFalse(got["cap_ok"])


class TestCellOnDev(unittest.TestCase):
    """One small dev job per kind: it runs, is shaped like select_mixture.member_cell."""
    def test_b2p_one_quarantines_nothing(self):
        name, _s, _k, rho, eq, c, fq = cell_d35(("B2p:1", "mid", "nominal", 0.0, (4,), (1,),
                                                 S.load_tuned()))
        self.assertEqual((name, rho, eq), ("B2p:1", 0.0, None))
        self.assertEqual(fq, 0.0)
        self.assertTrue(c and all(k.endswith("@4") for k in c))

    def test_fixed_member_runs(self):
        _n, _s, _k, _r, _e, c, fq = cell_d35(("FI-alt-m2", "mid", "nominal", 0.0, (4,), (1,),
                                              S.load_tuned()))
        self.assertTrue(c)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in c.values()))
        self.assertGreater(fq, 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd auditgame && ../.venv/bin/python -m unittest tests.tools.test_d35_tune -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'tools.tune_d35'`

- [ ] **Step 3: Implement** `auditgame/tools/tune_d35.py`:

```python
"""tune_d35.py -- the D35 addendum's tuning, on DEV only (preregistration D35).

  B2 FQ-matched, per (rho, Delta in {4, 8}): p* = argmin over P_GRID of the dev worst-case harm
     (max over the 3 kernels, over the tuning columns at that Delta), subject to dev FQ% (max over
     kernels, pooled over every Delta) <= fq_pct of Sentinel's mixture for mid|Delta; ties at 4
     decimals go to the lower FQ%, then the smaller p.  p = 1 (B1, FQ 0) is always feasible.
  A1 fixed interleave, per (rho, Delta in {4, 8}): the member of FIXED_LIBRARY with the lowest dev
     worst-case harm and FQ% <= D.FQ_CAP_PCT; ties: FQ%, then name (the rule of `pure`).
The dev measurement mirrors select_mixture.member_cell (seeds 1, 2; the 6 tuning columns; every
Delta), through the addendum's resolver.  Writes reference/d35_tuned.json, never v2_tuned.json.

    ../.venv/bin/python tools/tune_d35.py --jobs 10 | tee spikes/v2-addendum-dev/tune-log.txt
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import addendum_d35 as X
import attackers_v2 as A
import carrier_runner as R
import draft_setup as D
import sentinel as S
from tools.select_mixture import KERNELS, dev_workflows, make_world, reduce_kernels


def cell_d35(job):
    """select_mixture.member_cell through the addendum's resolver: one policy under one
    (setting, kernel, rho) on dev -- per-column harm means and the FQ%."""
    name, setting, kernel, rho, deltas, seeds, tuned = job
    K = D.TARGET_KAPPA_DRAFT
    world = make_world(setting, kernel, rho)
    cols, fr, bi = {}, 0, 0
    for an in A.tuning_attack_names():
        for d in deltas:
            for wf in dev_workflows():
                got = A.by_name(an).plan(wf, d)
                if got is None:
                    continue
                for s in seeds:
                    if not R.survives(wf, got[0], s):
                        continue
                    pol = X.make_policy_d35(name, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                            rng_seed=R.rs_of(wf, s), setting=setting,
                                            tuned=tuned, d35={}, rho_patch=rho, delta=d)
                    r = R.run_carrier(wf, got, pol, world, s, K)
                    cols.setdefault(f"{an}@{d}", []).append(r.harm)
                    fr += r.false_removed
                    bi += r.benign_inspected
    return (name, setting, kernel, rho, None,
            {c: sum(v) / len(v) for c, v in cols.items()}, 100.0 * fr / bi if bi else 0.0)


def _worst(M: dict, delta: int) -> float:
    return max(v for c, v in M.items() if c.endswith(f"@{delta}"))


def choose_p(cands, delta, target_fq) -> dict:
    """cands: {p: (M over columns, FQ%)}.  D35 arm B's rule."""
    ok = [(round(_worst(M, delta), 4), F, p, _worst(M, delta))
          for p, (M, F) in cands.items() if F <= target_fq + 1e-9]
    key, F, p, worst = min(ok)
    return {"p": p, "dev_worst": round(worst, 6), "dev_fq": round(F, 3), "target_fq": target_fq}


def choose_fixed(cands, delta, cap) -> dict:
    """cands: {member: (M over columns, FQ%)}.  D35 arm C's rule (that of `pure`)."""
    ok = [n for n, (_M, F) in cands.items() if F <= cap]
    pool = ok or list(cands)
    n = min(pool, key=lambda n: (_worst(cands[n][0], delta), cands[n][1], n))
    return {"member": n, "dev_worst": round(_worst(cands[n][0], delta), 6),
            "dev_fq": round(cands[n][1], 3), "cap_ok": bool(ok)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--out", default=str(X.D35_TUNED_PATH))
    a = ap.parse_args(argv)
    tuned, seeds, kernels = S.load_tuned(), tuple(D.TUNE_SEEDS), list(KERNELS)
    b2 = [f"{X.B2P_PREFIX}{p:g}" for p in X.P_GRID]
    names = b2 + sorted(X.FIXED_LIBRARY)
    jobs = [(n, D.HEADLINE_DETECTOR, k, rho, D.DELTAS, seeds, tuned)
            for rho in D.RHO_PATCH_GRID for n in names for k in kernels]
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(cell_d35, jobs, chunksize=1))
    out = {"seeds": list(seeds), "p_grid": list(X.P_GRID), "fixed_library": sorted(X.FIXED_LIBRARY),
           "b2_fq": {}, "fixed": {}, "dev_rows": {}}
    for rho in D.RHO_PATCH_GRID:
        rk = f"{rho:g}"
        M, F, _cols = reduce_kernels([r for r in rows if r[3] == rho], kernels)
        mix = S.cfg_for(tuned, rho)["mix"]
        out["dev_rows"][rk] = {n: {"worst": {str(d): round(_worst(M[n], d), 6)
                                             for d in D.HEADLINE_DELTAS},
                                   "fq": round(F[n], 3)} for n in names}
        for d in D.HEADLINE_DELTAS:
            target = mix[S.mix_key(D.HEADLINE_DETECTOR, d)]["fq_pct"]
            out["b2_fq"].setdefault(rk, {})[str(d)] = choose_p(
                {float(n[len(X.B2P_PREFIX):]): (M[n], F[n]) for n in b2}, d, target)
            out["fixed"].setdefault(rk, {})[str(d)] = choose_fixed(
                {n: (M[n], F[n]) for n in X.FIXED_LIBRARY}, d, D.FQ_CAP_PCT)
            print(rk, d, "b2_fq", out["b2_fq"][rk][str(d)], "fixed", out["fixed"][rk][str(d)],
                  flush=True)
    path = pathlib.Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd auditgame && ../.venv/bin/python -m unittest tests.tools.test_d35_tune -v`
Expected: 9 tests OK. The two `TestCellOnDev` tests take a few seconds each.

- [ ] **Step 5: Run the tuning on dev**

Run:
```bash
cd auditgame && mkdir -p spikes/v2-addendum-dev
../.venv/bin/python tools/tune_d35.py --jobs 10 | tee spikes/v2-addendum-dev/tune-log.txt
```
Expected: 8 lines `<rho> <delta> b2_fq {...} fixed {...}`, and `reference/d35_tuned.json` written. It should take under 20 minutes on 10 cores.
- Check: every `b2_fq` entry has `dev_fq <= target_fq`.
- Check: every `fixed` entry reports `cap_ok`.
- Paste the 8 lines into your report.

- [ ] **Step 6: Check the base freeze is still clean** (the same command as Task 1 Step 6). Expected: `freeze: clean sha256:c789fa7362e0`.

- [ ] **Step 7: Commit**

```bash
git add auditgame/tools/tune_d35.py auditgame/tests/tools/test_d35_tune.py auditgame/reference/d35_tuned.json auditgame/spikes/v2-addendum-dev/tune-log.txt
git commit -m "tune(d35): p of B2 FQ-matched and the fixed-phase schedule, per (rho, Delta), on dev only

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: The addendum's freeze and run tool, and the dev pilot (`freeze_d35.py`, `tools/run_d35.py`)

**Files:**
- Create: `auditgame/freeze_d35.py`
- Create: `auditgame/tools/run_d35.py`
- Test: `auditgame/tests/tools/test_d35_run.py`
- Create (by running on dev): `auditgame/spikes/v2-addendum-dev/d35-summary.json`, `auditgame/spikes/v2-addendum-dev/d35-records.sha256`

**Interfaces:**
- Consumes:
  - from Task 1: `X.make_policy_d35`, `X.ARMS`, `X.DHAT`, `X.B2_FQ`, `X.FIXED`, `X.FIXED_LIBRARY`, `X.P_GRID`, `X.load_d35()`;
  - from Task 2: `reference/d35_tuned.json`;
  - frozen: `freeze.load()`, `freeze.header_line(path)`, `freeze.MANIFEST_PATH`, `tools.run_draft_eval.workflows(split)`, `tools.run_draft_eval._write(path, obj)`, `tools.select_mixture.make_world`, `metrics_v2.gain_ci/value/harm_table/side/crossfit_value`, `metrics.loss`.
- Produces:
  - `freeze_d35.manifest() -> dict`, `digest(man) -> str`, `write(path=PATH) -> str`, `load(path=PATH)`, `drift(path=PATH) -> list[str]`, `header_line(path=PATH) -> str`, `clean(line) -> bool`, `PATH`;
  - `run_d35.refusal(split, header, out_dir, summarise_only) -> str | None`;
  - `run_d35.reproduces(v_b1, v_s, main_rho) -> list[str]`;
  - `run_d35.readings(rows) -> dict`;
  - `run_d35.main(argv) -> int` (0 ok, 1 withheld, 2 refused);
  - `run_d35.OUT = {"eval": spikes/v2-addendum, "dev": spikes/v2-addendum-dev}`.

- [ ] **Step 1: Write the failing tests** in `auditgame/tests/tools/test_d35_run.py`:

```python
"""D35 freeze and run tool (freeze_d35.py, tools/run_d35.py); no eval data is read.
Run from auditgame/: ../.venv/bin/python -m unittest tests.tools.test_d35_run -v"""
import json
import pathlib
import tempfile
import unittest

import addendum_d35 as X
import freeze_d35 as F
from tools import run_d35 as RD


class TestFreezeD35(unittest.TestCase):
    def test_manifest_pins_the_base_the_files_and_the_names(self):
        man = F.manifest()
        self.assertEqual(man["base_digest"][:12], "c789fa7362e0")
        self.assertEqual(set(man["files"]), {"addendum_d35.py", "reference/d35_tuned.json"})
        self.assertEqual(man["arms"], sorted(X.ARMS))
        self.assertEqual(len(man["fixed_library"]), 11)
        self.assertEqual(man["dhat"]["A1 dhat-swap"], {"4": 8, "8": 4})
        self.assertEqual(man["p_grid"], list(X.P_GRID))

    def test_write_then_no_drift_then_tamper_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "MANIFEST-D35.json"
            dig = F.write(path)
            self.assertEqual(len(dig), 64)
            self.assertEqual(F.drift(path), [])
            man = json.loads(path.read_text())
            man["files"]["addendum_d35.py"] = "0" * 64
            man["p_grid"] = [0.5]
            path.write_text(json.dumps(man))
            got = F.drift(path)
            self.assertIn("files/addendum_d35.py: changed", got)
            self.assertIn("p_grid: changed", got)

    def test_missing_manifest(self):
        self.assertEqual(F.drift(pathlib.Path("/nonexistent/M.json")),
                         ["no D35 manifest: nothing has been frozen"])

    def test_clean_needs_both_freezes_clean(self):
        ok = "freeze-d35: clean sha256:abc  |  base freeze: clean sha256:c789fa7362e0"
        self.assertTrue(F.clean(ok))
        self.assertFalse(F.clean("freeze-d35: NONE  |  base freeze: clean sha256:c789fa7362e0"))
        self.assertFalse(F.clean("freeze-d35: clean sha256:abc  |  base freeze: DRIFTED from x"))
        self.assertFalse(F.clean(ok + "  |  PIN CONFLICT: x"))


class TestRefusal(unittest.TestCase):
    def test_eval_needs_a_clean_d35_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNotNone(RD.refusal("eval", "freeze-d35: NONE  |  base freeze: clean",
                                            pathlib.Path(d), False))
            self.assertIsNone(RD.refusal(
                "eval", "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c", pathlib.Path(d), False))

    def test_dev_runs_before_the_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(RD.refusal("dev", "freeze-d35: NONE  |  base freeze: clean",
                                         pathlib.Path(d), False))

    def test_the_addendum_runs_once(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / RD.MAIN).write_text("{}\n")
            clean = "freeze-d35: clean sha256:a  |  base freeze: clean sha256:c"
            self.assertIn("runs once", RD.refusal("eval", clean, pathlib.Path(d), False))
            self.assertIsNone(RD.refusal("eval", clean, pathlib.Path(d), True))


class TestReproduction(unittest.TestCase):
    MAIN = {"table2": {"B1 audit-at-commit": {"worst_case_harm": 0.79813797},
                       "Sentinel-A1": {"worst_case_harm": 0.40543650}}}

    def test_equal_to_four_decimals_passes(self):
        self.assertEqual(RD.reproduces(0.79814, 0.405436, self.MAIN), [])

    def test_a_difference_is_named(self):
        got = RD.reproduces(0.79814, 0.4061, self.MAIN)
        self.assertEqual(len(got), 1)
        self.assertIn("Sentinel-A1", got[0])


def _ci(lo):
    return {"abs_lo": lo, "abs_hi": lo + 0.1, "abs_diff": lo + 0.05}


class TestReadings(unittest.TestCase):
    def rows(self, swap_lo=0.1, down1_lo=0.1, b2_lo=0.1, fixed_lo=0.1, vbr_fixed=0.5):
        out = {}
        for rk in ("0", "0.25", "0.5", "1"):
            out[rk] = {"Sentinel-A1": {"v_br": 0.4},
                       "A1 dhat-swap": {"vs_b1": _ci(swap_lo if rk != "1" else -0.1)},
                       "A1 dhat-down1": {"vs_b1": _ci(down1_lo if rk != "1" else -0.1)},
                       "A1 dhat-down2": {"vs_b1": _ci(-0.2)},
                       X.B2_FQ: {"vs_sentinel": _ci(b2_lo)},
                       X.FIXED: {"vs_sentinel": _ci(fixed_lo), "v_br": vbr_fixed}}
        return out

    def test_a_uses_rho_up_to_half_and_both_one_step_arms(self):
        self.assertTrue(RD.readings(self.rows())["A_oracle_survives_one_step"])
        self.assertFalse(RD.readings(self.rows(down1_lo=-0.01))["A_oracle_survives_one_step"])

    def test_b_and_c_per_rho(self):
        r = RD.readings(self.rows(b2_lo=-0.01, fixed_lo=0.02, vbr_fixed=0.3))
        self.assertEqual(r["B_beats_fq_matched_mix"], {"0": False, "0.25": False, "0.5": False, "1": False})
        self.assertTrue(all(r["C_scripted_gain_attributable_to_randomisation"].values()))
        self.assertFalse(any(r["C_br_fixed_above_sentinel"].values()))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd auditgame && ../.venv/bin/python -m unittest tests.tools.test_d35_run -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'freeze_d35'`

- [ ] **Step 3: Implement** `auditgame/freeze_d35.py`:

```python
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
FILES = ("addendum_d35.py", "reference/d35_tuned.json")
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
```

- [ ] **Step 4: Implement** `auditgame/tools/run_d35.py`:

```python
"""run_d35.py -- the D35 addendum (preregistration D35); on the eval split ONCE, after its freeze.

Headline cell only (mid, Delta in {4, 8}, the 7 held-out attackers, chi 1.34, b1, match 1), every
rho: B1 and Sentinel-A1 (re-simulated: the reproduction check) and the five addendum arms, plus
the cross-fitted best response of the same seven systems.  On eval, no addendum number is written
unless B1's and Sentinel-A1's V equal the main run's (spikes/v2/eval-summary.json) to 4 decimals
at every rho.

    ../.venv/bin/python tools/run_d35.py --split dev --jobs 10     # pilot -> spikes/v2-addendum-dev
    ../.venv/bin/python tools/run_d35.py --split eval --jobs 10    # once  -> spikes/v2-addendum
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import pathlib
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import addendum_d35 as X
import attackers_v2 as A
import carrier_runner as R
import costs
import draft_setup as D
import freeze_d35
import metrics as M
import metrics_v2 as MV
import policies as P
import sentinel as S
from tools.run_draft_eval import _write, workflows
from tools.select_mixture import make_world

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = {"eval": ROOT / "spikes" / "v2-addendum", "dev": ROOT / "spikes" / "v2-addendum-dev"}
MAIN_SUMMARY = ROOT / "spikes" / "v2" / "eval-summary.json"
B1, SA1 = "B1 audit-at-commit", "Sentinel-A1"
SYSTEMS = [B1, SA1] + X.ARMS
ALPHA = D.FAMILY_ALPHA / len(D.RHO_PATCH_GRID)           # 98.75%, per arm (D35)
MAIN, BR, PIN, SUMMARY = "d35-main.jsonl", "d35-br.jsonl", "d35-records.sha256", "d35-summary.json"
FIELDS = ("harm", "detected_at", "iota", "n_solved", "t_lost", "false_removed", "benign_inspected")


def work(args):
    """One (system, held-out attacker, Delta, rho) at the headline cell, as run_draft_eval.work."""
    (policy, attack, delta, rho), tuned, d35, seeds, split = args
    K = D.target_kappa_for_chi(D.HEADLINE_CHI)
    world = make_world(D.HEADLINE_DETECTOR, "nominal", rho, D.DRIFT_MATCH, D.DRIFT_VISIBLE_TASKS)
    out = []
    for wf in workflows(split):
        got = A.by_name(attack).plan(wf, delta)
        if got is None:
            continue
        for s in seeds:
            if not R.survives(wf, got[0], s):
                continue
            pol = X.make_policy_d35(policy, budget=D.BudgetSpec().budget(wf.H), kappa=K, H=wf.H,
                                    rng_seed=R.rs_of(wf, s), setting=D.HEADLINE_DETECTOR,
                                    tuned=tuned, d35=d35, rho_patch=rho, delta=delta,
                                    attacked=got[0].carrier)
            r = dataclasses.asdict(R.run_carrier(wf, got, pol, world, s, K))
            out.append({**{k: r[k] for k in FIELDS}, "policy": policy, "attack": attack,
                        "delta": delta, "rho_patch": rho, "wf": wf.wf_id, "repo": wf.repo,
                        "seed": s})
    return out


def br_work(args):
    """D27 for one system at one (Delta, rho), as run_draft_eval.br_work."""
    (policy, delta, rho), tuned, d35, seeds, split = args
    K = D.TARGET_KAPPA_DRAFT
    world = make_world(D.HEADLINE_DETECTOR, "nominal", rho)
    rows = []
    for wf in workflows(split):
        for ps in A.placements(wf, delta):
            for s in seeds:
                if not R.survives(wf, ps, s):
                    continue
                pol = X.make_policy_d35(policy, budget=D.budget_b1(wf.H), kappa=K, H=wf.H,
                                        rng_seed=R.rs_of(wf, s), setting=D.HEADLINE_DETECTOR,
                                        tuned=tuned, d35=d35, rho_patch=rho, delta=delta,
                                        attacked=ps.carrier)
                r = R.run_carrier(wf, (ps, "write"), pol, world, s, K)
                rows.append({"wf": wf.wf_id, "placement": (ps.carrier, ps.iota), "seed": s,
                             "harm": r.harm})
    return {"policy": policy, "delta": delta, "rho_patch": rho, **MV.crossfit_value(rows)}


def run(fn, items, jobs, path) -> int:
    n = 0
    with ProcessPoolExecutor(jobs) as ex, open(path, "x") as fh:     # "x": never overwrite (D35)
        for recs in ex.map(fn, items, chunksize=2):
            for r in (recs if isinstance(recs, list) else [recs]):
                fh.write(json.dumps(r, default=str) + "\n")
                n += 1
    return n


def pin(out_dir, names) -> pathlib.Path:
    rows = []
    for name in names:
        h, lines, size = hashlib.sha256(), 0, 0
        with open(out_dir / name, "rb") as fh:
            while chunk := fh.read(1 << 20):
                h.update(chunk)
                lines += chunk.count(b"\n")
                size += len(chunk)
        rows.append((h.hexdigest(), lines, size, name))
    path = out_dir / PIN
    path.write_text("# raw D35 records, not committed; lines  bytes  file:\n"
                    + "".join(f"#   {n}  {b}  {f}\n" for _, n, b, f in rows)
                    + "".join(f"{h}  {f}\n" for h, _, _, f in rows))
    return path


def refusal(split, header, out_dir, summarise_only) -> str | None:
    """D35: eval only on a clean D35 freeze over a clean base, and only once."""
    if split == "eval" and not freeze_d35.clean(header):
        return f"the D35 freeze is not clean: {header}"
    if not summarise_only and (pathlib.Path(out_dir) / MAIN).exists():
        return f"{pathlib.Path(out_dir) / MAIN} exists: the addendum runs once (D35)"
    return None


def reproduces(v_b1, v_s, main_rho) -> list:
    """D35: B1 and Sentinel-A1 must equal the main run to 4 decimals; the mismatches."""
    out = []
    for name, v in ((B1, v_b1), (SA1, v_s)):
        want = main_rho["table2"][name]["worst_case_harm"]
        if round(v, 4) != round(want, 4):
            out.append(f"{name}: {v:.4f} != main {want:.4f}")
    return out


def readings(rows) -> dict:
    """The declared readings (A), (B), (C) of D35, mechanically."""
    low = [rk for rk in rows if float(rk) <= 0.5]
    a = {arm: all(rows[rk][arm]["vs_b1"]["abs_lo"] > 0 for rk in low)
         for arm in ("A1 dhat-swap", "A1 dhat-down1")}
    return {"A_oracle_survives_one_step": all(a.values()), "A_by_arm": a,
            "B_beats_fq_matched_mix": {rk: rows[rk][X.B2_FQ]["vs_sentinel"]["abs_lo"] > 0
                                       for rk in rows},
            "C_scripted_gain_attributable_to_randomisation":
                {rk: rows[rk][X.FIXED]["vs_sentinel"]["abs_lo"] > 0 for rk in rows},
            "C_br_fixed_above_sentinel": {rk: rows[rk][X.FIXED]["v_br"] > rows[rk][SA1]["v_br"]
                                          for rk in rows}}


def _v(rs, p, loss=False):
    if loss:
        rs = [{**r, "harm": M.loss(r["harm"], r["false_removed"], r["t_lost"])} for r in rs]
    return MV.value(MV.harm_table(rs, p, A.held_out(), list(D.HEADLINE_DELTAS)))


def summarise(split, out_dir, meta) -> dict:
    ho, hd = A.held_out(), list(D.HEADLINE_DELTAS)
    recs = [json.loads(line) for line in open(out_dir / MAIN)]
    brs = [json.loads(line) for line in open(out_dir / BR)]
    d35 = X.load_d35()
    main = json.loads(MAIN_SUMMARY.read_text())["by_rho"] if split == "eval" else None
    out = {"run": meta, "alpha": ALPHA, "n_boot": 10000, "reproduction": {}, "rows": {}}
    by = {f"{rho:g}": [r for r in recs if r["rho_patch"] == rho] for rho in D.RHO_PATCH_GRID}
    for rk, rs in by.items():
        vb, vs = _v(rs, B1), _v(rs, SA1)
        out["reproduction"][rk] = {B1: vb, SA1: vs, "checked": main is not None,
                                   "mismatches": reproduces(vb, vs, main[rk]) if main else []}
    if any(v["mismatches"] for v in out["reproduction"].values()):
        out["withheld"] = "D35: B1 or Sentinel-A1 does not reproduce the main run; no addendum number"
        _write(out_dir / SUMMARY, out)
        return out
    for rk, rs in by.items():
        rho = float(rk)
        vb, vs = out["reproduction"][rk][B1], out["reproduction"][rk][SA1]
        rows = {}
        for p in SYSTEMS:
            prs = [r for r in rs if r["policy"] == p]
            vbr = [b["v_br"] for b in brs if b["policy"] == p and b["rho_patch"] == rho
                   and b["v_br"] is not None and math.isfinite(b["v_br"])]
            row = {"V": _v(prs, p), "worst_case_L": _v(prs, p, loss=True),
                   **MV.side(prs, p, ho, hd), "v_br": max(vbr) if vbr else float("nan"),
                   "n_workflows": len({r["wf"] for r in prs}),
                   "n_repos": len({r["repo"] for r in prs}), "n_episodes": len(prs)}
            if p in X.ARMS:
                row["vs_b1"] = MV.gain_ci(rs, B1, p, ho, hd, alpha=ALPHA)
                row["vs_sentinel"] = MV.gain_ci(rs, p, SA1, ho, hd, alpha=ALPHA)
            if p in X.DHAT:
                row["retained"] = (vb - row["V"]) / (vb - vs) if vb > vs else None
            if p == X.B2_FQ:
                row["tuned"] = d35["b2_fq"][rk]
            if p == X.FIXED:
                row["tuned"] = d35["fixed"][rk]
            rows[p] = row
        out["rows"][rk] = rows
    out["readings"] = readings(out["rows"])
    _write(out_dir / SUMMARY, out)
    return out


def provenance() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                                  check=True).stdout.rstrip("\n")
        except (OSError, subprocess.CalledProcessError):
            return None
    status = git("status", "--porcelain", "--", ".")
    return {"git_head": git("rev-parse", "--short", "HEAD"),
            "git_clean": None if status is None else status == "",
            "sha256": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
                       for n in ("tools/run_d35.py", "tools/tune_d35.py", "freeze_d35.py")}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("eval", "dev"), required=True)
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--summarise-only", action="store_true")
    a = ap.parse_args(argv)
    costs.install(P)
    header = freeze_d35.header_line()
    print(header, flush=True)
    out_dir = OUT[a.split]
    why = refusal(a.split, header, out_dir, a.summarise_only)
    if why:
        print(f"refused (D35): {why}", flush=True)
        return 2
    meta = {"split": a.split, "seeds": list(D.SEEDS), "rhos": list(D.RHO_PATCH_GRID),
            "deltas": list(D.HEADLINE_DELTAS), "systems": SYSTEMS, "header": header,
            **provenance()}
    if not a.summarise_only:
        out_dir.mkdir(parents=True, exist_ok=True)
        tuned, d35, seeds = S.load_tuned(), X.load_d35(), tuple(D.SEEDS)
        items = [((p, c, d, rho), tuned, d35, seeds, a.split) for p in SYSTEMS
                 for c in A.held_out() for d in D.HEADLINE_DELTAS for rho in D.RHO_PATCH_GRID]
        print("main", run(work, items, a.jobs, out_dir / MAIN), flush=True)
        brs = [((p, d, rho), tuned, d35, seeds, a.split) for p in SYSTEMS
               for d in D.HEADLINE_DELTAS for rho in D.RHO_PATCH_GRID]
        print("br", run(br_work, brs, a.jobs, out_dir / BR), flush=True)
        print("records", pin(out_dir, [MAIN, BR]), flush=True)
    s = summarise(a.split, out_dir, meta)
    return 1 if "withheld" in s else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `cd auditgame && ../.venv/bin/python -m unittest tests.tools.test_d35_run tests.tools.test_d35_policies tests.tools.test_d35_tune -v`
Expected: all OK.

- [ ] **Step 6: The dev pilot** (pipeline smoke, and the evidence the controller uses for predictions P7–P9)

Run:
```bash
cd auditgame
../.venv/bin/python tools/run_d35.py --split dev --jobs 10
```
Expected:
- The first line starts `freeze-d35: NONE  |  base freeze: clean sha256:c789fa7362e0`.
- Then `main <n>`, `br <n>`, `records ...`, and exit code 0.
- `spikes/v2-addendum-dev/d35-summary.json` has `rows` for the 4 rho keys, each with the 7 systems, and `reproduction.*.checked == false`.

Report per rho the V, FQ% and v_br of the 7 systems, and the `readings` block. Numbers go in your report file, never into any preregistration file.

- [ ] **Step 7: Check the base freeze is still clean** (the same command as Task 1 Step 6).

- [ ] **Step 8: Commit** (the jsonl files are gitignored)

```bash
git add auditgame/freeze_d35.py auditgame/tools/run_d35.py auditgame/tests/tools/test_d35_run.py auditgame/spikes/v2-addendum-dev/d35-summary.json auditgame/spikes/v2-addendum-dev/d35-records.sha256
git commit -m "feat(d35): the addendum's freeze and run tool; dev pilot summary

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4 (controller): Predictions P7–P9, then the D35 freeze

- [ ] Read the dev pilot summary (dev only). Write predictions P7–P9 into the `## Dự đoán khai trước` section of the VI preregistration, and the same into the EN mirror, each with its reason:
  - P7: arm A;
  - P8: arm B;
  - P9: arm C, both the scripted class and V_BR.
- [ ] Commit the predictions.
- [ ] Write the freeze. From `auditgame/`: `../.venv/bin/python -c "import costs, policies as P, freeze_d35; costs.install(P); print(freeze_d35.write())"`. Then check `freeze_d35.header_line()` prints `freeze-d35: clean ... | base freeze: clean sha256:c789fa7362e0`.
- [ ] Commit `auditgame/frozen/MANIFEST-D35.json` with message `freeze(d35): ...`, and add a line to the execution record naming its digest.

### Task 5 (controller): The single eval run
- [ ] Run `tools/run_d35.py --split eval --jobs 10` from `auditgame/`, exactly once.
- [ ] Read `reproduction` first. If it is withheld, stop and report to the user.
- [ ] Commit `spikes/v2-addendum/d35-summary.json` and `d35-records.sha256`, and add the execution record (VI and EN): time, header, record counts and the readings.

### Task 6 (controller + agent): The paper and the package
- [ ] Add a short D35 subsection to the results (secondary, labelled), and update:
  - the contribution wording ("primary endpoint evaluated once; one pre-declared addendum run once");
  - the measurement's D-list;
  - T1, T5 and the conclusion where the addendum answers them.
- [ ] Add the addendum numbers to `notes/v2-facts.md`.
- [ ] Cut to keep the Conclusion on p.18.
- [ ] Rebuild the replication package with the new files.
