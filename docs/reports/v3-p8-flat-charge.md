# v3 P8 — the flat clean-task charge: what actually increments `t_lost`, and the table aggregation

29/09/2026. Branch `int-p2`. Read-only audit of `auditgame/v3/runner.py`, `v3/metrics.py`,
`v3/baselines.py`, `v3/observe.py`, `world_v2.DriftDetector`, against the written records
`spikes/v3-run/eval-pass1/main.jsonl` (931,500 records) and `spikes/v3-run/dev-p6-a7/{a0,a7}.jsonl`
(46,812 each).

```
freeze-v3: clean sha256:9c4c0d018b18  |  freeze-d35: clean sha256:e46f8a5c2f94  |  base freeze: clean sha256:c789fa7362e0
```

**No evaluation was run.** Every number below is read off records that already existed, or computed
by calling the pure observation model (`v3/observe.ObservationModel.commit`) on synthetic inputs —
no episode, no `tools/v3_run.py`. `spikes/v3-run/eval-pass1/br.jsonl` was not opened (declared
not-a-result); `spikes/v2-pilot/eval-touch-2509/` was not touched. Nothing under `auditgame/v3/`,
`auditgame/frozen/`, `freeze.SOURCE` or `freeze.TABLES` was modified.

## The question

The paper explains its most-promoted result — that scoring harm alone rewards generous quarantine —
with rule O7: a *correct* quarantine removes a poisoned lineage and destroys the clean patches
downstream of it, so the charge "is incurred even by *correct* quarantines". The records refuse
that reading. For `B1 audit-at-commit` in `main.jsonl`, mean `t_lost` is **0.6540 at every one of
ρ ∈ {0, 0.25, 0.5, 1}**, while mean harm falls 0.6627 → 0.1220 (5.4×) and mean `fq` is 0.0000
everywhere. A charge driven by correct quarantines would scale with detection, which scales with ρ.
It does not move.

## 1. The mechanism

**`t_lost` for the B1 family is the commit review's false-positive rate on clean patches, charged
once per audited clean task that passed its tests. It follows the *audit* rate, not the detection
rate; and O7's lineage charge contributes exactly nothing, anywhere in the study.**

### The code path

`runner.py:386` defines the field:

```python
t_lost=self.clean_lost_branch + self.clean_blocked,
```

Two summands, and only the second ever fires for B1.

* `clean_lost_branch` is O7's charge — incremented in `Episode.quarantine()` when a **branch**
  quarantine removes a clean, solved patch. B1 never reaches it: `baselines._Baseline.quarantine`
  returns `None` on a commit alarm —
  ```python
  target = self.alarmed_target(t)
  if target == COMMIT:
      return None                  # the runner blocks this task's patch only (step 5)
  ```
  so `Episode.quarantine()` is never called for B1 at all.

* `clean_blocked` is incremented in `Episode.block_patch` (`runner.py:281-295`), which the runner
  calls at step 5 whenever a bought **commit** audit's alarm fires:
  ```python
  if w.poisoned:   self.patch_blocks += 1
  elif o.solved:   self.clean_blocked += 1
  ```
  The runner's own docstring is explicit that this is not a quarantine: *"A commit review whose
  alarm fires BLOCKS THIS TASK'S PATCH ONLY (`block_patch`) … It is not a quarantine: no FQ, no
  other branch item is touched."* `baselines.py` says the same: *"A COMMIT alarm quarantines
  nothing."*

So every unit of B1's `t_lost` is one clean, test-passing patch rejected by a commit review that
fired on it — i.e. **a detector false positive**, nothing else.

### Why ρ cannot reach it

ρ is the exposure of a **delegated marked** patch to commit review (D20). A clean patch has no
marker, so ρ is structurally absent from its score. `observe.patch_mean`:

```python
if not has_marker:
    return 0.0
```

and the world-side draw, `world_v2.DriftDetector.score_patch`:

```python
if not has_marker:
    mean = 0.0
...
return random.Random(seed_of(seed, "v2-patch", task_id)).gauss(mean, 1.0)
```

The mean is 0, `rho_patch` is not consulted, and the seed depends only on `(episode seed, task_id)`
— not on ρ and not on depth. A clean patch therefore draws **the identical score at every ρ**, fires
iff it exceeds the one shared threshold τ, and does so with probability φ, the detector's declared
false-positive rate. For the headline cell's mid detector, `detector.SETTINGS["mid"] = (0.85, 0.12)`
→ d′ = 2.211420, τ = 1.174987, ψ = 0.85, **φ = 0.12**.

Measured directly on the real `ObservationModel` (200,000 clean commit reviews per ρ, A7 world,
headline cell):

| ρ | P(patch score fires) | P(provenance fires) | P(either) |
|---|---|---|---|
| 0 | 0.12005 | 0.12044 | 0.22610 |
| 0.25 | 0.12005 | 0.12044 | 0.22610 |
| 0.5 | 0.12005 | 0.12044 | 0.22610 |
| 1 | 0.12005 | 0.12044 | 0.22610 |

Identical to five decimals across ρ, as the code requires.

### The evidence in the records

Five independent checks, all over the full 931,500 held-out records unless stated.

1. **O7 never fires.** `clean_lost_branch != 0` in **0 of 931,500** records — and 0 of 46,812 in
   `a7.jsonl`, 0 of 46,812 in `a0.jsonl`. Not just for B1: for *every* policy in the study,
   including Sentinel. The mechanism the paper names contributes exactly zero to every printed cell.
   Hence `t_lost == clean_blocked` identically.

2. **No commit audit, no charge.** Records with zero commit audits and `t_lost > 0`: **0**. Records
   with `t_lost > (number of commit audits)`: **0**. The three policies that never audit the commit —
   B3 audit-on-insertion, B4 audit-on-retrieval, B6 two-stage — have mean `t_lost` **exactly 0.0000**
   at every ρ, while carrying 4.417, 0.812 and 0.850 false quarantines per episode respectively.
   Sweeps and quarantines generate no `t_lost` at all.

3. **The charge is a constant rate per commit audit**, across systems with wildly different
   allocations (pooled over all ρ):

   | policy | Σ t_lost | Σ commit audits | t_lost / commit audit |
   |---|---:|---:|---:|
   | B1 audit-at-commit | 40,616 | 627,468 | 0.06473 |
   | B2 uniform random | 10,396 | 152,364 | 0.06823 |
   | B5 risk-score | 9,201 | 139,462 | 0.06597 |
   | SW randomised | 20,256 | 313,352 | 0.06464 |
   | Oracle (+) | 7,636 | 107,936 | 0.07075 |
   | cost-greedy | 4,904 | 68,896 | 0.07118 |
   | Sentinel | 4,983 | 81,857 | 0.06087 |
   | B3 / B4 / B6 | 0 | 0 | — (no commit audit) |

   Normalised by `benign_inspected`, which for a commit-only policy counts exactly the commit audits
   landing on a *clean* patch, B1 gives 0.07737 blocks per clean audit = φ × P(solved | audited
   clean task), with φ = 0.12 and a solve rate near 0.6.

4. **Bit-identical across ρ.** B1's summed `t_lost` is the integer **10,154 at ρ = 0, 0.25, 0.5 and
   1** — not equal to four decimals, equal exactly. Keyed per episode on
   `(attack, delta, wf, seed)`, B1's `t_lost` is identical across all four ρ in **15,525 / 15,525**
   episodes, and its commit-audit count in 15,525 / 15,525, while its harm differs in 54% of them.
   The same holds for SW randomised (15,525 / 15,525). This is the signature of a draw that ρ does
   not enter.

5. **Sentinel's `t_lost` moves with ρ only through its audit schedule.** Sentinel is the one system
   whose `t_lost` varies (0.0815 / 0.0959 / 0.0695 / 0.0741), and it varies in lockstep with how
   many commit audits it chooses to buy (1.387 / 1.471 / 1.164 / 1.250); the per-audit rate is flat
   at 0.0587–0.0652. Its `t_lost` is identical across ρ in 12,631 / 15,525 episodes — but its
   commit-audit count in only 605 / 15,525. Sentinel's charge moves because its *allocation* moves,
   not because its detection does.

### The B1-prov confirmation

`B1-prov` is B1 whose commit alarm also reads the A7 provenance channel — a second, independent
N(0,1) score that has mean 0 on a clean patch, exactly like the patch score. If the mechanism is a
false-alarm charge, adding a second false-alarm channel must raise `t_lost` by roughly a factor of
two and leave everything else alone. It does:

* In **A0** (`a0.jsonl`, no provenance channel) B1-prov is bit-identical to B1 on every field:
  `t_lost` 0.7049, harm 0.6296, fq 0.0000, quarantines 0.0000, commit audits 10.079.
* In **A7** (`a7.jsonl`) the two policies still buy the identical audits (157,268 commit audits,
  142,176 of them on clean patches, 106,664 tasks solved — identical integers), but `t_lost` goes
  **0.7049 → 1.3843** (×1.9636) while harm goes 0.6296 → 0.1031.
* B1-prov's `t_lost` is itself bit-identical across ρ (5,400 at each of the four), which rules out
  any contribution from blocks on marked patches, whose firing probability does depend on ρ.

So the entire extra charge comes from the second false-alarm channel on **clean** patches, and the
paper's own discussion already says so for this case: *"a commit alarm quarantines nothing and the
entire price lands in lost clean work"* (discussion.tex). That sentence is correct. The sentences
about B1 are not.

**One residual I could not close.** Two independent channels at φ = 0.12 predict a ratio of
(1 − (1 − φ)²)/φ = 1.8834, and that is what the pure model gives (0.22610 / 0.12005 = 1.8834,
confirmed independent over 560,000 realistic `(seed, task_id)` pairs: P(both) = 0.01429 against
0.01439 under independence). The records give 1.9636 — about 920 blocks more than predicted, roughly
10 SD, so not sampling noise. Two candidate paths are ruled out: contributions from marked-delegated
tasks (excluded by ρ-invariance) and multiple clean patch writes per blocked task (no record has
`t_lost` exceeding its clean-commit-audit count). **The remaining 4.3% is unexplained and is recorded
as unexplained, not as zero.** It does not bear on the mechanism, which is settled by items 1–5
above, and it concerns a dev-only A7 diagnostic, not a headline cell.

### Verdict on the four hypotheses

| hypothesis | verdict |
|---|---|
| the charge follows the **audit** rate rather than the detection rate | **TRUE.** t_lost = 0 for every policy that buys no commit audit; a flat 0.061–0.071 per commit audit for every policy that does. |
| it follows **alarm firing** rather than confirmed detection | **TRUE**, and more sharply: it follows alarm firing *on a clean patch*, i.e. only false alarms. A correct block is charged to `patch_blocks`, never to `t_lost`. |
| it is charged per **quarantine attempt** regardless of correctness | **FALSE.** B1 issues zero quarantines in all 62,100 of its records. The charge is per blocked clean commit, and a commit block is not a quarantine. |
| **ρ does not reach B1's quarantine path** (harness defect) | **Vacuously true but for the wrong reason, and not a defect.** B1 has no quarantine path. ρ does reach B1's *detection* path — harm falls 5.4× — and is absent from the clean-patch score by design (D20), because a clean patch has no marker to expose. |

## 2. Why `fq` is exactly 0 for the B1 family

The definition, `runner.py:43-47`:

> ```
> ACCOUNTING OF A QUARANTINE (O7; branch = poisoned lineage only since 27/09, see step 7).
>     true_q            quarantines of a carrier with c_t[k] = 1 (just before removal)
>     fq                quarantines of a carrier with c_t[k] = 0: the draft's "false quarantines"
> ```

FQ is defined **per carrier quarantine**, and it is only ever incremented inside
`Episode.quarantine()`:

```python
poisoned = any(it.poisoned for it in self.store.live(k))
...
if poisoned:
    self.true_q += 1
else:
    self.fq += 1
```

B1 never calls it. Its `quarantine(t)` returns `None` for a commit alarm, so `fq` is not "small" or
"rounded to zero" — it is **structurally unreachable**. The records agree: **0 of 62,100** B1 records
have `fq > 0`, and **0 of 62,100** have any quarantine at all (`quarantines == []`). The paper's
"exactly zero false quarantines" is literally true.

**Does it mislabel errors? Yes — rhetorically, though not arithmetically.** B1's *only* error mode is
a false alarm at commit, and it commits 0.633 of them per episode in the headline cell — more
false-positive events per episode than any other non-oracle system's false *quarantine* count except
B3's. They are not lost: they are charged, in full, as `t_lost` at λ_T = 0.5. But they are booked
under a column named "clean tasks lost" and reported beside a column named "false quarantines"
showing 0.000, and a reader scanning those two columns will conclude that B1 makes no false-positive
errors and merely suffers collateral. The opposite is true: B1's entire `t_lost` column *is* its
false-positive column, and every unit of it is an error, whereas Sentinel's `t_lost` and every other
system's could in principle contain genuine O7 collateral (in this study they do not — see finding 1).
The two error types are also priced differently, λ_T = 0.5 against λ_Q = 0.54865, so a commit false
alarm is charged 8.8% less per event than a carrier false quarantine. That is defensible — rejecting
one patch is cheaper than removing a carrier — but it is a pricing decision the paper never states.

## 3. Defect or convention?

**Convention. Declared in the code, correctly implemented, and not a simulation defect — but the
paper's stated mechanism for it is wrong in four places, and the flat charge is a real and unflagged
consequence of the design.**

The convention is declared, verbatim, in `auditgame/v3/runner.py`:

> ```
>     t_lost            clean tasks lost = clean_lost_branch + clean solved patches BLOCKED at
>                       the commit review (step 5).  A blocked marked patch is harm prevented,
>                       not a loss (`patch_blocks` in counters()).
> ```

and in step 5 of the same docstring:

> ```
>                     A commit review whose alarm fires BLOCKS THIS TASK'S PATCH ONLY
>                     (`block_patch`) … the patch never enters the branch (v2's patch_blocks,
>                     the draft's "audit-at-commit"; M1 fix 27/09).  It is not a quarantine:
>                     no FQ, no other branch item is touched.
> ```

and in `auditgame/v3/baselines.py`:

> ```
>   A COMMIT alarm quarantines nothing: the runner blocks that task's patch only, so it never
>   enters the branch (v3/runner.py step 5; v2's patch_blocks, the draft's "audit-at-commit";
>   M1 fix 27/09).
> ```

ρ not reaching a clean patch is likewise by design, not by accident: D20 makes ρ the exposure of a
delegated *marked* patch, and `patch_mean` returns 0 for an unmarked one. A clean patch has no
provenance to betray, so there is nothing for ρ to modulate. The simulation is doing what it says.

**What is wrong is the paper.** Four passages attribute B1's charge to O7:

* `formulation.tex:123` — "under the quarantine accounting of O7 that charge is incurred even by
  *correct* quarantines, because removing a poisoned lineage removes the clean patches downstream of
  it" (also `paper-v3-conf/sections/formulation.tex:82`);
* `results.tex:595` — "a commit review that fires correctly quarantines a poisoned lineage and, by
  the declared accounting (O7), charges every clean patch behind it as a lost clean task" (also
  `paper-v3-conf/sections/results.tex:332`);
* `discussion.tex:40` — "audit-at-commit reaches low harm by quarantining the lineage of a poisoned
  patch, and under the declared accounting (O7) that removes the clean patches behind it";
* `introduction.tex:107` — "audit-at-commit reaches low harm by quarantining the lineage of a
  poisoned patch and removing the clean patches behind it".

`results.tex:595` is the worst of them: it states that a commit review quarantines a lineage, which
the runner and `baselines.py` both explicitly deny. And the O7 lineage charge those passages invoke
has a measured contribution of **exactly zero** in all 1,025,124 records examined.

**Three consequences the paper does not currently carry.**

1. B1's headline penalty is a **detector property, not an allocation property**. It equals
   (commit audits) × φ × P(solved on a clean audited task), so it would move if the detector's φ
   moved, and it is identical at all four exposures. Any reading that treats it as evidence about
   *where B1 audits* is reading a false-alarm rate.
2. The false-alarm term is a large share of the headline. In the headline cell at ρ = 0,
   λ_T · T_l = 0.5 × 0.6329 = **0.3164, i.e. 25.2% of B1's L of 1.258**; in the column that actually
   attains B1's maximum (`memory-last-ingress-e0.3@8`, T_l = 0.7923) it is 0.3962, **31.5% of that
   cell**. And **74.3% of the whole +30.0% headline gain** (absolute 0.3774) is the T_l difference:
   0.5 × (0.6329 − 0.0719) = 0.2805. The headline result is, to three-quarters of its magnitude, a
   statement that B1 blocks 8.8× more clean patches than Sentinel — which is true, and is a
   consequence of auditing every commit with a φ = 0.12 detector.
3. The generalisation in `discussion.tex` — *"any evaluation of a poisoning defence that scores harm
   alone will rank 'quarantine generously' above 'quarantine precisely'"* — survives, but its warrant
   changes. In this study nothing was ever ranked up by generous *quarantining*; B1 was ranked up by
   generous *blocking*. The lesson is about unpriced false positives of any kind, which is a broader
   and better claim, but it must be argued from the false-alarm charge, not from O7.

## 4. The exact table aggregation, and the 4% gap

**The gap is fully explained. Both the paper's number and the reconstruction are arithmetically
correct; they are two different aggregations, and Sentinel agreeing was a coincidence.**

The paper's table uses `metrics.table(...).value` (`auditgame/v3/metrics.py:137-161`), driven by
`tools/v3_p5_h18_heldout.py` with `field="loss"`, `HELD_OUT` (the 7 held-out attacks) and
`HEAD_DELTAS = (4, 8)`. Precisely:

1. Select one cell — world, ρ, χ = 1.33, d′ = 2.21, K_d = 2, budget b1 — and the records with
   `attack ∈ HELD_OUT` and `delta ∈ {4, 8}`.
2. Per record, `loss = harm + λ_Q · fq + λ_T · t_lost`, λ_Q = 0.54865, λ_T = 0.5 (`runner.loss_of`).
3. **The column key is `f"{attack}@{delta}"`** (`metrics.column`). Δ is *part of the column label*,
   not pooled: the headline "pools Δ ∈ {4, 8}" only in the sense that the call *spans* both, giving
   **7 × 2 = 14 columns**, not 7.
4. `W[w, c]` = **mean over seeds** of the field for workflow `w` in column `c` (NaN if absent).
5. `column_means()` = **mean over the workflows present in that column** — a second, equally-weighted
   stage, not a pooled mean over episodes.
6. `value` = **max over the 14 columns**.

Reproducing all four readings at ρ = 0 from `main.jsonl`:

| aggregation | B1 L | Sentinel L | B1 V_wc | Sentinel V_wc |
|---|---:|---:|---:|---:|
| **A. column = attack@delta, workflow-weighted** (= `metrics.table`) | **1.2580** | **0.8806** | **0.8618** | **0.8248** |
| B. column = attack@delta, pooled over episodes | 1.2616 | 0.8902 | 0.8605 | 0.8328 |
| C. column = attack (Δ pooled), workflow-weighted | 1.1594 | 0.8705 | 0.7893 | 0.8123 |
| D. column = attack (Δ pooled), pooled over episodes | 1.2059 | 0.8808 | 0.8109 | 0.8166 |

Variant A reproduces the printed table exactly, on every number checked:

| quantity | reconstruction A | paper |
|---|---:|---:|
| B1 L | 1.2580 | 1.258 |
| B1 V_wc | 0.8618 | 0.862 |
| B1 T_l | 0.6329 | 0.633 |
| B1 clean completion | 90.40% | 90.4 |
| Sentinel L | 0.8806 | 0.881 |
| Sentinel V_wc | 0.8248 | 0.825 |
| Sentinel T_l | 0.0719 | 0.072 |
| Sentinel clean completion | 98.91% | 98.9 |
| gain | +30.00% | +30.0 |

The reconstruction that gave 1.206 / 0.811 is **variant D** (1.2059 / 0.8109) — it differs from the
paper in *two* independent ways, both of which matter:

* **Δ was pooled into the column.** The max must run over 14 `attack@delta` columns, not 7 attacker
  columns. This is the dominant term: for B1 it is worth +0.0557 of L (D → B). B1 is far more
  sensitive to it than Sentinel because B1's worst column is at Δ = 8, where a longer horizon buys
  both more harm and more commit audits, so averaging Δ = 4 into it pulls the max down hard.
* **The mean was pooled over episodes** instead of the two-stage workflow-weighted mean (seeds →
  workflow, workflows → column). Worth −0.0036 of L for B1 (B → A).

**Why Sentinel matched and B1 did not.** For Sentinel the two corrections are +0.0094 and −0.0096 and
cancel to −0.0002: 0.8808 (D) against 0.8806 (A), agreeing to three decimals **by coincidence**.
Sentinel's exact match was therefore not a validation of the reconstruction; it was luck, and B1
exposed it.

**On the direction.** A B1 that reads higher does inflate the reported gain — the same records give
+30.0% under A and +26.9% under D — so the concern was the right one to raise. But the aggregation
is symmetric: it is applied identically to B1 and to Sentinel, it is declared in
`metrics.py`'s module docstring (*"V = max over attacker columns (attack@delta) of the column's
workflow-weighted mean harm"*), and it is the same rule `metrics_v2.harm_table` has always used.
**So the headline is not inflated by an inconsistency.** What it *is* is sensitive: the headline
drops from +30.0% to +26.9% under a reading a careful reader could plausibly adopt, and the gate is
15%, so the verdict survives either way — but the paper should say which reading it means.

**A documentation gap worth fixing.** The paper never defines "attacker column". The Table 2 caption
says only *"re-maximised across attacker columns within every draw"*, and the surrounding text says
*"Δ ∈ {4,8}"* as if pooled. A reader has no way to learn from the paper that Δ is part of the column
key and that the max runs over 14 columns rather than 7 — which is exactly the misreading that
produced the 1.206. One clause in the caption closes it:

> …re-maximised across attacker columns within every draw, where a column is one (attacker policy, Δ)
> pair, so the maximum runs over the 7 held-out attackers × Δ ∈ {4, 8} = 14 columns; a column's value
> is the mean over seeds within a workflow, then the mean over workflows.

## 5. The corrected sentence

The primary replacement, for `results.tex:594-597` ("Where the two metrics disagree, and why"):

> B1 audits every commit, so its false-quarantine column is zero by construction — a commit alarm
> blocks that task's patch and quarantines nothing, and only a carrier quarantine registers an FQ.
> The charge it does pay is the mirror image of that. Every commit review is a fresh draw against the
> shared detector, so a clean patch is blocked with the detector's false-positive rate φ = 0.12, and
> a blocked clean patch that passed its tests is one clean task lost. B1 buys 9.8 commit audits per
> episode in the headline cell and therefore destroys 0.633 clean tasks per episode there (clean
> completion 90.4%) against \Sent{}'s 1.2 audits and 0.072 (98.9%). The charge scales with the
> commit-audit rate and not with
> detection: it is identical at all four exposures ρ ∈ {0, 0.25, 0.5, 1} while B1's harm falls 5.4×,
> because a clean patch's score has mean 0 at every ρ (D20). At λ_T = 0.5 that term alone adds 0.316
> to B1's loss against 0.036 to \Sent{}'s, and with λ_Q = 0.54865 times \Sent{}'s false quarantines
> the two corrections account for the whole sign change.

The clause to strike everywhere it appears — `formulation.tex:123`,
`paper-v3-conf/sections/formulation.tex:82`, `discussion.tex:40`, `introduction.tex:107`,
`results.tex:595`, `paper-v3-conf/sections/results.tex:332` — is the attribution of B1's charge to a
quarantined lineage. A one-line drop-in for the `formulation.tex` sentence, which states the general
principle rather than B1's numbers:

> A policy can drive harm down by rejecting work generously, and the clean work this destroys is
> charged in $\Loss$ and invisible in $\Vwc$: a commit review that blocks a clean patch, and a
> correct carrier quarantine that removes the clean patches downstream of a poisoned lineage (O7),
> both lose clean tasks while recording no false quarantine at all. In this study the charge is
> entirely of the first kind — `clean_lost_branch` is 0 in all 931,500 held-out records, so the O7
> lineage term never fires — and B1's 0.633 lost clean tasks per episode are 0.633 false alarms of
> the shared detector at $\varphi = 0.12$.

And `discussion.tex`'s generalisation should be re-based on false positives rather than on
quarantines:

> …any evaluation of a poisoning defence that scores harm alone will rank "reject generously" above
> "reject precisely", and will keep doing so until the clean work destroyed is priced — whether it is
> destroyed by a false alarm at commit, as B1's is, or by the collateral of a correct quarantine, as
> O7 prices.

## What I did not measure

* `spikes/v3-run/eval-pass1/br.jsonl` — not opened. Declared not-a-result (7.8 GB partial); no
  best-response number appears above.
* No episode was simulated and no evaluation grant was consumed; the only executed model code is the
  pure `ObservationModel.commit` on synthetic clean patches.
* The 4.3% residual in the A7 B1-prov ratio (1.9636 observed against 1.8834 predicted) is
  **unexplained**, not zero. It is a dev-split A7 diagnostic and bears on no headline cell.
* Whether the same flat-charge pattern holds in the H18 and K_d blocks (`eval-p1-h18kd/`) was not
  checked; only `main.jsonl` and the A7 dev pair were read.
