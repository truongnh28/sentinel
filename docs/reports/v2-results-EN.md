# v2 results (English companion)

This document summarises the single evaluation run of the frozen v2 configuration (sha256:c789fa7362e0). Every number carries its JSON path under `auditgame/spikes/v2/`. The Vietnamese report `docs/reports/v2-so-voi-draft.md` is the authors' full working report.

---

## 0. How to read this file

**Source abbreviations.** Paths are given relative to the repository root (Section G explains the layout). Elsewhere in this document a bare path such as `spikes/...`, `reference/...`, `tools/...` or `frozen/...`, or a bare module name such as `draft_setup.py`, is relative to `auditgame/`; a `docs/...` path is already relative to the repository root.

| Tag | File | What it holds |
|---|---|---|
| `S` | `auditgame/spikes/v2/eval-summary.json` | run block, controls, endpoint curve, Table 2, Table 3, gain by Delta, detectors, transfer, Verified-only, gate world, denominators |
| `W` | `auditgame/spikes/v2/eval-sweeps-summary.json` | eta_Q, match, persistent-drift and budget (EXPLORATORY) sweeps |
| `G` | `auditgame/spikes/v2/small-games.json` | B7 on the 240 small games |
| `T` | `auditgame/reference/v2_tuned.json` | beta-hat, tau5, eta_Q, all 72 tuned mixtures |
| `PR` | `docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md` | D1-D34, endpoint, P1-P6, Q1-Q12, execution record (Vietnamese) |
| `RP` | `docs/reports/v2-so-voi-draft.md` | the results report (Vietnamese); section numbers below are its own |
| `FR` | final branch review (`.superpowers/sdd/final-review.md`, gitignored, NOT in the package) | findings I1-I5, M1-M11; every finding the paper needs is also declared in `RP` and in `PR`'s execution record, so cite those |

**JSON path syntax.** `S:curve_rho."0.25".lo` means key `curve_rho`, then key `"0.25"`, then key `lo`. The rho keys are the strings `"0"`, `"0.25"`, `"0.5"`, `"1"`; Delta keys are `"0"`, `"1"`, `"2"`, `"4"`, `"8"`; system keys are exactly `B1 audit-at-commit`, `B2 uniform random`, `B3 audit-on-insertion`, `B4 audit-on-retrieval`, `B5 risk-score`, `B6 two-stage`, `Sentinel-A1`, `A1 -randomization`, `A1 -alarm memory`, `A1 -transition uncertainty`, `A1 -benign-drift`, `A1 -regime estimate`, `Oracle (control)`.

**Rounding.** Numbers are printed at the precision the report uses, which the paper may print as is: harm-scale quantities (V, V_BR, exploitability, L, absolute differences and their CIs) at 4 decimals; percentages (gain, CI bounds of the gain, FQ, clean completion) and detection delay at 2 decimals. If a writer wants fewer digits, round the raw JSON value, not the printed one. Negative numbers use ASCII `-` so they paste into LaTeX math.

**Labels.** POST HOC = not preregistered and added after the single eval run, mostly because of the final review (read from the pinned records or from code; no simulation), plus the report's crossover reading rule; it must be labelled post hoc in the paper. EXPLORATORY = preregistered as exploratory, no test attached. NOT EXERCISED = the arm could not change any decision in that cell (not "zero effect").

**The headline cell** (used everywhere unless stated): detector mid, trigger delay Delta in {4, 8}, chi = 1.34, budget b1, transient drift, drift match 1, the 7 held-out attackers, 57 eval workflows / 16 repos, 10 seeds.

---

## A. Study identity and setup

### A.1 Identity

| Fact | Value | Source |
|---|---|---|
| Study | v2: reproduces the §4 carrier-audit model set out in the preregistration, built faithfully rather than tuned to a target | `PR` title, D1-D34 |
| Preregistration | declared 25/09/2026, before any line of v2 code; replaces the 24/09 version (the stage-gate world), which is kept as the secondary world (D29) | `PR` lines 1-5 |
| Tuning | dev split only (the django family, 43 workflows), tuning seeds 1 and 2 | `PR` D8, D24; `tools/select_mixture.py` |
| Freeze | manifest `frozen/MANIFEST.json`, field `digest` = `c789fa7362e0...`; every header prints `freeze: clean sha256:c789fa7362e0` | `S:run.header_start`, `S:run.header_summary` |
| Single eval run | 25/09/2026, 16:00:46 to 16:29:47 (+07:00), `--split eval`, exit 0 | `spikes/v2/eval-log.txt` |
| Code state at the run | git HEAD `5c99042`, `auditgame/` clean (`git_clean = true`, `git_dirty = []`) | `S:run.git_head`, `S:run.git_clean` |
| Tools outside the freeze digest, pinned by sha256 in the run block | `tools/run_draft_eval.py` `388510ac...`, `tools/select_mixture.py` `3fa56fd7...` | `S:run.sha256` |
| Raw records | 7 JSONL files, about 5.0 GB, NOT committed (D33); pinned by sha256, line and byte counts | `spikes/v2/eval-records.sha256` |
| Primary result | `HEADLINE_RHO = None` (not chosen before tuning), so the preregistered endpoint is the whole curve over rho_patch (D20) | `S:run.headline_rho = null`; `PR` execution record, Task 10 Step 0 |
| Reference rho for the controls | 0.25 (D23) | `S:run.ref_rho` |
| v1 | manifest `sha256:4ff1c8f72df4`, kept as a record and fallback only; no v1 number enters the paper (D34) | `PR` line 5, D34 |
| Compute | 0.99 ms per simulated run; tuning about 3.1e6 runs (0.09 h on 10 cores); eval estimated at 1.15e7 runs (0.32 h), actual wall clock 29 min | `PR` execution record, Task 10 Step 1; `eval-log.txt` |

### A.2 The model (the primary "carrier world")

Source: `PR` D1-D5, D16, D17, Q1-Q3; code `draft_setup.py`, `carrier_runner.py`.

- **Carriers.** memory, skill, queue, branch (`core.CARRIERS`).
- **One action per task (D1).** Each task t the defender picks one action a_t in {none} U {(k, d) : k in {memory, queue, skill}} U {(commit, d)}, depth d in {1, 2, 3}. The runner buys the deepest affordable depth not above the requested one (one depth ladder for every policy), or nothing.
- **Sweep of carrier k** (k in memory, queue, skill): scores EVERY live item of k at the end of task t at depth d, one independent detector draw per inspection (D16). The policy sees the carrier signal it paid for (D5: a posterior computed from the mean likelihood ratio of the scores, `scoring.carrier_score`), updates, then decides which FIRING items to quarantine (quarantined items leave the store). Baselines quarantine every firing item ("quarantine on any anomaly"); library members and Sentinel use Algorithm 1 line 8.
- **Commit audit** (the branch carrier's audit, at one point in time): reviews THIS task's patch. A firing patch is blocked: a marked patch loses its marker (its branch write is quarantined, never merged); a clean solved patch that fires costs one T_lost. The commit alarm is NOT evidence about any carrier (D17). The branch carrier is never swept.
- **Order inside task t:** buy the action, inject the payload at iota (both attack channels write into the store an audit reads), the agent runs task t, then the bought action executes. Harm is read at sigma.
- **Attack timing.** The payload is inserted into carrier k at iota and triggers at sigma = iota + Delta; Delta is a cell parameter. Dormancy: the payload is not retrieved by any task in [iota, sigma) (`build.plan_poison_all`); a rule with no feasible placement leaves the denominator.
- **Harm (verified harm).** harm = 1 iff the task at sigma is solved (public tests pass) and its final patch still carries the marker (the sealed hidden test fails); else 0 (`oracle.harm_of`). Only episodes whose sigma task is solved in the clean run are kept (survival filter N4), so harm = "the patch at sigma ships the marker".
- **Audit cost.** kappa per target from the reproduced price table: memory 0.4, queue 0.9, skill 1.6, commit (branch) 4.1; an action (k, d) costs kappa(k) x d.
- **The kappa <-> carrier bijection** (insertion -> memory 0.4, retrieval -> queue 0.9, delegation -> skill 1.6, commit -> branch 4.1) is **our reading of the reproduced model's §8, pending confirmation** (D2, Q2; `RP` §10 item 1). The four audit kinds and their prices are described in its §7 ("Audit actions", p. 5) and Table 1 (p. 5). chi does not depend on the bijection, and at budget b1 no action is ever budget-limited, so the bijection matters only in the EXPLORATORY budget sweep.

### A.3 chi and the budget b1

Source: `PR` D2, D4, D4b, Q2, Q4; `draft_setup.py`.

- kbar = mean of the four prices = 1.75.
- **chi, v2 label (D2):** chi = 2 x MAD / kbar = 1.3429 on the reference price table ("chi = 1.34"). An alternative §4 formula, chi_range = max|kappa(k) - kappa(k')| / kbar = 2.1143 (printed 2.114 in `PR` Q2). Both are reported; chi_range = 1.574 x chi on the interpolation path.
- **Grid:** kappa(lambda) = kbar + lambda (kappa - kbar), lambda = chi / 1.34 (so chi = 1.34 is exactly the reference price table). chi in {0, 0.5, 1.34} <-> chi_range in {0.0000, 0.7889, 2.1143} (`W:budget_EXPLORATORY.<rho>."chi=<chi>".<share>.<Delta>.chi_range`). The grid labels are nominal: the rescaled table at label 0.5 has 2 x MAD / kbar = 0.5011, at label 1.34 it has 1.3429.
- **The main grid runs at chi = 1.34 only.**
- **Budget b1 = H x 3 x 4.1** = 12.3 H, anchored on the reference price table and kept fixed at every chi (D4). Every policy is paced: spent <= B (t + 1) / H.
- **D4b.** At b1, B / H = 12.3 equals the price of the most expensive action (a depth-3 commit), so one action per task is never budget-limited: the main grid measures "where to look", not "how much budget is enough". chi and the budget-dependent part of Theorem 4 are read only in the share x chi sweep (share in {0.25, 0.5, 0.75, 1} of b1), labelled EXPLORATORY. In that sweep B1 is also budget-limited below share 1 (e.g. at share 0.25 and chi = 1.34 a depth-1 commit, 4.1, exceeds the per-task pace 3.075).

### A.4 Corpus

Source: `PR` D8, Q6, execution record Task 2 and Task 11; `corpus_v2.py`.

- **Sources:** SWE-bench Verified (12 repos; seaborn with 2 instances and flask with 1 are too short, so 10 usable) + SWE-bench Multilingual (`test` split, 300 instances, 41 repos, 9 languages).
- **Workflows:** per repository, instances sorted by `created_at`, cut into consecutive windows of H ~ U{6..14} tasks, H seeded per repo (`seed_of(2027, repo, offset)`); two passes (offsets 0 and 3) so an instance is in at most 2 workflows (reuse <= 2).
- **Result:** 100 workflows over 17 repositories (85 Verified workflows, 15 Multilingual). Feasibility over the whole corpus: 100/100 workflows at Delta <= 4, 58 at Delta = 8 (`PR` Q6).
- **Split (D8):** dev = the largest repo family, django (43 workflows); eval = 57 workflows over 16 repos, Kish effective number of clusters 8.1 (it would be 2.5 with django left in eval). Every tuning step ran on one repository, so "dev vs held-out" is transfer from django to 16 other repos.
- **Eval clusters (workflows):** sympy 15, sphinx 8, scikit-learn 6, matplotlib 5, lombok 3, xarray 3, pytest 3, astropy 2, caddy 2, laravel 2, preact 2, rubocop 2, fastlane 1, fluentd 1, phpspreadsheet 1, bat 1 (`PR` execution record, Task 11). Kish = 57^2 / 401 = 8.10.
- **Verified subset of eval:** 7 repos / 42 workflows (sympy, sphinx, scikit-learn, matplotlib, xarray, pytest, astropy); the other 15 eval workflows (9 repos) are Multilingual. `PR` D8/Q6 wrote "9 repos" for this subset; the data has 7.
- **At Delta = 8** only 34 eval workflows / 12 repos have a feasible held-out placement (union over the 7 held-out columns; per column 26-34 workflows, B.17).
- **What is real and what is simulated:** workflows are real in sequence and topic (SWE-bench metadata, topics from the gold patch), simulated in execution (no task is executed; the agent is a mock; harm is scored by a marker oracle).

### A.5 Attacker class

Source: `PR` D7, D18, D27, Q10; `attackers_v2.py`; `S:transfer_note`.

- **18 scripted rules** `<carrier>-<iota rule>-<channel>-e<eps>`: carrier in {memory, skill, queue, branch, uniform}; iota rule in {first, mid, last} feasible placement; channel in {write, ingress}; eps (topic-overlap budget of the payload: its topic is a ceil(eps x |B|)-token subset of the target task's topic B, and a task retrieves an item when the Jaccard similarity of their topic tokens is >= 0.5) in {0.3, 0.6, 1.0}. "uniform" draws the carrier per workflow.
- **Held-out (7)**, the names with the smallest `seed_of("heldout-v2", name)`: `branch-first-write-e0.6`, `memory-last-ingress-e0.3`, `memory-last-write-e0.6`, `memory-mid-write-e0.3`, `queue-last-ingress-e0.6`, `queue-mid-write-e0.6`, `skill-last-write-e1.0`.
- **Development (11):** `branch-last-ingress-e0.6`, `branch-last-write-e0.6`, `branch-mid-ingress-e0.6`, `memory-first-write-e0.6`, `memory-last-ingress-e0.6`, `queue-first-write-e0.6`, `skill-first-write-e0.6`, `skill-last-ingress-e0.6`, `skill-last-write-e0.6`, `uniform-last-ingress-e0.6`, `uniform-mid-write-e0.6`.
- **The channel is inert** in the carrier world (both channels land in the store), so held-out hygiene is done on behaviour keys (carrier, iota rule, eps), not on names.
- **D18 tuning columns (6):** development and BR columns whose behaviour keys can never coincide with a held-out attacker's on any workflow, one name per distinct behaviour set: `branch-last-ingress-e0.6`, `branch-mid-ingress-e0.6`, `memory-first-write-e0.6`, `queue-first-write-e0.6`, `skill-first-write-e0.6`, `skill-last-ingress-e0.6` (all eps = 0.6; they cover all four carriers).
- **Overlap:** 3 of the 11 development attackers can realise a held-out behaviour key: `memory-last-ingress-e0.6`, `uniform-last-ingress-e0.6`, `uniform-mid-write-e0.6` (`S:transfer_note`), so the plan's "development vs held-out" row is not a clean transfer; the D18 row is.
- **Best response (D27), the "BR menu":** a Stackelberg attacker that knows the committed policy (Sentinel's mixture) but not its per-episode draw. Menu = every feasible (carrier, iota, sigma) at the cell's Delta over all four carriers, at eps = 0.6 only. Cross-fit: per workflow, choose the placement on the odd seeds and score it on the even seeds, then the reverse, and average. Menu sizes: B.18.
- **16 BR columns** (4 carriers x 2 channels x {first, last}) also run in the main grid as scripted columns; no summary number uses them (`S:run.records_kept` drops them).
- **No LLM attacker** in the class.

### A.6 The world: agent, drift, patch exposure, detectors

Source: `PR` D6, D16, D20, Q7, Q8; `world_v2.py`, `detector.py`, `agent.py`, `tools/select_mixture.py` (`make_world`, `KERNELS`).

- **Agent: `StagedMockAgent`** (reproduces v1's MockAgent draw for draw when there is no drift; every draw keyed on the workflow and seed, D19). Per task: retrieves the items matching the task topic; if a retrieved item is poisoned, the patch carries the marker with the adoption probability (0.85 in the nominal kernel); always writes a memory note; induces a skill with probability 0.55 when anything was retrieved (the skill inherits poison if a poisoned item was seen); writes a branch item (poisoned iff the patch carries the marker); leaves a queued call with probability 0.35; solves the task with probability 0.62.
- **Kernels:** nominal (adoption 0.85, skill induction 0.55) in every eval cell; tuning also uses low and high (both shifted by zeta = 0.10: 0.75/0.45 and 0.95/0.65).
- **Benign drift (D6, transient events):** each task, carrier k gets a drift event with probability beta_world = {memory 0.314, skill 0.058, queue 0.033, branch 0}; a drift item scores like poison (mean match x d') ONLY in the task it happens (`DRIFT_VISIBLE_TASKS = 1`), then like a clean item. Headline match = 1; swept over {0, 0.5, 1}; "persistent drift" (anomalous for life) is a sensitivity check. The payload scores like poison for as long as it lives.
- **Patch exposure rho_patch (D20):** a patch that got the marker through direct retrieval scores with mean d' x sqrt(depth); a patch that got it only through a skill or a queued call (a "delegated" patch) scores with mean rho_patch x d'(depth 1), and depth does not help. Grid {0, 0.25, 0.5, 1}. The defender knows rho_patch and is tuned per rho. rho_patch was NOT calibrated to make V(B1) = 0.412. Scope: rho_patch acts only on attacks placed directly in skill or queue; a memory -> skill -> patch chain does not produce a delegated patch at sigma, because of dormancy.
- **Detector (one shared by every system; D16):** score s ~ N(d' x 1[poisoned], 1); fires iff s > tau_det; d' = z(psi) - z(phi), tau_det = z(1 - phi); depth d multiplies d' by sqrt(d) and keeps tau_det. The three detector settings:

| Setting | (psi, phi) | d' (depth 1) | tau_det | d' at depth 3 |
|---|---|---|---|---|
| weak | (0.75, 0.20) | 1.5161 | 0.8416 | 2.6260 |
| mid (headline) | (0.85, 0.12) | 2.2114 | 1.1750 | 3.8303 |
| strong | (0.92, 0.06) | 2.9598 | 1.5548 | 5.1266 |

- **Secondary world (D29):** the four audit kinds read as stage GATES over all carriers (the 24/09 reading); only four fixed baselines run there (B1g commit, B2g uniform, B3g insertion, B4g retrieval); it answers "why not read §8 as gates" and is never used to compare Sentinel.

### A.7 Policies

Source: `carrier_policies.py`, `sentinel.py`; `PR` D9-D12, Q9.

**Baselines (all quarantine every firing item):**

| Name | Behaviour |
|---|---|
| B1 audit-at-commit | commit audit at depth 3 every task |
| B2 uniform random | each task one of the four targets uniformly at random, depth 3 |
| B3 audit-on-insertion | sweep memory (the insertion audit) at depth 3 every task |
| B4 audit-on-retrieval | sweep queue (the retrieval audit) at depth 3 every task |
| B5 risk-score | depth-1 sweeps in a fixed rotation memory -> queue -> skill; a depth-3 commit audit on the task after a sweep whose carrier signal exceeds tau5 (tau5 = 0 means escalate after every sweep) |
| B6 two-stage | a random depth-1 screen of one sweep carrier; a depth-3 confirmation sweep of the same carrier on the task after it fires |
| Oracle (control) | POSITIVE CONTROL, not a competitor: told the attacked carrier; sweeps it at depth 3 every task (commit at depth 3 if the attacked carrier is branch) |

**The 28-member library (line 5's support), all at depth 3 unless named, all using line 7 and line 8:**
- **SW, stage-weighted (8):** each task draws the target with weights over (memory, queue, skill, commit): `commit` (0,0,0,1), `uniform` (1,1,1,1), `sweeps` (1,1,1,0), `memory` (3,1,1,1), `queue` (1,3,1,1), `skill` (1,1,3,1), `commit3` (1,1,1,3), `nomemory` (0,1,1,1). Names `L-SW-<name>`.
- **BT, belief-threshold (12):** commit while p_attack <= tau; above tau, SAMPLE a sweep carrier from floor x uniform + (1 - floor) x posterior carrier mass. tau in {0.3, 0.5, 0.7, 0.9}, floor in {0, 1/3, 2/3} (`L-BT-<tau>-f0|f1|f2`).
- **RO, carrier-rotation (8):** cycle through c3 = (memory, queue, skill) or c4 = (memory, queue, skill, commit), each target held p in {1, 2} tasks, depth d in {2, 3}, from a random phase drawn per workflow (`L-RO-<c3|c4>-p<p>-d<d>`).
- **Behavioural duplicates (POST HOC, FR I1; verified in B.22):** 10 of the 28 members play exactly B1: the 9 BT members with tau >= 0.5 and `L-SW-commit`. The library has at most 19 distinct behaviours.

**Sentinel-A1 = Algorithm 1, lines 1, 5, 7, 8 (D9, D9b, D10, D11):**
- **Line 1:** Sentinel is GIVEN the cell's regime (Delta; chi is fixed at 1.34 in the main grid), i.e. a perfect regime estimator, declared in advance (D9b). It plays the mixture tuned for (rho, detector, Delta).
- **Line 5:** commits to the robust FQ-constrained minimax mixture over the 28 members, solved on dev for that regime; reveals only the mixture; draws ONE member per workflow episode (the draw is keyed on the workflow and the seed). The member then is the executed policy.
- **Line 7:** the member's drift-aware window belief (`belief_v2.DriftBelief`: windows (carrier, iota, sigma) plus NULL, prior p_attack = 0.5, drift as a competing cause with rate beta-hat), updated from the carrier signals bought.
- **Line 8:** quarantine a firing item iff P(payload | score) > eta_Q, against three hypotheses: payload (prior p_k / n_k, the carrier's window mass over its live items), a fresh drift event (prior beta-hat_k / n_fresh, only for items created this task), clean (the rest); Gaussian likelihoods. eta_Q = 0 is the naive rule (quarantine any firing item with p_k > 0); 0.3543 = lambda_Q / (1 + lambda_Q) is the Bayes value for binary harm.
- **Line 3** (exact solve) runs only on the small games (B7, B.15).

**The five ablations (Table 3):**

| Arm | What it changes |
|---|---|
| A1 -randomization | plays the tuned `pure` member (argmin of worst-case dev harm within the FQ cap; ties by FQ, then name, D32) with member seed 0, i.e. one schedule for every workflow |
| A1 -alarm memory | stateless belief (reset before every update) |
| A1 -transition uncertainty | the nominal-kernel mixture instead of the robust (3-kernel) one |
| A1 -benign-drift | beta-hat = 0 in the belief and in the line-8 posterior |
| A1 -regime estimate | NEW in v2 (Q9): drops line 1 and plays the mixture tuned over all Delta pooled ("all") |

### A.8 Tuning (dev only, before the freeze)

Source: `tools/select_mixture.py`; `T`; `spikes/v2/select-log.txt`; `PR` D6, D9, D11, D12, D26, D32, execution record Task 10.

1. **beta-hat by moments (D6)** on OBSERVED alarms of dev clean runs, never on drift labels: an insertion probe scores every new item at depth 1 (mid detector); E[F_k] = beta_k T psi_m + (N_k - beta_k T) phi, psi_m = Phi(match d' - tau_det), so beta-hat_k = (F_k - N_k phi) / (T (psi_m - phi)). Result (`T:betas`): memory 0.3058, skill 0.0654, queue 0.0326, branch 0.0141 (world: 0.314, 0.058, 0.033, 0).
2. **tau5 for B5 (D12):** argmin of worst-case dev harm at the headline cell (nominal kernel), grid {0, 0.1, 0.2, 0.3, 0.5, 0.7}, ties to the smaller value.
3. **eta_Q (D11):** for each value of the grid {0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3543, 0.5}, the constrained minimax over the 28 members at the headline cell with 3 kernels; keep the lowest worst-case harm (to 4 decimals), ties to the lower FQ%.
4. **Mixtures (D9, D26, D32):** at that eta_Q, for each (detector, regime), regime in {Delta = 0, 1, 2, 4, 8, "all"}: M[pi, col] = max over the 3 kernels of dev harm in each D18 tuning column; F_pi = FQ% (max over kernels, pooled over all Delta, `FR` M4). LP: minimise z s.t. sum_pi x_pi M[pi, col] <= z for every column, sum_pi x_pi F_pi <= 10 (the FQ cap, D26), sum x = 1, x >= 0. If infeasible, the unconstrained LP with `cap_ok = false` (never happened: `cap_ok` true in all 72 cells). **D32 tie-break:** among mixtures that keep the optimal worst case (tolerance 1e-9), a second LP takes the lowest FQ%. Also stored per cell: the nominal-kernel mixture (for "-transition uncertainty") and the `pure` argmin (for "-randomization").
5. 72 tuned cells = 4 rho x 3 detectors x 6 regimes (18 per rho).
6. **Tuning averages harm per column over episodes, while the eval averages per-workflow means** (`FR` M4; declared in `RP` §10).

**Tuned values per rho (`T:rho.<rho>.tau5`, `T:rho.<rho>.eta_q`):**

| rho_patch | tau5 | eta_Q | dev worst-case harm at the chosen eta_Q (FQ %) | why that eta_Q (`select-log.txt`) |
|---|---|---|---|---|
| 0 | 0.1 | 0 | 0.4117 (6.37) | lowest harm; 0.4197 at eta_Q = 0.01 |
| 0.25 | 0.1 | 0 | 0.3863 (5.97) | lowest harm; 0.3947 at eta_Q = 0.01 |
| 0.5 | 0 | 0 | 0.2928 (4.46) | lowest harm; 0.3007 at eta_Q = 0.01 |
| 1 | 0 | 0.3543 | 0.1589 (0.15) | harm tied at 0.1589 for every eta_Q from 0 to 0.3543; the tie rule picks the lowest FQ |

The mixtures Sentinel plays in the headline cells are in B.19. At rho <= 0.5 the chosen eta_Q = 0 and, at rho >= 0.5, tau5 = 0 are the new lower edges of grids widened after the D30 touch (E.1). The dev harm-vs-eta_Q log is monotone, so the D26 objective picks eta_Q = 0 whenever the FQ cap does not bind (`RP` §10 item 12; C.10).

### A.9 Metrics (§9.3; D13, D15, D27)

Source: `metrics_v2.py`, `tools/run_draft_eval.py`.

- **V, worst-case harm (D13):** the maximum over the 14 columns (7 held-out attackers x Delta in {4, 8}) of the column mean, where a column mean is the mean over that column's feasible workflows of each workflow's mean harm over its surviving seeds. (It is a max over 14 (attacker, Delta) columns, not "over attackers"; `FR` I4.)
- **Gain** = 100 x (1 - V(S) / V(B1)); **absolute difference** = V(B1) - V(S) (positive: Sentinel has less harm). Every gain is printed with its absolute difference and CI.
- **V_BR, cross-fitted best-response value (D27):** per workflow, the attacker's placement is chosen on the odd seeds and scored on the even seeds and vice versa, averaged; mean over workflows; maximum over Delta in {4, 8}. Attacker = the BR menu (A.5), eps = 0.6.
- **Exploitability** = V_BR - V.
- **FQ %** = 100 x (benign items quarantined) / (benign objects inspected); "inspected" counts benign live items scored in sweeps plus clean patches reviewed at commit (D15). FQ(B1) = 0 by construction: a commit audit quarantines no item, and a blocked clean patch counts in T_lost.
- **FQ items / episode** = benign items quarantined per episode (`false_removed_per_ep`).
- **T_lost** = clean solved patches blocked at commit; **clean completion %** = 100 x (1 - sum T_lost / sum tasks solved).
- **Detection delay** = mean (detected_at - iota) in tasks, over the episodes with a detection; detected_at = the first task at which a marked patch was blocked at commit or a poisoned item was quarantined (it can be a commit block at or after sigma, `FR` M9).
- **Loss L (D15), reported, never tuned on:** per episode L = harm + lambda_Q x (benign items quarantined in the episode) + lambda_T x T_lost, lambda_Q = 0.54865 (= 1.0973 x lambda_T), lambda_T = 0.5 (`S:run.lambda_Q`, `S:run.lambda_T`); worst-case L = max over the same 14 columns. `PR` D15 writes "lambda_Q x FQ"; the code uses the COUNT of false quarantines, i.e. Q_false.
- **Controls (D28), checked BEFORE any Sentinel number is read:** (+) the Oracle reaches V <= 0.05 in the headline cell at the reference rho; (-) at Delta = 0, neither sweep-only baseline (B3, B4) beats B1, since a sweep runs after the agent and cannot act before sigma when iota = sigma. A failed control withholds every Sentinel number.
- **Denominators (N3):** every row carries N workflows, N repos, N episodes (episode = workflow x attacker x Delta x seed); drops are recorded with their reason: "infeasible" (no placement at this Delta and H) and "non-surviving" (N4: the sigma task is not solved in the clean run).

### A.10 Statistics

Source: `metrics_v2.gain_ci`, `gain_vs_best`; `PR` D14, D21, D22, D25, "Endpoint chinh".

- **Repo-family cluster bootstrap (D14):** 10,000 resamples (`n_boot` stamped on every CI), bootstrap seed 2026. Each resample draws the 16 eval repo families with replacement, pools their workflows, recomputes every column mean on the resampled workflows and RE-TAKES THE MAX over the 14 columns, for both policies; percentile CI.
- **D25 multiplicity:** the 15% statement over the 4-point rho curve uses two-sided CIs at 1 - 0.05/4 = 98.75% (family alpha 0.0125, `S:family_alpha`), for both `curve_rho` and the D22 line. (A HEADLINE_RHO would have used 95%; there is none.) Every other CI in this file is a two-sided 95% CI with no multiplicity correction.
- **Margin:** the 15% margin is met at a rho iff the lower 98.75% bound of the gain is >= 15 AND the gain is readable (D21); JSON `meets_margin`.
- **D21 readability:** a relative gain is read only if V(B1) > 0, B1 shows >= 10 harm events in its worst column, and <= 1% of resamples have V(B1) = 0; otherwise "not readable" and only the absolute difference is read. In this run every gain entry in both summaries is readable (B.20).
- **D22:** the absolute difference between Sentinel and the BEST baseline in B1-B6, the best baseline re-chosen inside every resample (the CI pays for the selection).
- **No CI** exists in the summaries for a single system's V, for V_BR, for exploitability or for L.
- **Coverage caveat (POST HOC, `FR` I4):** a percentile bootstrap over 16 unbalanced families (sympy holds 15 of 57 workflows; only 12 families at Delta = 8) may cover below its nominal level.

### A.11 Seeds and grids

| Item | Value | Source |
|---|---|---|
| Eval seeds | 1-10 (D24) | `S:run.seeds` |
| Tuning seeds | 1, 2 | `PR` D24 |
| Bootstrap seed | 2026 | `metrics_v2.gain_ci` |
| Corpus seed | `seed_of(2027, repo, offset)`, offsets 0 and 3 | `corpus_v2.py` |
| Held-out selection | 7 smallest `seed_of("heldout-v2", name)` | `attackers_v2.held_out` |
| Per-episode draws | keyed on `seed_of(wf_id, seed)` (D19) | `carrier_runner.rs_of` |
| Delta | {0, 1, 2, 4, 8} (headline {4, 8}) | `S:run.deltas` |
| rho_patch | {0, 0.25, 0.5, 1} | `S:run.rhos` |
| Detectors | weak, mid, strong (headline mid), at every rho | `S:run.rho_mid_only = false` |
| chi | 1.34 in the main grid; {0, 0.5, 1.34} in the budget sweep | `draft_setup.CHIS` |
| Budget | b1 in the main grid; share {0.25, 0.5, 0.75, 1} x b1 in the budget sweep | `D4b` |
| Depth | {1, 2, 3} | `draft_setup.DEPTHS` |
| H | 6-14 tasks | `draft_setup.H_RANGE` |
| eta_Q grid | {0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3543, 0.5} | `draft_setup.ETA_Q_GRID` |
| tau5 grid | {0, 0.1, 0.2, 0.3, 0.5, 0.7} | `draft_setup.TAU5_GRID` |
| Drift match | 1 (headline); sweep {0, 0.5, 1} | D6 |
| FQ cap | 10% | D26 |
| Margin | 15% | `PR` "Endpoint chinh" |
| Main grid | 13 systems x 34 columns (18 scripted + 16 BR) x 5 Delta x 3 detectors x 4 rho x 10 seeds | `tools/run_draft_eval.py` |
| BR | 13 systems x 5 Delta x 4 rho at mid = 260 records | `S:run.records_read` |
| Sweeps | eta (Sentinel, 8 values), match (B1 and Sentinel, 3 values), persistent drift (B1 and Sentinel), budget (B1 and Sentinel, 3 chi x 4 shares x Delta {2, 4, 8}), gate world (4 gate baselines); all at mid, held-out, Delta {4, 8} unless stated | `tools/run_draft_eval.py` |

### A.12 Integrity

| Fact | Value | Source |
|---|---|---|
| Gate 1 (integrity) | 710/710 | `PR` execution record, Task 11 |
| Gate 2 (validity) | 203/205, two known reds, both pre-dating v2 and both in the benign-corpus surface test, not in the v2 carrier model: (1) `test_some_epsilon_makes_the_payload_indistinguishable_at_every_delta` (pipeline `matched`, phase `screen`): a genuine failure of the payload-indistinguishability check, no eps in the grid {0, 0.2, 0.4, 0.7, 1.0} keeps the payload under the 0.56 surface-AUC ceiling at every Delta; (2) `test_one_split_cannot_decide_a_delta_of_the_certify_corpus`: a deliberate "unanimity trap" that fires because all 20 splits clear the ceiling at Delta in {0, 2}, i.e. the multi-split criterion buys nothing there (a recorded finding, not a code defect) | `PR` Task 11; repo `README.md` §3.5; `docs/preregistration/cong-v2.md` §4 |
| Gate 3 (power) | 15/15 | `PR` Task 11 |
| v2 selection tests | `test_v2_select`: 5 OK | `PR` Task 11 |
| v2 drift surface test | payload vs drift at the SAME recency (Delta = 2), AUC <= 0.56 required; median AUC 0.514 on 60 workflows and 0.473 on 120 (`FR` T3; `PR` Q8 prints 0.51 / 0.47) | `PR` Q8 |
| Freeze | `freeze: clean sha256:c789fa7362e0` at run start and at summary time; the eval tool refuses to run or summarise the eval split on anything but a clean freeze (D33) | `S:run.header_*` |
| One run | the eval split was simulated once (25/09, 16:00-16:29); the only earlier contact is the declared D30 smoke touch (E.1) | `eval-log.txt`; `PR` D30 |
| git | HEAD `5c99042`, `git_clean = true` | `S:run` |
| Records | 7 raw files pinned by sha256, lines, bytes; `shasum -a 256 -c eval-records.sha256` inside `spikes/v2` checks them | `spikes/v2/eval-records.sha256` |
| Inputs outside the freeze digest (`FR` M7) | `swebench_dataset.py`, `topics.py`, `prose_world.py`, `data/*.jsonl`, and `make_world` in `tools/select_mixture.py`; covered by `git_head`, `git_clean` and the two tool sha256 | `RP` §10 |
| The report | every number and interpretation in `RP` was checked against the JSON by an independent checking script (0 mismatches) | `check.py`, outside the repository |

---

## B. Results

**At a glance (the preregistered endpoint, B.2):** the 15% margin is met at rho_patch = 0, 0.25 and 0.5 (gain 49.20%, 49.15%, 43.03%; lower 98.75% bounds 40.80, 36.89, 23.82) and NOT at rho_patch = 1 (gain 8.79%, 98.75% CI [-27.32, 18.86]; absolute difference 0.0171 [-0.0390, 0.0372]). Both controls pass (B.1). Every sentence that states this must carry the conditions in C.1-C.3.

**The regime map as the data draw it** (each line points to its table; conditions in Section C):
- rho_patch (endpoint, B.2): allocation beats commit-time auditing where the commit review sees delegated patches weakly or not at all (rho_patch <= 0.5); at rho_patch = 1 the two cannot be told apart. Most of the variation comes from B1: V(B1) falls from 0.7981 to 0.1943 as rho_patch goes from 0 to 1, V(S) from 0.4054 to 0.1772.
- Delta (RQ1, B.6): at Delta = 0 Sentinel plays exactly B1 (gain 0, CI [0, 0] at every rho); the smallest Delta whose 95% CI of the difference is above 0 is 1 (rho 0, 0.25), 2 (rho 0.5), none (rho 1) - a reading rule of the report, POST HOC.
- Detector (RQ4, B.7): at rho <= 0.5 the gain is nearly flat across detectors (41.91-49.83%); the weak detector never gives the largest gain; at rho = 1 every CI contains 0.
- eta_Q (B.9): gain rises as eta_Q falls, paid for in FQ.
- Budget x chi (EXPLORATORY, B.12): at b1 chi has no effect (D4b); the effect appears only when the budget binds.

### B.1 Controls (D28), read before any Sentinel number

Paths: `S:controls.*`. Reference rho = 0.25 (`S:run.ref_rho`), detector mid, 7 held-out attackers.

| Control | Pre-declared condition | Measured | Path | Outcome |
|---|---|---|---|---|
| (+) Oracle (told the attacked carrier), Delta in {4, 8} | V(Oracle) <= 0.05 | V(Oracle) = 0.0054 (raw 0.00543) | `S:controls.v_oracle_headline` | pass (`positive_ok = true`) |
| (-) at Delta = 0 the sweep-only baselines do not beat B1 | V(B3), V(B4) >= V(B1) | V(B3) = 0.8592, V(B4) = 0.8592, V(B1) = 0.6444 | `S:controls.v_sweepers_delta0.*`, `S:controls.v_b1_delta0` | pass (`negative_ok = true`) |

- `S:controls.ok = true`. N in the JSON: 57 workflows / 16 repos / 6301 episodes (`S:controls.n_workflows|n_repos|n_episodes`).
- That N is the UNION of two cells: 3829 episodes at Delta in {4, 8} for the Oracle (`S:curve_rho."0.25".n_episodes`) + 2472 episodes at Delta = 0 for B1/B3/B4 (`S:by_rho."0.25".figure3_gain_by_delta."0".n_episodes`) = 6301. Print the per-cell N (57/16/3829 and 57/16/2472) beside each control.

### B.2 Primary endpoint: the curve over rho_patch (`S:curve_rho.<rho>`)

Cell: detector mid, Delta in {4, 8}, chi = 1.34, budget b1, transient drift, match 1, 7 held-out attackers. Two-sided CI at 98.75% (alpha = `S:curve_rho.<rho>.alpha` = 0.0125, Bonferroni 0.05/4, D25). `n_boot` = 10000. Gain = 100*(1 - V(S)/V(B1)); abs = V(B1) - V(S) (positive = Sentinel has less harm).

| rho | N wf/repo/ep | V(B1) `v_base` | V(S) `v_cand` | Gain % [98.75% CI] `gain [lo, hi]` | Abs diff [98.75% CI] `abs_diff [abs_lo, abs_hi]` | B1 harm events in worst column `base_events` | resamples with V(B1)=0 `n_zero_base` | `rel_reliable` | `meets_margin` |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [40.80, 54.92] | 0.3927 [0.3080, 0.4465] | 128 | 0 | true | true |
| 0.25 | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [36.89, 54.13] | 0.3517 [0.2302, 0.4194] | 115 | 0 | true | true |
| 0.5 | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [23.82, 47.10] | 0.2318 [0.1136, 0.2710] | 102 | 0 | true | true |
| 1 | 57/16/3829 | 0.1943 | 0.1772 | 8.79 [-27.32, 18.86] | 0.0171 [-0.0390, 0.0372] | 66 | 0 | true | false |

Margin rule (preregistration, 'Endpoint chinh'): the 15% margin is met at a rho iff the lower 98.75% bound of the gain >= 15 AND the gain is readable (D21). `meets_margin` in the JSON implements exactly `rel_reliable and lo >= 15`.

### B.3 Secondary line (D22): Sentinel against the best baseline in B1-B6 (`S:curve_rho_vs_best.<rho>`)

Best baseline chosen by V at the point estimate (ties by name) and re-chosen inside every resample, so the CI pays for the selection. CI 98.75%.

| rho | N wf/repo/ep | Best baseline `best_baseline` | V_best `v_best` | V(S) `v_cand` | V_best - V(S) [98.75% CI] `abs_diff [abs_lo, abs_hi]` |
|---|---|---|---|---|---|
| 0 | 57/16/3829 | B2 uniform random | 0.6754 | 0.4054 | 0.2700 [0.1656, 0.3579] |
| 0.25 | 57/16/3829 | B2 uniform random | 0.6754 | 0.3638 | 0.3116 [0.2106, 0.3692] |
| 0.5 | 57/16/3829 | B5 risk-score | 0.4920 | 0.3069 | 0.1851 [0.0493, 0.2566] |
| 1 | 57/16/3829 | B1 audit-at-commit | 0.1943 | 0.1772 | 0.0171 [-0.0390, 0.0372] |

FQ of those best baselines (from B.4): B2 = 14.37% (best at rho = 0, 0.25); B5 = 12.32% (best at rho = 0.5). Both above the 10% FQ cap Sentinel's tuning had to respect (D26); baselines were never held to it.

### B.4 Table 2, every rho, every system (`S:by_rho.<rho>.table2.<system>`)

Cell as B.2. Every row: N = 57 workflows / 16 repos / 3829 episodes (`n_workflows`, `n_repos`, `n_episodes`). Fields: V = `worst_case_harm`; V_BR = `v_br_crossfit` (= max over `v_br_by_delta."4"`, `v_br_by_delta."8"`); Expl = `exploitability` (= V_BR - V); FQ% = `false_quarantine_pct`; FQ items/ep = `false_removed_per_ep`; CC% = `clean_completion`; Delay = `detection_delay` (tasks); L_wc = `worst_case_L`. No CI exists in the summary for V of a single system, for V_BR, for Expl, or for L.

**rho_patch = 0**

| System | V | V_BR (Delta=4 / Delta=8) | Expl | FQ % | FQ items/ep | CC % | Delay | L_wc | N wf/repo/ep |
|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 0.7981 | 0.7928 (0.7488 / 0.7928) | -0.0053 | 0.00 | 0.00 | 89.43 | 5.51 | 1.1839 | 57/16/3829 |
| B2 uniform random | 0.6754 | 0.5848 (0.5643 / 0.5848) | -0.0906 | 14.37 | 4.08 | 97.17 | 2.45 | 3.4087 | 57/16/3829 |
| B3 audit-on-insertion | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 18.57 | 8.17 | 100.00 | 0.00 | 6.0967 | 57/16/3829 |
| B4 audit-on-retrieval | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 14.57 | 2.11 | 100.00 | 0.00 | 2.2664 | 57/16/3829 |
| B5 risk-score | 0.7769 | 0.7828 (0.6586 / 0.7828) | 0.0059 | 14.17 | 4.42 | 97.78 | 2.27 | 3.6528 | 57/16/3829 |
| B6 two-stage | 0.8658 | 0.8672 (0.8408 / 0.8672) | 0.0014 | 15.70 | 5.73 | 100.00 | 2.03 | 4.5380 | 57/16/3829 |
| Sentinel-A1 | 0.4054 | 0.3709 (0.3709 / 0.3598) | -0.0345 | 8.58 | 1.57 | 94.00 | 3.09 | 1.5592 | 57/16/3829 |
| A1 -randomization | 0.8471 | 0.8672 (0.8518 / 0.8672) | 0.0201 | 12.75 | 1.95 | 98.47 | 1.85 | 2.2689 | 57/16/3829 |
| A1 -alarm memory | 0.4054 | 0.3709 (0.3709 / 0.3598) | -0.0345 | 8.58 | 1.57 | 94.00 | 3.09 | 1.5592 | 57/16/3829 |
| A1 -transition uncertainty | 0.4460 | 0.3931 (0.3836 / 0.3931) | -0.0529 | 8.71 | 1.71 | 93.64 | 3.05 | 1.9261 | 57/16/3829 |
| A1 -benign-drift | 0.4054 | 0.3709 (0.3709 / 0.3598) | -0.0345 | 8.58 | 1.57 | 94.00 | 3.09 | 1.5592 | 57/16/3829 |
| A1 -regime estimate | 0.7981 | 0.7928 (0.7408 / 0.7928) | -0.0053 | 0.27 | 0.03 | 89.43 | 5.46 | 1.1839 | 57/16/3829 |
| Oracle (control) | 0.0054 | 0.0051 (0.0051 / 0.0000) | -0.0003 | 16.92 | 4.45 | 98.59 | 0.71 | 5.2067 | 57/16/3829 |

**rho_patch = 0.25**

| System | V | V_BR (Delta=4 / Delta=8) | Expl | FQ % | FQ items/ep | CC % | Delay | L_wc | N wf/repo/ep |
|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 0.7154 | 0.6560 (0.5921 / 0.6560) | -0.0594 | 0.00 | 0.00 | 89.42 | 5.46 | 1.1012 | 57/16/3829 |
| B2 uniform random | 0.6754 | 0.5848 (0.5813 / 0.5848) | -0.0906 | 14.37 | 4.08 | 97.17 | 2.46 | 3.4087 | 57/16/3829 |
| B3 audit-on-insertion | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 18.57 | 8.17 | 100.00 | 0.00 | 6.0967 | 57/16/3829 |
| B4 audit-on-retrieval | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 14.57 | 2.11 | 100.00 | 0.00 | 2.2664 | 57/16/3829 |
| B5 risk-score | 0.7769 | 0.7828 (0.6550 / 0.7828) | 0.0059 | 14.17 | 4.42 | 97.78 | 2.27 | 3.6528 | 57/16/3829 |
| B6 two-stage | 0.8658 | 0.8672 (0.8408 / 0.8672) | 0.0014 | 15.70 | 5.73 | 100.00 | 2.03 | 4.5380 | 57/16/3829 |
| Sentinel-A1 | 0.3638 | 0.3621 (0.3227 / 0.3621) | -0.0017 | 8.40 | 1.49 | 93.73 | 3.21 | 1.4796 | 57/16/3829 |
| A1 -randomization | 0.8471 | 0.8672 (0.8518 / 0.8672) | 0.0201 | 12.75 | 1.95 | 98.47 | 1.85 | 2.2689 | 57/16/3829 |
| A1 -alarm memory | 0.3638 | 0.3621 (0.3227 / 0.3621) | -0.0017 | 8.40 | 1.49 | 93.73 | 3.21 | 1.4796 | 57/16/3829 |
| A1 -transition uncertainty | 0.4085 | 0.3266 (0.3266 / 0.3118) | -0.0819 | 8.41 | 1.53 | 93.61 | 3.18 | 1.6506 | 57/16/3829 |
| A1 -benign-drift | 0.3638 | 0.3621 (0.3227 / 0.3621) | -0.0017 | 8.40 | 1.49 | 93.73 | 3.21 | 1.4796 | 57/16/3829 |
| A1 -regime estimate | 0.7154 | 0.6647 (0.5760 / 0.6647) | -0.0507 | 0.09 | 0.01 | 89.42 | 5.43 | 1.1012 | 57/16/3829 |
| Oracle (control) | 0.0054 | 0.0051 (0.0051 / 0.0000) | -0.0003 | 16.92 | 4.45 | 98.59 | 0.71 | 5.2067 | 57/16/3829 |

**rho_patch = 0.5**

| System | V | V_BR (Delta=4 / Delta=8) | Expl | FQ % | FQ items/ep | CC % | Delay | L_wc | N wf/repo/ep |
|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 0.5387 | 0.4839 (0.4439 / 0.4839) | -0.0548 | 0.00 | 0.00 | 89.42 | 5.44 | 0.9167 | 57/16/3829 |
| B2 uniform random | 0.6754 | 0.5879 (0.5879 / 0.5718) | -0.0875 | 14.37 | 4.08 | 97.17 | 2.46 | 3.4087 | 57/16/3829 |
| B3 audit-on-insertion | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 18.57 | 8.17 | 100.00 | 0.00 | 6.0967 | 57/16/3829 |
| B4 audit-on-retrieval | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 14.57 | 2.11 | 100.00 | 0.00 | 2.2664 | 57/16/3829 |
| B5 risk-score | 0.4920 | 0.5006 (0.4946 / 0.5006) | 0.0086 | 12.32 | 2.97 | 94.96 | 3.02 | 2.5950 | 57/16/3829 |
| B6 two-stage | 0.8658 | 0.8672 (0.8408 / 0.8672) | 0.0014 | 15.70 | 5.73 | 100.00 | 2.03 | 4.5380 | 57/16/3829 |
| Sentinel-A1 | 0.3069 | 0.2911 (0.2763 / 0.2911) | -0.0158 | 6.98 | 1.09 | 92.50 | 3.78 | 1.2286 | 57/16/3829 |
| A1 -randomization | 0.5387 | 0.4839 (0.4439 / 0.4839) | -0.0548 | 0.00 | 0.00 | 89.42 | 5.44 | 0.9167 | 57/16/3829 |
| A1 -alarm memory | 0.3069 | 0.2911 (0.2763 / 0.2911) | -0.0158 | 6.98 | 1.09 | 92.50 | 3.78 | 1.2286 | 57/16/3829 |
| A1 -transition uncertainty | 0.3285 | 0.3233 (0.2851 / 0.3233) | -0.0052 | 7.25 | 1.16 | 92.74 | 3.71 | 1.3552 | 57/16/3829 |
| A1 -benign-drift | 0.3069 | 0.2911 (0.2763 / 0.2911) | -0.0158 | 6.98 | 1.09 | 92.50 | 3.78 | 1.2286 | 57/16/3829 |
| A1 -regime estimate | 0.5387 | 0.4839 (0.4439 / 0.4839) | -0.0548 | 0.00 | 0.00 | 89.42 | 5.44 | 0.9167 | 57/16/3829 |
| Oracle (control) | 0.0054 | 0.0051 (0.0051 / 0.0000) | -0.0003 | 16.92 | 4.45 | 98.59 | 0.72 | 5.2067 | 57/16/3829 |

**rho_patch = 1**

| System | V | V_BR (Delta=4 / Delta=8) | Expl | FQ % | FQ items/ep | CC % | Delay | L_wc | N wf/repo/ep |
|---|---|---|---|---|---|---|---|---|---|
| B1 audit-at-commit | 0.1943 | 0.1175 (0.1175 / 0.1089) | -0.0768 | 0.00 | 0.00 | 89.42 | 5.43 | 0.5601 | 57/16/3829 |
| B2 uniform random | 0.6754 | 0.5879 (0.5879 / 0.5718) | -0.0875 | 14.37 | 4.08 | 97.17 | 2.48 | 3.4087 | 57/16/3829 |
| B3 audit-on-insertion | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 18.57 | 8.17 | 100.00 | 0.00 | 6.0967 | 57/16/3829 |
| B4 audit-on-retrieval | 0.8833 | 0.8672 (0.8408 / 0.8672) | -0.0161 | 14.57 | 2.11 | 100.00 | 0.00 | 2.2664 | 57/16/3829 |
| B5 risk-score | 0.4920 | 0.5109 (0.5107 / 0.5109) | 0.0189 | 12.32 | 2.97 | 94.96 | 3.03 | 2.5950 | 57/16/3829 |
| B6 two-stage | 0.8658 | 0.8672 (0.8408 / 0.8672) | 0.0014 | 15.70 | 5.73 | 100.00 | 2.03 | 4.5380 | 57/16/3829 |
| Sentinel-A1 | 0.1772 | 0.1477 (0.1389 / 0.1477) | -0.0295 | 0.36 | 0.05 | 91.34 | 4.80 | 0.4903 | 57/16/3829 |
| A1 -randomization | 0.1943 | 0.1175 (0.1175 / 0.1089) | -0.0768 | 0.00 | 0.00 | 89.42 | 5.43 | 0.5601 | 57/16/3829 |
| A1 -alarm memory | 0.1725 | 0.1477 (0.1389 / 0.1477) | -0.0248 | 0.38 | 0.05 | 91.34 | 4.80 | 0.4873 | 57/16/3829 |
| A1 -transition uncertainty | 0.1750 | 0.1503 (0.1161 / 0.1503) | -0.0247 | 0.47 | 0.06 | 91.45 | 4.65 | 0.4885 | 57/16/3829 |
| A1 -benign-drift | 0.1725 | 0.1420 (0.1389 / 0.1420) | -0.0305 | 1.56 | 0.22 | 91.34 | 4.69 | 0.5854 | 57/16/3829 |
| A1 -regime estimate | 0.1943 | 0.1175 (0.1175 / 0.1089) | -0.0768 | 0.00 | 0.00 | 89.42 | 5.43 | 0.5601 | 57/16/3829 |
| Oracle (control) | 0.0054 | 0.0051 (0.0051 / 0.0000) | -0.0003 | 16.92 | 4.45 | 98.59 | 0.72 | 5.2067 | 57/16/3829 |

### B.5 Table 3, five ablations, every rho (`S:by_rho.<rho>.table3_ablations.<arm>`)

Base = the ablation, candidate = Sentinel-A1. Diff = V(ablation) - V(S) (positive = removing the component raises worst-case harm). Gain = 100*(1 - V(S)/V(ablation)). CI 95% (`alpha` = 0.05), no multiplicity correction. N = 57/16/3829 in every row. FQ% and Expl of the arm come from `S:by_rho.<rho>.table2.<arm>`. The Note column is POST HOC (final review I1/I5; report sec. 4, 4.1).

| Arm | rho | V(arm) `v_base` | V(S) `v_cand` | Diff [95% CI] | Gain % [95% CI] | arm harm events `base_events` | FQ % (arm) | Expl (arm) | Note (POST HOC) |
|---|---|---|---|---|---|---|---|---|---|
| A1 -randomization | 0 | 0.8471 | 0.4054 | 0.4416 [0.3808, 0.5004] | 52.14 [46.58, 57.96] | 170 | 12.75 | 0.0201 |  |
| A1 -randomization | 0.25 | 0.8471 | 0.3638 | 0.4833 [0.4204, 0.5360] | 57.05 [51.80, 61.85] | 170 | 12.75 | 0.0201 |  |
| A1 -randomization | 0.5 | 0.5387 | 0.3069 | 0.2318 [0.1465, 0.2629] | 43.03 [30.06, 45.98] | 102 | 0.00 | -0.0548 | = B1 in every Table 2 column |
| A1 -randomization | 1 | 0.1943 | 0.1772 | 0.0171 [-0.0200, 0.0333] | 8.79 [-13.60, 16.70] | 66 | 0.00 | -0.0768 | = B1 in every Table 2 column |
| A1 -alarm memory | 0 | 0.4054 | 0.4054 | 0.0000 [0.0000, 0.0000] | 0.00 [0.00, 0.00] | 81 | 8.58 | -0.0345 | NOT EXERCISED: identical to Sentinel in every Table 2 column |
| A1 -alarm memory | 0.25 | 0.3638 | 0.3638 | 0.0000 [0.0000, 0.0000] | 0.00 [0.00, 0.00] | 73 | 8.40 | -0.0017 | NOT EXERCISED: identical to Sentinel in every Table 2 column |
| A1 -alarm memory | 0.5 | 0.3069 | 0.3069 | 0.0000 [0.0000, 0.0000] | 0.00 [0.00, 0.00] | 112 | 6.98 | -0.0158 | NOT EXERCISED: identical to Sentinel in every Table 2 column |
| A1 -alarm memory | 1 | 0.1725 | 0.1772 | -0.0047 [-0.0147, 0.0000] | -2.73 [-9.77, 0.00] | 60 | 0.38 | -0.0248 |  |
| A1 -transition uncertainty | 0 | 0.4460 | 0.4054 | 0.0406 [0.0025, 0.0714] | 9.09 [0.57, 15.36] | 90 | 8.71 | -0.0529 |  |
| A1 -transition uncertainty | 0.25 | 0.4085 | 0.3638 | 0.0448 [0.0062, 0.0639] | 10.96 [1.68, 14.53] | 82 | 8.41 | -0.0819 |  |
| A1 -transition uncertainty | 0.5 | 0.3285 | 0.3069 | 0.0216 [-0.0298, 0.0420] | 6.59 [-9.48, 11.94] | 118 | 7.25 | -0.0052 |  |
| A1 -transition uncertainty | 1 | 0.1750 | 0.1772 | -0.0022 [-0.0206, 0.0595] | -1.23 [-12.48, 27.79] | 37 | 0.47 | -0.0247 |  |
| A1 -benign-drift | 0 | 0.4054 | 0.4054 | 0.0000 [0.0000, 0.0000] | 0.00 [0.00, 0.00] | 81 | 8.58 | -0.0345 | NOT EXERCISED: identical to Sentinel in every Table 2 column |
| A1 -benign-drift | 0.25 | 0.3638 | 0.3638 | 0.0000 [0.0000, 0.0000] | 0.00 [0.00, 0.00] | 73 | 8.40 | -0.0017 | NOT EXERCISED: identical to Sentinel in every Table 2 column |
| A1 -benign-drift | 0.5 | 0.3069 | 0.3069 | 0.0000 [0.0000, 0.0000] | 0.00 [0.00, 0.00] | 112 | 6.98 | -0.0158 | NOT EXERCISED: identical to Sentinel in every Table 2 column |
| A1 -benign-drift | 1 | 0.1725 | 0.1772 | -0.0047 [-0.0147, 0.0000] | -2.73 [-9.77, 0.00] | 60 | 1.56 | -0.0305 |  |
| A1 -regime estimate | 0 | 0.7981 | 0.4054 | 0.3927 [0.3267, 0.4350] | 49.20 [42.87, 53.86] | 128 | 0.27 | -0.0053 | V = V(B1) exactly (other columns differ) |
| A1 -regime estimate | 0.25 | 0.7154 | 0.3638 | 0.3517 [0.2515, 0.4067] | 49.15 [39.97, 52.97] | 115 | 0.09 | -0.0507 | V = V(B1) exactly (other columns differ) |
| A1 -regime estimate | 0.5 | 0.5387 | 0.3069 | 0.2318 [0.1465, 0.2629] | 43.03 [30.06, 45.98] | 102 | 0.00 | -0.0548 | = B1 in every Table 2 column |
| A1 -regime estimate | 1 | 0.1943 | 0.1772 | 0.0171 [-0.0200, 0.0333] | 8.79 [-13.60, 16.70] | 66 | 0.00 | -0.0768 | = B1 in every Table 2 column |

### B.6 Gain by Delta, every rho (`S:by_rho.<rho>.figure3_gain_by_delta.<Delta>`)

Detector mid, 7 held-out attackers, one Delta at a time. CI 95%. At Delta = 8 only 34 workflows / 12 repos are feasible.

| rho | Delta | N wf/repo/ep | V(B1) | V(S) | Gain % [95% CI] | Abs diff [95% CI] | B1 events | `rel_reliable` |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 57/16/2472 | 0.7625 | 0.7625 | 0.00 [0.00, 0.00] | 0.0000 [0.0000, 0.0000] | 270 | true |
| 0 | 1 | 57/16/2478 | 0.7713 | 0.5754 | 25.40 [18.42, 29.18] | 0.1959 [0.1387, 0.2297] | 274 | true |
| 0 | 2 | 57/16/2481 | 0.7828 | 0.4928 | 37.05 [30.92, 39.85] | 0.2900 [0.2351, 0.3196] | 279 | true |
| 0 | 4 | 57/16/2486 | 0.7611 | 0.3716 | 51.18 [44.62, 53.97] | 0.3896 [0.3400, 0.4043] | 270 | true |
| 0 | 8 | 34/12/1343 | 0.7981 | 0.4054 | 49.20 [43.06, 56.20] | 0.3927 [0.3231, 0.4499] | 128 | true |
| 0.25 | 0 | 57/16/2472 | 0.6444 | 0.6444 | 0.00 [0.00, 0.00] | 0.0000 [0.0000, 0.0000] | 229 | true |
| 0.25 | 1 | 57/16/2478 | 0.6580 | 0.5988 | 9.00 [0.65, 16.48] | 0.0592 [0.0040, 0.1138] | 236 | true |
| 0.25 | 2 | 57/16/2481 | 0.6774 | 0.4606 | 32.01 [21.94, 33.83] | 0.2168 [0.1434, 0.2381] | 241 | true |
| 0.25 | 4 | 57/16/2486 | 0.6592 | 0.3543 | 46.25 [41.30, 49.94] | 0.3049 [0.2641, 0.3293] | 233 | true |
| 0.25 | 8 | 34/12/1343 | 0.7154 | 0.3638 | 49.15 [39.56, 55.66] | 0.3517 [0.2443, 0.4181] | 115 | true |
| 0.5 | 0 | 57/16/2472 | 0.4725 | 0.4725 | 0.00 [0.00, 0.00] | 0.0000 [0.0000, 0.0000] | 170 | true |
| 0.5 | 1 | 57/16/2478 | 0.5125 | 0.5354 | -4.46 [-16.01, 3.21] | -0.0229 [-0.0777, 0.0170] | 184 | true |
| 0.5 | 2 | 57/16/2481 | 0.5034 | 0.4320 | 14.20 [5.82, 22.13] | 0.0715 [0.0290, 0.1201] | 181 | true |
| 0.5 | 4 | 57/16/2486 | 0.4867 | 0.3069 | 36.94 [30.73, 42.04] | 0.1798 [0.1435, 0.2168] | 174 | true |
| 0.5 | 8 | 34/12/1343 | 0.5387 | 0.3018 | 43.98 [30.36, 47.37] | 0.2369 [0.1498, 0.2689] | 102 | true |
| 1 | 0 | 57/16/2472 | 0.1493 | 0.1493 | 0.00 [0.00, 0.00] | 0.0000 [0.0000, 0.0000] | 55 | true |
| 1 | 1 | 57/16/2478 | 0.1662 | 0.1662 | 0.00 [0.00, 0.00] | 0.0000 [0.0000, 0.0000] | 61 | true |
| 1 | 2 | 57/16/2481 | 0.1806 | 0.1806 | 0.00 [0.00, 0.00] | 0.0000 [0.0000, 0.0000] | 66 | true |
| 1 | 4 | 57/16/2486 | 0.1943 | 0.1772 | 8.79 [-8.89, 17.22] | 0.0171 [-0.0134, 0.0340] | 66 | true |
| 1 | 8 | 34/12/1343 | 0.1744 | 0.1465 | 15.99 [-41.43, 22.06] | 0.0279 [-0.0447, 0.0385] | 27 | true |

Crossover reading (the REPORT's rule, not in the preregistration; treat as POST HOC): the smallest Delta on the grid whose 95% CI of the abs diff lies entirely above 0.
- rho = 0: Delta = 1
- rho = 0.25: Delta = 1
- rho = 0.5: Delta = 2
- rho = 1: none on the grid

### B.7 Gain by detector, every rho (`S:by_rho.<rho>.rq4_detectors.<weak|mid|strong>`)

Delta in {4, 8}, 7 held-out attackers. CI 95%. The mid row is the endpoint cell at 95% (the same object as `transfer_*.heldout_attackers`).

| rho | Detector | N wf/repo/ep | V(B1) | V(S) | Gain % [95% CI] | Abs diff [95% CI] | B1 events |
|---|---|---|---|---|---|---|---|
| 0 | weak | 57/16/3829 | 0.7583 | 0.3862 | 49.07 [40.63, 52.86] | 0.3721 [0.2706, 0.4249] | 122 |
| 0 | mid | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] | 128 |
| 0 | strong | 57/16/3829 | 0.8181 | 0.4104 | 49.83 [44.63, 54.52] | 0.4077 [0.3577, 0.4505] | 131 |
| 0.25 | weak | 57/16/3829 | 0.6574 | 0.3598 | 45.26 [35.13, 48.86] | 0.2975 [0.2061, 0.3542] | 106 |
| 0.25 | mid | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] | 115 |
| 0.25 | strong | 57/16/3829 | 0.7473 | 0.3843 | 48.57 [40.57, 53.87] | 0.3630 [0.2730, 0.4190] | 120 |
| 0.5 | weak | 57/16/3829 | 0.5387 | 0.3129 | 41.91 [29.49, 45.91] | 0.2258 [0.1452, 0.2643] | 102 |
| 0.5 | mid | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] | 102 |
| 0.5 | strong | 57/16/3829 | 0.5387 | 0.3054 | 43.31 [30.91, 46.50] | 0.2333 [0.1516, 0.2677] | 102 |
| 1 | weak | 57/16/3829 | 0.2716 | 0.2607 | 4.05 [-34.85, 20.02] | 0.0110 [-0.0773, 0.0639] | 43 |
| 1 | mid | 57/16/3829 | 0.1943 | 0.1772 | 8.79 [-13.60, 16.70] | 0.0171 [-0.0200, 0.0333] | 66 |
| 1 | strong | 57/16/3829 | 0.1063 | 0.1224 | -15.15 [-91.38, 6.71] | -0.0161 [-0.0775, 0.0086] | 16 |

### B.8 Attacker transfer (RQ3), every rho

All three classes run on the same 57 eval workflows; tuning ran on django, so every row is already django -> 16-repo transfer (D8). CI 95%.
Paths: plan row = `S:by_rho.<rho>.transfer_dev_vs_heldout.dev_attackers`; D18 row = `S:by_rho.<rho>.transfer_tuning_vs_heldout.tuning_attackers`; held-out = `S:by_rho.<rho>.transfer_dev_vs_heldout.heldout_attackers` (identical object under `transfer_tuning_vs_heldout`).

| rho | Attacker class | N wf/repo/ep | V(B1) | V(S) | Gain % [95% CI] | Abs diff [95% CI] |
|---|---|---|---|---|---|---|
| 0 | 11 development attackers (plan row) | 57/16/6020 | 0.7776 | 0.4268 | 45.12 [37.64, 49.65] | 0.3509 [0.2845, 0.4168] |
| 0 | 6 D18 tuning columns | 57/16/3301 | 0.7776 | 0.4268 | 45.12 [37.67, 49.65] | 0.3509 [0.2847, 0.4168] |
| 0 | 7 held-out (endpoint) | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] |
| 0.25 | 11 development attackers (plan row) | 57/16/6020 | 0.6840 | 0.3897 | 43.03 [30.65, 48.89] | 0.2943 [0.1930, 0.3710] |
| 0.25 | 6 D18 tuning columns | 57/16/3301 | 0.6840 | 0.3897 | 43.03 [30.88, 49.49] | 0.2943 [0.1947, 0.3759] |
| 0.25 | 7 held-out (endpoint) | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] |
| 0.5 | 11 development attackers (plan row) | 57/16/6020 | 0.5264 | 0.3223 | 38.77 [23.80, 44.89] | 0.2041 [0.1144, 0.2647] |
| 0.5 | 6 D18 tuning columns | 57/16/3301 | 0.5264 | 0.3223 | 38.77 [23.80, 44.92] | 0.2041 [0.1144, 0.2647] |
| 0.5 | 7 held-out (endpoint) | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] |
| 1 | 11 development attackers (plan row) | 57/16/6020 | 0.1643 | 0.1547 | 5.82 [-34.82, 22.33] | 0.0096 [-0.0478, 0.0439] |
| 1 | 6 D18 tuning columns | 57/16/3301 | 0.1643 | 0.1547 | 5.82 [-34.82, 22.33] | 0.0096 [-0.0478, 0.0439] |
| 1 | 7 held-out (endpoint) | 57/16/3829 | 0.1943 | 0.1772 | 8.79 [-13.60, 16.70] | 0.0171 [-0.0200, 0.0333] |

Overlap note (`S:transfer_note`): 3 of the 11 development attackers can realise a held-out behaviour key (k, iota rule, eps): `memory-last-ingress-e0.6`, `uniform-last-ingress-e0.6`, `uniform-mid-write-e0.6`. So the plan row is not a clean transfer; the D18 row (6 tuning columns, no shared behaviour key) is. The two rows have identical point estimates at every rho (the worst development column lies inside the 6 tuning columns for both B1 and S); their CIs differ slightly because each resample re-maxes over a different column set.

### B.9 eta_Q sweep ('as quarantine becomes cheap') (`W:eta.<rho>.<eta>`)

Sentinel at every eta_Q of the grid, mixture held fixed; Delta in {4, 8}, mid, 7 held-out. B1 has no line 8, so the gain pairs the main-grid B1 records of the same cell with each eta (`W:eta.<rho>.<eta>.gain_ci`, `deltas` = [4, 8]). CI 95%. Tuned eta per rho = `T:rho.<rho>.eta_q` (marked *). The gain-vs-B1 per eta was computed by the pinned tool but is an analysis D33 does not list (final review M8; declared in the report sec. 5.5 and the execution record).

| rho | eta_Q | V(S) `worst_case_harm` | FQ % | FQ items/ep | CC % | Delay | V(B1) | Gain % [95% CI] | Abs diff [95% CI] | N wf/repo/ep |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0* | 0.4054 | 8.58 | 1.57 | 94.00 | 3.09 | 0.7981 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] | 57/16/3829 |
| 0 | 0.01 | 0.4054 | 3.02 | 0.58 | 94.00 | 3.14 | 0.7981 | 49.20 [42.91, 52.57] | 0.3927 [0.3279, 0.4271] | 57/16/3829 |
| 0 | 0.02 | 0.4054 | 2.62 | 0.50 | 94.00 | 3.15 | 0.7981 | 49.20 [42.88, 52.33] | 0.3927 [0.3270, 0.4262] | 57/16/3829 |
| 0 | 0.05 | 0.4054 | 2.01 | 0.39 | 94.00 | 3.22 | 0.7981 | 49.20 [42.65, 51.89] | 0.3927 [0.3243, 0.4225] | 57/16/3829 |
| 0 | 0.1 | 0.4054 | 1.22 | 0.24 | 94.01 | 3.34 | 0.7981 | 49.20 [42.52, 51.37] | 0.3927 [0.3237, 0.4167] | 57/16/3829 |
| 0 | 0.2 | 0.4175 | 0.83 | 0.16 | 94.01 | 3.43 | 0.7981 | 47.69 [41.10, 50.08] | 0.3806 [0.3149, 0.4083] | 57/16/3829 |
| 0 | 0.3543 | 0.4366 | 0.71 | 0.14 | 94.02 | 3.45 | 0.7981 | 45.30 [39.23, 48.96] | 0.3616 [0.3043, 0.3961] | 57/16/3829 |
| 0 | 0.5 | 0.4542 | 0.52 | 0.10 | 94.02 | 3.51 | 0.7981 | 43.10 [36.84, 47.78] | 0.3440 [0.2886, 0.3848] | 57/16/3829 |
| 0.25 | 0* | 0.3638 | 8.40 | 1.49 | 93.73 | 3.21 | 0.7154 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] | 57/16/3829 |
| 0.25 | 0.01 | 0.3643 | 3.00 | 0.56 | 93.74 | 3.27 | 0.7154 | 49.08 [39.82, 52.18] | 0.3511 [0.2531, 0.4015] | 57/16/3829 |
| 0.25 | 0.02 | 0.3665 | 2.61 | 0.48 | 93.74 | 3.28 | 0.7154 | 48.78 [39.52, 51.94] | 0.3490 [0.2496, 0.4006] | 57/16/3829 |
| 0.25 | 0.05 | 0.3712 | 2.00 | 0.37 | 93.74 | 3.35 | 0.7154 | 48.12 [39.03, 51.49] | 0.3443 [0.2451, 0.3963] | 57/16/3829 |
| 0.25 | 0.1 | 0.3842 | 1.21 | 0.23 | 93.74 | 3.46 | 0.7154 | 46.30 [38.34, 50.44] | 0.3312 [0.2430, 0.3865] | 57/16/3829 |
| 0.25 | 0.2 | 0.3924 | 0.82 | 0.15 | 93.75 | 3.56 | 0.7154 | 45.15 [37.34, 49.85] | 0.3230 [0.2381, 0.3808] | 57/16/3829 |
| 0.25 | 0.3543 | 0.4114 | 0.68 | 0.13 | 93.75 | 3.58 | 0.7154 | 42.49 [35.20, 48.27] | 0.3040 [0.2273, 0.3665] | 57/16/3829 |
| 0.25 | 0.5 | 0.4290 | 0.49 | 0.09 | 93.75 | 3.64 | 0.7154 | 40.03 [32.37, 47.03] | 0.2864 [0.2099, 0.3545] | 57/16/3829 |
| 0.5 | 0* | 0.3069 | 6.98 | 1.09 | 92.50 | 3.78 | 0.5387 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] | 57/16/3829 |
| 0.5 | 0.01 | 0.3094 | 2.56 | 0.41 | 92.50 | 3.81 | 0.5387 | 42.57 [29.97, 45.75] | 0.2293 [0.1464, 0.2618] | 57/16/3829 |
| 0.5 | 0.02 | 0.3116 | 2.24 | 0.36 | 92.50 | 3.83 | 0.5387 | 42.16 [29.67, 45.59] | 0.2271 [0.1444, 0.2611] | 57/16/3829 |
| 0.5 | 0.05 | 0.3163 | 1.72 | 0.28 | 92.50 | 3.88 | 0.5387 | 41.29 [28.97, 45.07] | 0.2224 [0.1409, 0.2580] | 57/16/3829 |
| 0.5 | 0.1 | 0.3188 | 1.04 | 0.17 | 92.51 | 3.97 | 0.5387 | 40.83 [28.68, 44.42] | 0.2199 [0.1390, 0.2541] | 57/16/3829 |
| 0.5 | 0.2 | 0.3210 | 0.73 | 0.12 | 92.51 | 4.04 | 0.5387 | 40.42 [27.91, 44.03] | 0.2177 [0.1354, 0.2530] | 57/16/3829 |
| 0.5 | 0.3543 | 0.3378 | 0.64 | 0.10 | 92.52 | 4.08 | 0.5387 | 37.29 [26.40, 42.49] | 0.2009 [0.1285, 0.2429] | 57/16/3829 |
| 0.5 | 0.5 | 0.3467 | 0.46 | 0.08 | 92.52 | 4.13 | 0.5387 | 35.63 [25.77, 41.14] | 0.1920 [0.1267, 0.2342] | 57/16/3829 |
| 1 | 0 | 0.1693 | 5.53 | 0.74 | 91.34 | 4.63 | 0.1943 | 12.83 [-12.76, 19.29] | 0.0249 [-0.0189, 0.0369] | 57/16/3829 |
| 1 | 0.01 | 0.1693 | 2.18 | 0.30 | 91.34 | 4.65 | 0.1943 | 12.83 [-12.76, 19.29] | 0.0249 [-0.0189, 0.0369] | 57/16/3829 |
| 1 | 0.02 | 0.1693 | 1.81 | 0.25 | 91.34 | 4.65 | 0.1943 | 12.83 [-12.76, 19.29] | 0.0249 [-0.0189, 0.0369] | 57/16/3829 |
| 1 | 0.05 | 0.1693 | 1.31 | 0.18 | 91.34 | 4.67 | 0.1943 | 12.83 [-12.76, 19.29] | 0.0249 [-0.0189, 0.0369] | 57/16/3829 |
| 1 | 0.1 | 0.1693 | 0.74 | 0.10 | 91.34 | 4.72 | 0.1943 | 12.83 [-12.76, 19.26] | 0.0249 [-0.0189, 0.0369] | 57/16/3829 |
| 1 | 0.2 | 0.1693 | 0.47 | 0.07 | 91.34 | 4.77 | 0.1943 | 12.83 [-12.76, 19.26] | 0.0249 [-0.0189, 0.0369] | 57/16/3829 |
| 1 | 0.3543* | 0.1772 | 0.36 | 0.05 | 91.34 | 4.80 | 0.1943 | 8.79 [-13.60, 16.70] | 0.0171 [-0.0200, 0.0333] | 57/16/3829 |
| 1 | 0.5 | 0.1772 | 0.23 | 0.03 | 91.34 | 4.83 | 0.1943 | 8.79 [-13.60, 16.65] | 0.0171 [-0.0200, 0.0333] | 57/16/3829 |

POST HOC, D30 sensitivity line (final review, optional readout): with the mixture held fixed, the LOWEST 95% lower bound of the gain over the whole eta grid:
- rho = 0: 36.84% (at eta_Q = 0.5; `min over e of W:eta."0".<e>.gain_ci.lo`)
- rho = 0.25: 32.37% (at eta_Q = 0.5; `min over e of W:eta."0.25".<e>.gain_ci.lo`)
- rho = 0.5: 25.77% (at eta_Q = 0.5; `min over e of W:eta."0.5".<e>.gain_ci.lo`)
- rho = 1: -13.60% (at eta_Q = 0.3543, 0.5; `min over e of W:eta."1".<e>.gain_ci.lo`)
These are 95% bounds, not the endpoint's 98.75% Bonferroni bounds.

At the tuned eta, the sweep reproduces Sentinel's main-grid V and FQ exactly at every rho (check: `W:eta.<rho>.<tuned>.worst_case_harm` == `S:by_rho.<rho>.table2.Sentinel-A1.worst_case_harm`).

### B.10 Drift-match sweep (`W:match.<rho>.<match>`)

World and defender change match together; headline match = 1 (Q8). Delta in {4, 8}, mid, 7 held-out. CI 95%. The summary holds harm/gain only, no FQ (final review M3).

| rho | match | N wf/repo/ep | V(B1) | V(S) | Gain % [95% CI] | Abs diff [95% CI] |
|---|---|---|---|---|---|---|
| 0 | 0.0 | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] |
| 0 | 0.5 | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] |
| 0 | 1.0 | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] |
| 0.25 | 0.0 | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] |
| 0.25 | 0.5 | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] |
| 0.25 | 1.0 | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] |
| 0.5 | 0.0 | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] |
| 0.5 | 0.5 | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] |
| 0.5 | 1.0 | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] |
| 1 | 0.0 | 57/16/3829 | 0.1943 | 0.1725 | 11.22 [-12.77, 17.72] | 0.0218 [-0.0191, 0.0347] |
| 1 | 0.5 | 57/16/3829 | 0.1943 | 0.1725 | 11.22 [-12.77, 17.72] | 0.0218 [-0.0191, 0.0347] |
| 1 | 1.0 | 57/16/3829 | 0.1943 | 0.1772 | 8.79 [-13.60, 16.70] | 0.0171 [-0.0200, 0.0333] |

### B.11 Persistent-drift sweep (`W:drift_visible.<rho>.persistent`)

Drift items anomalous for life instead of one task (Q8 sensitivity check). Headline (transient) row repeated at 95% from `S:by_rho.<rho>.rq4_detectors.mid`. CI 95%. No FQ in the summary (M3).

| rho | Drift | N wf/repo/ep | V(B1) | V(S) | Gain % [95% CI] | Abs diff [95% CI] |
|---|---|---|---|---|---|---|
| 0 | transient, 1 task (headline) | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] |
| 0 | persistent | 57/16/3829 | 0.7981 | 0.4054 | 49.20 [42.99, 53.91] | 0.3927 [0.3288, 0.4350] |
| 0.25 | transient, 1 task (headline) | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] |
| 0.25 | persistent | 57/16/3829 | 0.7154 | 0.3638 | 49.15 [40.28, 52.97] | 0.3517 [0.2564, 0.4067] |
| 0.5 | transient, 1 task (headline) | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] |
| 0.5 | persistent | 57/16/3829 | 0.5387 | 0.3069 | 43.03 [30.06, 45.98] | 0.2318 [0.1465, 0.2629] |
| 1 | transient, 1 task (headline) | 57/16/3829 | 0.1943 | 0.1772 | 8.79 [-13.60, 16.70] | 0.0171 [-0.0200, 0.0333] |
| 1 | persistent | 57/16/3829 | 0.1943 | 0.1740 | 10.41 [-12.86, 17.21] | 0.0202 [-0.0193, 0.0341] |

### B.12 Budget share x chi sweep: EXPLORATORY (D4b) (`W:budget_EXPLORATORY.<rho>."chi=<chi>"."share-<s>".<Delta>`)

EXPLORATORY: no preregistered test; Sentinel tuned at b1 is run at every share without re-tuning (M9); B1 is re-run at the same share and chi. Budget = share x b1. mid, 7 held-out, each Delta read alone, CI 95%. Two chi labels for the same grid point: the v2 label chi = 2*MAD/kbar (D2) and an alternative range/kbar formula (`chi_range` in the JSON). N per Delta: Delta=2 57/16/2481, Delta=4 57/16/2486, Delta=8 34/12/1343 in every row (asserted below). Every row has `rel_reliable = true`.

| rho | chi (2MAD/kbar) | range/kbar `chi_range` | share | Delta=2: gain % / abs [95% CI] / V(B1), V(S) | Delta=4: gain % / abs [95% CI] / V(B1), V(S) | Delta=8: gain % / abs [95% CI] / V(B1), V(S) |
|---|---|---|---|---|---|---|
| 0 | 0 | 0.0000 | 0.25 | 36.05 / 0.2822 [0.2244, 0.3042] / 0.7828, 0.5006 | 48.07 / 0.3659 [0.3086, 0.3842] / 0.7611, 0.3953 | 42.28 / 0.3374 [0.2916, 0.3816] / 0.7981, 0.4607 |
| 0 | 0 | 0.0000 | 0.5 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4043] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0 | 0 | 0.0000 | 0.75 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4043] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0 | 0 | 0.0000 | 1 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4043] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0 | 0.5 | 0.7889 | 0.25 | 35.47 / 0.2777 [0.2300, 0.3074] / 0.7828, 0.5051 | 49.73 / 0.3785 [0.3087, 0.3936] / 0.7611, 0.3826 | 40.88 / 0.3263 [0.2710, 0.3738] / 0.7981, 0.4718 |
| 0 | 0.5 | 0.7889 | 0.5 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4040] / 0.7611, 0.3716 | 48.37 / 0.3860 [0.3180, 0.4427] / 0.7981, 0.4121 |
| 0 | 0.5 | 0.7889 | 0.75 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4043] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0 | 0.5 | 0.7889 | 1 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4043] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0 | 1.34 | 2.1143 | 0.25 | 32.57 / 0.2599 [0.2107, 0.3027] / 0.7980, 0.5381 | 13.68 / 0.1058 [0.0532, 0.2086] / 0.7734, 0.6676 | 14.34 / 0.1178 [0.0695, 0.1886] / 0.8216, 0.7038 |
| 0 | 1.34 | 2.1143 | 0.5 | 37.05 / 0.2900 [0.2349, 0.3193] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3331, 0.4007] / 0.7611, 0.3716 | 42.28 / 0.3374 [0.2916, 0.3816] / 0.7981, 0.4607 |
| 0 | 1.34 | 2.1143 | 0.75 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4040] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0 | 1.34 | 2.1143 | 1 | 37.05 / 0.2900 [0.2351, 0.3196] / 0.7828, 0.4928 | 51.18 / 0.3896 [0.3400, 0.4043] / 0.7611, 0.3716 | 49.20 / 0.3927 [0.3231, 0.4499] / 0.7981, 0.4054 |
| 0.25 | 0 | 0.0000 | 0.25 | 28.06 / 0.1901 [0.1299, 0.2185] / 0.6774, 0.4873 | 44.07 / 0.2905 [0.2109, 0.3102] / 0.6592, 0.3687 | 39.72 / 0.2842 [0.1917, 0.3495] / 0.7154, 0.4313 |
| 0.25 | 0 | 0.0000 | 0.5 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2641, 0.3293] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 0 | 0.0000 | 0.75 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2641, 0.3293] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 0 | 0.0000 | 1 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2641, 0.3293] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 0.5 | 0.7889 | 0.25 | 31.09 / 0.2106 [0.1310, 0.2262] / 0.6774, 0.4668 | 45.65 / 0.3009 [0.2048, 0.3223] / 0.6592, 0.3583 | 38.17 / 0.2730 [0.1693, 0.3444] / 0.7154, 0.4424 |
| 0.25 | 0.5 | 0.7889 | 0.5 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2636, 0.3292] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 0.5 | 0.7889 | 0.75 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2641, 0.3293] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 0.5 | 0.7889 | 1 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2641, 0.3293] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 1.34 | 2.1143 | 0.25 | 27.76 / 0.1986 [0.1526, 0.2384] / 0.7154, 0.5168 | 4.61 / 0.0321 [0.0102, 0.1262] / 0.6968, 0.6647 | 7.46 / 0.0557 [-0.0033, 0.1361] / 0.7471, 0.6913 |
| 0.25 | 1.34 | 2.1143 | 0.5 | 32.01 / 0.2168 [0.1409, 0.2375] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2373, 0.3279] / 0.6592, 0.3543 | 40.65 / 0.2908 [0.1989, 0.3547] / 0.7154, 0.4246 |
| 0.25 | 1.34 | 2.1143 | 0.75 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2635, 0.3292] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.25 | 1.34 | 2.1143 | 1 | 32.01 / 0.2168 [0.1434, 0.2381] / 0.6774, 0.4606 | 46.25 / 0.3049 [0.2641, 0.3293] / 0.6592, 0.3543 | 49.15 / 0.3517 [0.2443, 0.4181] / 0.7154, 0.3638 |
| 0.5 | 0 | 0.0000 | 0.25 | 13.40 / 0.0675 [0.0245, 0.1082] / 0.5034, 0.4360 | 34.79 / 0.1693 [0.1211, 0.1966] / 0.4867, 0.3173 | 30.97 / 0.1669 [0.1111, 0.2210] / 0.5387, 0.3718 |
| 0.5 | 0 | 0.0000 | 0.5 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 0.5 | 0 | 0.0000 | 0.75 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 0.5 | 0 | 0.0000 | 1 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 0.5 | 0.5 | 0.7889 | 0.25 | 13.01 / 0.0655 [0.0237, 0.1101] / 0.5034, 0.4380 | 36.94 / 0.1798 [0.1171, 0.2092] / 0.4867, 0.3069 | 27.88 / 0.1502 [0.0959, 0.2073] / 0.5387, 0.3885 |
| 0.5 | 0.5 | 0.7889 | 0.5 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 0.5 | 0.5 | 0.7889 | 0.75 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 0.5 | 0.5 | 0.7889 | 1 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 0.5 | 1.34 | 2.1143 | 0.25 | 5.76 / 0.0352 [0.0166, 0.1214] / 0.6123, 0.5771 | 0.59 / 0.0041 [-0.0349, 0.0531] / 0.6968, 0.6927 | -0.80 / -0.0057 [-0.0549, 0.0794] / 0.7143, 0.7200 |
| 0.5 | 1.34 | 2.1143 | 0.5 | 14.20 / 0.0715 [0.0281, 0.1190] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1309, 0.2137] / 0.4867, 0.3069 | 31.86 / 0.1716 [0.1164, 0.2247] / 0.5387, 0.3671 |
| 0.5 | 1.34 | 2.1143 | 0.75 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1496, 0.2643] / 0.5387, 0.3018 |
| 0.5 | 1.34 | 2.1143 | 1 | 14.20 / 0.0715 [0.0290, 0.1201] / 0.5034, 0.4320 | 36.94 / 0.1798 [0.1435, 0.2168] / 0.4867, 0.3069 | 43.98 / 0.2369 [0.1498, 0.2689] / 0.5387, 0.3018 |
| 1 | 0 | 0.0000 | 0.25 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | -10.52 / -0.0204 [-0.0931, 0.0195] / 0.1943, 0.2147 | -35.97 / -0.0627 [-0.1350, 0.0029] / 0.1744, 0.2371 |
| 1 | 0 | 0.0000 | 0.5 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0134, 0.0340] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |
| 1 | 0 | 0.0000 | 0.75 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0134, 0.0340] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |
| 1 | 0 | 0.0000 | 1 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0134, 0.0340] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |
| 1 | 0.5 | 0.7889 | 0.25 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | -13.53 / -0.0263 [-0.0987, 0.0161] / 0.1943, 0.2205 | -45.53 / -0.0794 [-0.1090, -0.0151] / 0.1744, 0.2538 |
| 1 | 0.5 | 0.7889 | 0.5 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0161, 0.0338] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |
| 1 | 0.5 | 0.7889 | 0.75 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0134, 0.0340] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |
| 1 | 0.5 | 0.7889 | 1 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0134, 0.0340] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |
| 1 | 1.34 | 2.1143 | 0.25 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.4217, 0.4217 | -2.35 / -0.0164 [-0.0437, -0.0025] / 0.6968, 0.7132 | 0.64 / 0.0046 [-0.0267, 0.0322] / 0.7143, 0.7097 |
| 1 | 1.34 | 2.1143 | 0.5 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | -9.23 / -0.0179 [-0.0910, 0.0235] / 0.1943, 0.2122 | -29.42 / -0.0513 [-0.1307, 0.0130] / 0.1744, 0.2257 |
| 1 | 1.34 | 2.1143 | 0.75 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0168, 0.0336] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0588, 0.0368] / 0.1744, 0.1465 |
| 1 | 1.34 | 2.1143 | 1 | 0.00 / 0.0000 [0.0000, 0.0000] / 0.1806, 0.1806 | 8.79 / 0.0171 [-0.0134, 0.0340] / 0.1943, 0.1772 | 15.99 / 0.0279 [-0.0447, 0.0385] / 0.1744, 0.1465 |

Cells whose 95% CI of the abs diff lies entirely BELOW 0 (Sentinel more harm than B1), whole budget grid:
- rho = 1, chi=0.5, share-0.25, Delta = 8: abs -0.0794 [-0.1090, -0.0151], gain -45.53%
- rho = 1, chi=1.34, share-0.25, Delta = 4: abs -0.0164 [-0.0437, -0.0025], gain -2.35%

At share 1 (= b1) the three chi levels give identical entries (all fields but `chi_range`) at every rho and Delta: true (D4b).

### B.13 Verified only (`S:by_rho.<rho>.verified_only`)

Endpoint cell restricted to the SWE-bench Verified (Python) repos of the eval split. CI 95%.

| rho | N wf/repo/ep | V(B1) | V(S) | Gain % [95% CI] | Abs diff [95% CI] | B1 events | Same cell, all 16 repos, 95% (`rq4_detectors.mid`) |
|---|---|---|---|---|---|---|---|
| 0 | 42/7/2970 | 0.8114 | 0.4123 | 49.19 [44.91, 54.40] | 0.3991 [0.3569, 0.4307] | 116 | 49.20 / 0.3927 [0.3288, 0.4350] (57/16) |
| 0.25 | 42/7/2970 | 0.7523 | 0.3741 | 50.27 [44.37, 54.59] | 0.3782 [0.2965, 0.4098] | 107 | 49.15 / 0.3517 [0.2564, 0.4067] (57/16) |
| 0.5 | 42/7/2970 | 0.5680 | 0.3088 | 45.63 [34.42, 47.31] | 0.2592 [0.1875, 0.2771] | 89 | 43.03 / 0.2318 [0.1465, 0.2629] (57/16) |
| 1 | 42/7/2970 | 0.2071 | 0.1833 | 11.50 [-29.32, 18.54] | 0.0238 [-0.0434, 0.0389] | 54 | 8.79 / 0.0171 [-0.0200, 0.0333] (57/16) |

### B.14 Secondary world D29 (`S:gate_world.<rho>.<baseline>`)

The four audit kinds read as stage GATES over all carriers (the 24/09 reading). Only four fixed baselines run; Sentinel is not compared here. Delta in {4, 8}, mid, 7 held-out; fields `worst_case_harm`, `false_blocks_per_ep`. Pre-declared (D29, from pilot 1 on dev), at every rho and Delta in {4, 8}: B4g has V <= 0.05 and >= 2 false blocks per episode; B1g has V >= 0.1 when rho <= 0.5. No prediction for B2g, B3g.

| rho | Baseline | V | False blocks / ep | N wf/repo/ep | D29 prediction | Outcome |
|---|---|---|---|---|---|---|
| 0 | B1g commit | 0.7981 | 0.00 | 57/16/3829 | V >= 0.1 (rho <= 0.5) | holds |
| 0 | B2g uniform | 0.6238 | 2.70 | 57/16/3829 | none | - |
| 0 | B3g insertion | 0.8560 | 5.45 | 57/16/3829 | none | - |
| 0 | B4g retrieval | 0.0144 | 4.75 | 57/16/3829 | V <= 0.05 and >= 2 false blocks/ep | holds |
| 0.25 | B1g commit | 0.7154 | 0.00 | 57/16/3829 | V >= 0.1 (rho <= 0.5) | holds |
| 0.25 | B2g uniform | 0.5938 | 2.70 | 57/16/3829 | none | - |
| 0.25 | B3g insertion | 0.8560 | 5.45 | 57/16/3829 | none | - |
| 0.25 | B4g retrieval | 0.0144 | 4.75 | 57/16/3829 | V <= 0.05 and >= 2 false blocks/ep | holds |
| 0.5 | B1g commit | 0.5387 | 0.00 | 57/16/3829 | V >= 0.1 (rho <= 0.5) | holds |
| 0.5 | B2g uniform | 0.5589 | 2.70 | 57/16/3829 | none | - |
| 0.5 | B3g insertion | 0.8560 | 5.45 | 57/16/3829 | none | - |
| 0.5 | B4g retrieval | 0.0144 | 4.75 | 57/16/3829 | V <= 0.05 and >= 2 false blocks/ep | holds |
| 1 | B1g commit | 0.1943 | 0.00 | 57/16/3829 | none | - |
| 1 | B2g uniform | 0.4563 | 2.70 | 57/16/3829 | none | - |
| 1 | B3g insertion | 0.8560 | 5.45 | 57/16/3829 | none | - |
| 1 | B4g retrieval | 0.0144 | 4.75 | 57/16/3829 | V <= 0.05 and >= 2 false blocks/ep | holds |

V(B1g) equals V(B1) of the carrier world (B.4) to every digit at all four rho: true (commit-only audit is the same in both worlds).

### B.15 B7 on the small games, covering model (`G:*`, i.e. `spikes/v2/small-games.json`)

Algorithm 1 line 3 (exact solve) runs only on the small games; the carrier-world eval grid has no B7 row, so Table 2 has none. File generated 2026-09-25T15:50:19 at commit `fa6b4ef`; identical to v1's `spikes/small-games.json` except commit and timestamp (report sec. 9).

| Quantity | v2 value | Path |
|---|---|---|
| Small games solved exactly | 240 | `G:setup.n_games` |
| Library measured | 8 policies (the small-game model's library, NOT the 28-member carrier library) | `G:setup.library_size` |
| Covering radius rho of the library (mean TV over tasks) | 0.7500 | `G:rho_library_vs_optima` |
| Max regret over the 240 games | 0.3333 | `G:max_regret` |
| Mean regret | 0.0280 | `G:mean_regret` |
| Worst-covered game | H=4, K=4, Delta=3, m=4 | `G:worst_covered_game` |
| Double oracle: after adding 40 policies (ceiling 40) | rho = 0.5000, max regret 0.3333, mean regret 0.0219 | `G:double_oracle_curve[-1]` |
| Policies needed for rho <= 0.1 | not reached within the ceiling (`null`) | `G:policies_needed_for_target` |
| Proposition 6 bound | not computed in the file | - |

'rho' here is the library's COVERING RADIUS (TV distance from the optimum to the nearest member), not rho_patch.

### B.16 Loss L (D15), reported beside V, never tuned on (`S:by_rho.<rho>.table2.<system>.worst_case_L`)

L per episode = harm + lambda_Q * (benign items quarantined) + lambda_T * T_lost, lambda_Q = 0.54865 (`S:run.lambda_Q`), lambda_T = 0.5 (`S:run.lambda_T`); worst-case L = max over the same 14 held-out columns. No CI for L in the summary.

| rho | L(B1) | L(B2) | L(B3) | L(B4) | L(B5) | L(B6) | L(S) | L(S) - L(B1) | FQ items/ep S, B1 | FQ % S, B1 | V S, B1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.1839 | 3.4087 | 6.0967 | 2.2664 | 3.6528 | 4.5380 | 1.5592 | 0.3754 | 1.57, 0.00 | 8.58, 0.00 | 0.4054, 0.7981 |
| 0.25 | 1.1012 | 3.4087 | 6.0967 | 2.2664 | 3.6528 | 4.5380 | 1.4796 | 0.3784 | 1.49, 0.00 | 8.40, 0.00 | 0.3638, 0.7154 |
| 0.5 | 0.9167 | 3.4087 | 6.0967 | 2.2664 | 2.5950 | 4.5380 | 1.2286 | 0.3119 | 1.09, 0.00 | 6.98, 0.00 | 0.3069, 0.5387 |
| 1 | 0.5601 | 3.4087 | 6.0967 | 2.2664 | 2.5950 | 4.5380 | 0.4903 | -0.0698 | 0.05, 0.00 | 0.36, 0.00 | 0.1772, 0.1943 |

### B.17 POST HOC: which column decides V, and on what N

Source: one streamed read of the pinned `eval-main.jsonl` (sha256 matched `spikes/v2/eval-records.sha256`), headline cell only; no simulation (report sec. 2.2; numbers here from posthoc.json `cells.<rho>|<system>`). Recomputed V equals the summary's V to every digit in all 8 rows (asserted). Column = attacker@Delta; its N is the feasible workflows of that one column (the '57/16' printed elsewhere is the union over the 14 columns).

| rho | System | Deciding column | V | N of that column wf/repo/ep | Columns within 0.05 of the max / 14 | Runner-up column (value) |
|---|---|---|---|---|---|---|
| 0 | B1 audit-at-commit | `skill-last-write-e1.0@8` | 0.7981 | 26/10/160 | 4/14 | `queue-last-ingress-e0.6@8` (0.7776) |
| 0 | Sentinel-A1 | `branch-first-write-e0.6@8` | 0.4054 | 30/11/200 | 4/14 | `queue-last-ingress-e0.6@4` (0.3716) |
| 0.25 | B1 audit-at-commit | `skill-last-write-e1.0@8` | 0.7154 | 26/10/160 | 3/14 | `queue-last-ingress-e0.6@8` (0.6840) |
| 0.25 | Sentinel-A1 | `branch-first-write-e0.6@8` | 0.3638 | 30/11/200 | 3/14 | `queue-last-ingress-e0.6@4` (0.3543) |
| 0.5 | B1 audit-at-commit | `queue-mid-write-e0.6@8` | 0.5387 | 30/11/187 | 3/14 | `skill-last-write-e1.0@8` (0.5309) |
| 0.5 | Sentinel-A1 | `queue-last-ingress-e0.6@4` | 0.3069 | 57/16/355 | 7/14 | `queue-mid-write-e0.6@8` (0.3018) |
| 1 | B1 audit-at-commit | `skill-last-write-e1.0@4` | 0.1943 | 53/14/334 | 3/14 | `skill-last-write-e1.0@8` (0.1744) |
| 1 | Sentinel-A1 | `skill-last-write-e1.0@4` | 0.1772 | 53/14/334 | 4/14 | `skill-last-write-e1.0@8` (0.1465) |

Per-column feasible N of the 14 held-out columns (`S:denominators.sweeps.columns.<col>.used` = episodes; workflows from posthoc.json):

| Column | Delta=4: workflows / episodes | Delta=8: workflows / episodes |
|---|---|---|
| `branch-first-write-e0.6` | 57 / 356 | 30 / 200 |
| `memory-last-ingress-e0.3` | 57 / 356 | 34 / 207 |
| `memory-last-write-e0.6` | 57 / 355 | 30 / 188 |
| `memory-mid-write-e0.3` | 57 / 370 | 34 / 213 |
| `queue-last-ingress-e0.6` | 57 / 355 | 30 / 188 |
| `queue-mid-write-e0.6` | 57 / 360 | 30 / 187 |
| `skill-last-write-e1.0` | 53 / 334 | 26 / 160 |

### B.18 POST HOC: best-response bracket, cross-fit vs naive (`eval-br.jsonl`, read whole)

Max over Delta in {4, 8}, each estimator maximised separately. 'Cross-fit' = the Table 2 V_BR (biased LOW: placement chosen on <= 5 seeds per half among dozens). 'Naive' chooses and scores placements on the same seeds (biased HIGH). In expectation the true best-response value lies between. Numbers from posthoc.json `br.<rho>|<system>|<Delta>.{v_br, v_br_naive}` (report sec. 3, bracket table). The BR's own N: 57 workflows / 16 repos at Delta = 4 and 29 / 11 at Delta = 8, the same for every system (asserted).

| System | rho=0 cross-fit / naive | rho=0.25 | rho=0.5 | rho=1 |
|---|---|---|---|---|
| B1 audit-at-commit | 0.7928 / 0.8833 | 0.6560 / 0.7867 | 0.4839 / 0.6388 | 0.1175 / 0.2739 |
| B2 uniform random | 0.5848 / 0.7918 | 0.5848 / 0.7918 | 0.5879 / 0.7876 | 0.5879 / 0.7861 |
| B3 audit-on-insertion | 0.8672 / 0.9531 | 0.8672 / 0.9531 | 0.8672 / 0.9531 | 0.8672 / 0.9531 |
| B4 audit-on-retrieval | 0.8672 / 0.9531 | 0.8672 / 0.9531 | 0.8672 / 0.9531 | 0.8672 / 0.9531 |
| B5 risk-score | 0.7828 / 0.8617 | 0.7828 / 0.8582 | 0.5006 / 0.7374 | 0.5109 / 0.6956 |
| B6 two-stage | 0.8672 / 0.9531 | 0.8672 / 0.9531 | 0.8672 / 0.9531 | 0.8672 / 0.9531 |
| Sentinel-A1 | 0.3709 / 0.6070 | 0.3621 / 0.5697 | 0.2911 / 0.5045 | 0.1477 / 0.3120 |
| A1 -randomization | 0.8672 / 0.9404 | 0.8672 / 0.9404 | 0.4839 / 0.6388 | 0.1175 / 0.2739 |
| A1 -alarm memory | 0.3709 / 0.6070 | 0.3621 / 0.5697 | 0.2911 / 0.5045 | 0.1477 / 0.3120 |
| A1 -transition uncertainty | 0.3931 / 0.6103 | 0.3266 / 0.5781 | 0.3233 / 0.5128 | 0.1503 / 0.2977 |
| A1 -benign-drift | 0.3709 / 0.6070 | 0.3621 / 0.5697 | 0.2911 / 0.5045 | 0.1420 / 0.3120 |
| A1 -regime estimate | 0.7928 / 0.8779 | 0.6647 / 0.7867 | 0.4839 / 0.6388 | 0.1175 / 0.2739 |
| Oracle (control) | 0.0051 / 0.0084 | 0.0051 / 0.0084 | 0.0051 / 0.0084 | 0.0051 / 0.0084 |

Examples the final review quotes (Delta = 4 only): Sentinel rho=0: naive 0.6070 vs cross-fit 0.3709; B1 rho=1: naive 0.2739 vs cross-fit 0.1175.

BR menu size (`S:denominators.br.<Delta>`, (workflow, placement, seed) triples tried -> kept after the N4 survival filter):
- Delta = 0: 21760 -> 13412
- Delta = 1: 16760 -> 10420
- Delta = 2: 13840 -> 8632
- Delta = 4: 9160 -> 5772
- Delta = 8: 2800 -> 1804

### B.19 Tuned values and the mixtures Sentinel plays (`T:rho.<rho>`, i.e. `reference/v2_tuned.json`)

| rho | tau5 (B5) `tau5` | eta_Q `eta_q` | mid Delta=0 `mix."mid\|0".robust` | mid Delta=4 `mix."mid\|4".robust` | mid Delta=8 `mix."mid\|8".robust` | mid 'all' (used by -regime estimate) | pure Delta=4 / Delta=8 (used by -randomization) |
|---|---|---|---|---|---|---|---|
| 0 | 0.1 | 0 | `L-BT-0.5-f0` 1.0000 | `L-BT-0.5-f0` 0.4853; `L-RO-c4-p1-d3` 0.5147 | `L-BT-0.5-f0` 0.3483; `L-RO-c4-p2-d3` 0.1582; `L-SW-nomemory` 0.4935 | `L-BT-0.5-f0` 0.9924; `L-SW-commit3` 0.0076 | `L-SW-nomemory` / `L-SW-nomemory` |
| 0.25 | 0.1 | 0 | `L-BT-0.5-f0` 1.0000 | `L-BT-0.5-f0` 0.5179; `L-RO-c4-p1-d3` 0.4821 | `L-BT-0.5-f0` 0.4050; `L-RO-c4-p2-d3` 0.1440; `L-SW-nomemory` 0.4511 | `L-BT-0.5-f0` 0.9928; `L-SW-nomemory` 0.0064; `L-SW-queue` 0.0007 | `L-SW-nomemory` / `L-SW-nomemory` |
| 0.5 | 0 | 0 | `L-BT-0.5-f0` 1.0000 | `L-BT-0.5-f0` 0.6398; `L-RO-c4-p1-d3` 0.3602 | `L-BT-0.5-f0` 0.5330; `L-RO-c4-p2-d3` 0.1117; `L-SW-nomemory` 0.3553 | `L-BT-0.5-f0` 1.0000 | `L-BT-0.5-f0` / `L-BT-0.5-f0` |
| 1 | 0 | 0.3543 | `L-BT-0.5-f0` 1.0000 | `L-BT-0.5-f0` 0.8602; `L-RO-c3-p1-d3` 0.1094; `L-SW-queue` 0.0304 | `L-BT-0.5-f0` 0.7652; `L-RO-c4-p2-d3` 0.2348 | `L-BT-0.5-f0` 1.0000 | `L-BT-0.5-f0` / `L-BT-0.5-f0` |

beta-hat (`T:betas`): branch 0.0141, memory 0.3058, queue 0.0326, skill 0.0654; world beta: memory 0.314, skill 0.058, queue 0.033, branch 0 (`draft_setup.BETA_WORLD`).
Tuned cells: 72 (4 rho x 3 detectors x 6 regimes: Delta in {0,1,2,4,8} + 'all'); `cap_ok` true in all: true.
Weight of `L-BT-0.5-f0` (a behavioural copy of B1, see C) in the 8 headline mixtures (mid, Delta 4 and 8, 4 rho): min 0.3483, max 0.8602.
Its weight in mid Delta=0 and mid 'all': min 0.9924, max 1.0000.
Over all 72 robust mixtures its weight ranges from 0.0000 (rho = 0, `strong|1`) to 1.0000; so 'it carries 35-100% of every tuned mixture' (final review I1) is NOT true of all 72 cells; it is true of the headline cells (0.35-0.86) and of Delta=0/'all' at mid.
Robust mixtures with any weight on a tau = 0.3 BT member: 0. Nominal mixtures (used only by '-transition uncertainty'): rho 1 `weak|8` `L-BT-0.3-f0` 0.0110; rho 1 `weak|8` `L-BT-0.3-f1` 0.1493.

### B.20 Run block and record counts (`S:run.*`)

| Field | Value | Path |
|---|---|---|
| split | `"eval"` | `S:run.split` |
| seeds | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` | `S:run.seeds` |
| deltas | `[0, 1, 2, 4, 8]` | `S:run.deltas` |
| rhos | `[0.0, 0.25, 0.5, 1.0]` | `S:run.rhos` |
| header_start | `"freeze: clean sha256:c789fa7362e0"` | `S:run.header_start` |
| header_summary | `"freeze: clean sha256:c789fa7362e0"` | `S:run.header_summary` |
| git_head | `"5c99042"` | `S:run.git_head` |
| git_clean | `true` | `S:run.git_clean` |
| git_dirty | `[]` | `S:run.git_dirty` |
| ref_rho | `0.25` | `S:run.ref_rho` |
| headline_rho | `null` | `S:run.headline_rho` |
| family_alpha | `0.0125` | `S:run.family_alpha` |
| n_boot | `10000` | `S:run.n_boot` |
| lambda_Q | `0.54865` | `S:run.lambda_Q` |
| lambda_T | `0.5` | `S:run.lambda_T` |
| rho_mid_only | `false` | `S:run.rho_mid_only` |
| skip_br | `false` | `S:run.skip_br` |
| skip_sweeps | `false` | `S:run.skip_sweeps` |
| summarise_only | `false` | `S:run.summarise_only` |
| records_read eval-main.jsonl | 8501064 (kept 4512456) | `S:run.records_read."eval-main.jsonl"` |
| records_read eval-br.jsonl | 260 (kept 260) | `S:run.records_read."eval-br.jsonl"` |
| records_read sweep-eta.jsonl | 122528 (kept 122528) | `S:run.records_read."sweep-eta.jsonl"` |
| records_read sweep-match.jsonl | 91896 (kept 91896) | `S:run.records_read."sweep-match.jsonl"` |
| records_read sweep-persistent-drift.jsonl | 30632 (kept 30632) | `S:run.records_read."sweep-persistent-drift.jsonl"` |
| records_read sweep-budget-EXPLORATORY.jsonl | 605760 (kept 605760) | `S:run.records_read."sweep-budget-EXPLORATORY.jsonl"` |
| records_read eval-gate-world.jsonl | 61264 (kept 61264) | `S:run.records_read."eval-gate-world.jsonl"` |
| sha256 tools/run_draft_eval.py | `388510aceecaa516f9fd3e5dc50b2c886036c82e3efc7fa8769d85f5bc7e9bf8` | `S:run.sha256."tools/run_draft_eval.py"` |
| sha256 tools/select_mixture.py | `3fa56fd720420c924d32b325e0e62ead0a7718ebf218d23eb52ecc3199141221` | `S:run.sha256."tools/select_mixture.py"` |

Main-grid denominators (`S:denominators.main.total`, over the 90 summarised (attacker, Delta) columns x 57 workflows x 10 seeds): pairs 51300, infeasible 4870, non-surviving (N4) 17504, used 28926. Held-out headline cell (`S:denominators.sweeps.total`): pairs 7980, infeasible 1890, non-surviving 2261, used 3829. Reasons (`S:denominators.reasons`): infeasible = attacker rule has no placement at this Delta and H; non-surviving = N4, the task at sigma is not solved in the clean run.

Global checks: 268 gain entries in the two summaries; `rel_reliable = true` in all: true; `n_boot` values present: [10000].

### B.21 Preregistered predictions P1-P6 (`PR` "Du doan khai truoc"; outcomes from `RP` §7)

| # | Prediction (translated from `PR`) | Observed | Outcome | Mechanism note |
|---|---|---|---|---|
| P1 | Both D28 controls pass. | `S:controls.ok = true`; V(Oracle) = 0.0054; at Delta = 0, V(B3) = V(B4) = 0.8592 >= V(B1) = 0.6444 | holds | - |
| P2 | At Delta = 0, Sentinel ~ B1: the Delta = 0 regime mixture is commit. | gain 0.00 with CI [0.00, 0.00] and difference 0.0000 at all four rho (`S:by_rho.<rho>.figure3_gain_by_delta."0"`) | outcome holds | Not literally: the Delta = 0 mixture is `L-BT-0.5-f0` with weight 1 at every rho and every detector (`T:rho.<rho>.mix."<det>\|0".robust`), not `L-SW-commit`. POST HOC: `L-BT-0.5-f0` is a copy of B1 (B.22); at mid, `d32-effect.txt` records 10 members tied at the worst case in the Delta = 0 cell, all with FQ 0.00, at all four rho. |
| P3 | Gain vs B1 falls as rho rises, since B1 is weakest against delegated patches; at rho = 1 the gain may be ~0 or negative. | 49.20 -> 49.15 -> 43.03 -> 8.79%; at rho = 1, 98.75% CI [-27.32, 18.86], difference 0.0171 [-0.0390, 0.0372] | holds | The first step is nearly flat (49.20 vs 49.15). V(B1) falls from 0.7981 to 0.1943, consistent with the stated mechanism. |
| P4 | "A1 -regime estimate" ~ B1: the mixture pooled over every Delta collapses to commit. | V(-regime estimate) = V(B1) at all four rho: 0.7981 / 0.7154 / 0.5387 / 0.1943; at rho >= 0.5 every Table 2 column equals B1's | outcome holds | Not literally: the "all" mixture at mid is `L-BT-0.5-f0` 0.9924 / 0.9928 at rho <= 0.25 (the rest SW members) and 1 at rho >= 0.5. POST HOC: `L-BT-0.5-f0` is a B1 copy, so the outcome holds by construction. |
| P5 | Under the cross-fitted best response, "A1 -randomization" has a larger V_BR than Sentinel. | V_BR(-randomization) = 0.8672 / 0.8672 / 0.4839 / 0.1175; V_BR(S) = 0.3709 / 0.3621 / 0.2911 / 0.1477 | holds at rho <= 0.5; fails at rho = 1 | At rho >= 0.5 the arm equals B1 in every Table 2 column, so (POST HOC) P5 at rho = 0.5 compares Sentinel with B1. V_BR has no CI and is a lower bound, so this compares point estimates; (POST HOC) the ordering is the same under the naive estimator (B.18). |
| P6 | The secondary world behaves as D29 predicts. | B.14 | holds at every rho | - |

Also pre-declared (not a P-line): `PR` D4c expected V(B1) at rho = 1 to be decided by the skill/queue columns, about 0.85 x (1 - psi_1) ~ 0.13 at mid (pilot 1 on dev: 0.158). Measured: 0.1943, decided by `skill-last-write-e1.0@4` (B.17).

### B.22 POST HOC: the belief-threshold lock-in (code and synthetic probes only; no eval record)

Source: `RP` §4.1 and §10 item 11; `PR` execution record (25/09, I1 entry); code `carrier_policies.BeliefThreshold`, `belief_v2.DriftBelief`. Re-run for this file: an independent code-only check (`bt_check2.py`) and synthetic probe (`bt_probe.py`: 60 synthetic workflows x 3 seeds, detector mid, rho_patch 0.25), both outside the repository; no dev or eval record is touched.

- **tau >= 0.5 (9 members) always commit.** Under commit-only play p_attack stays at its 0.5 prior, because a commit gives no carrier evidence (D17); BT commits while p_attack <= tau. Probe: each of the 9 played only commit (180 episodes each, min p_attack 0.5000); every EpisodeResult of these 9 and of `L-SW-commit` equals B1's (0 differing episodes).
- **tau = 0.3 (3 members) never commit.** About half of the prior attack mass sits on windows no sweep can ever inform (Delta = 0 windows are never active; the branch carrier is never swept): 51.47% of windows at H = 6 down to 44.09% at H = 14. That mass keeps a fixed ratio to NULL, so p_attack cannot fall below 0.3398 (H = 6) to 0.3060 (H = 14), above tau = 0.3. Probe: 540 episodes (3 members x 180), only sweep actions, lowest p_attack 0.4069.
- **Library:** 10 of 28 members play B1 (9 BT with tau >= 0.5, plus `L-SW-commit`), so there are at most 19 distinct behaviours. `L-BT-0.5-f0` is the first of the 10 clones in sorted name order; `d32-effect.txt` records the 10-way tie at the worst case (FQ 0.00 for all 10) that the name order breaks. It carries 0.3483-0.8602 of the weight in the 8 headline mixtures and 0.9924-1 at mid Delta = 0 and "all" (B.19).
- **Line 7 never drives allocation:** no robust mixture in the 72 tuned cells puts weight on a tau = 0.3 member, the only members whose action reads the belief. One NOMINAL mixture (rho = 1, weak, Delta = 8; used only by "-transition uncertainty") has `L-BT-0.3-f0` 0.0110 and `L-BT-0.3-f1` 0.1493.
- **Line 8 at rho <= 0.5:** eta_Q = 0, so a firing item is quarantined whenever p_k > 0; no decision there depends on the belief or on beta-hat. Hence "-alarm memory" and "-benign-drift" are NOT EXERCISED at rho <= 0.5, and the match and persistent-drift sweeps cannot move harm there.
- **At rho = 1** (eta_Q = 0.3543) line 8 compares a posterior with a positive threshold, so the belief acts through line 8 and both arms are exercised: V 0.1725 for both vs 0.1772 for Sentinel (difference -0.0047 [-0.0147, 0.0000]); FQ 0.38% (-alarm memory) and 1.56% (-benign-drift) vs 0.36%; worst-case L 0.4873 and 0.5854 vs 0.4903; V_BR 0.1477 and 0.1420 vs 0.1477 (`S:by_rho."1".table2`, `S:by_rho."1".table3_ablations`).
- **Where the defect sits:** D17 follows §4 of the reproduced model; the plan set the tau grid without checking the range the switching statistic can reach, and the only BT test sets the posterior by hand (`tests/gate1_integrity/test_v2_policies.py`). Repairing the library needs re-tuning and a new eval, i.e. a new study; the eval split is no longer fresh.

---

## C. Claim boundaries

Derived from `FR` I1-I5 and `RP` §2.1, §2.2, §4.1, §7, §8, §10. For each: what the data say, what the paper MAY and MUST NOT claim, and one recommended sentence (edit freely, keep the content). In the paper, point these at `RP` and `PR` (the final review is not in the package).

### C.1 No credit for belief or drift modelling (`FR` I1; `RP` §4.1, §10 items 11-12)
- Data: B.22; the two arms are NOT EXERCISED at rho <= 0.5 (B.5, difference 0.0000 [0.0000, 0.0000]); eta_Q = 0 there; the drift sweeps are identical to the headline at rho <= 0.5 (B.10, B.11) because they cannot move harm.
- MAY: POST HOC mechanism: per workflow, Sentinel randomizes between a schedule identical to B1 (`L-BT-0.5-f0`) and RO/SW sweep schedules that read no evidence; the gain comes from that mixing.
- MUST NOT: attribute any part of the gain to the belief state, alarm memory or benign-drift modelling; read a 0.0000 [0.0000, 0.0000] row as "no effect"; cite the match or persistent-drift sweeps as evidence of robustness to drift at rho <= 0.5; say line 7 steers allocation.
- Wording (LaTeX-ready): No audit decision in this configuration reads the belief: every belief-threshold member of the library is locked into always or never committing, and at $\rhoP \le 0.5$ the tuned quarantine threshold is $\etaQ = 0$, so the alarm-memory and benign-drift ablations were not exercised there and we credit none of the gain to belief or drift modelling.

### C.2 The gain rests on the line-1 regime oracle (`FR` I2; `RP` §2.1)
- Data: "A1 -regime estimate" has V exactly equal to V(B1) at all four rho (0.7981 / 0.7154 / 0.5387 / 0.1943) and equals B1 in every Table 2 column at rho >= 0.5 (B.5); Sentinel is given the cell's Delta (D9b).
- MUST NOT: present Sentinel as estimating the regime, or the gain as available without knowing Delta.
- Wording (LaTeX-ready): \Sent{} is told each cell's trigger delay \Dl{} (a perfect regime estimator, declared before the run); without it, the ``$-$regime estimate'' ablation has exactly B1's worst-case harm at every \rhoP{}, so the whole gain is conditional on knowing \Dl{}.

### C.3 The gain costs false quarantines and worst-case L (`FR` I2; `RP` §2.1, §8)
- Data (B.4, B.16): FQ(S) = 8.58 / 8.40 / 6.98 / 0.36% vs FQ(B1) = 0.00 at every rho; S removes 1.57 / 1.49 / 1.09 / 0.05 benign items per episode, B1 none. Worst-case L(S) - L(B1) = +0.3754 / +0.3784 / +0.3119 / -0.0698: at rho <= 0.5, B1 has the lowest worst-case L among B1-B6 and S, S the second; at rho = 1, S has the lowest among B1-B6 and S (0.4903 vs B1's 0.5601; two ablation arms are lower still, B.4). No CI for L. The D22 best baselines exceed the 10% FQ cap Sentinel was held to (B2 14.37%, B5 12.32%). FQ(B1) = 0 by construction.
- MUST NOT: call the gain free; claim Sentinel is best on L at rho <= 0.5; present differences in L as significant.
- Wording (LaTeX-ready): The harm reduction is paid for in false quarantines: \Sent{} removes 1.1--1.6 benign items per episode ($\FQ = 6.98$--$8.58\%$) where B1, by construction, removes none, and on the declared loss \Loss{} its worst case exceeds B1's at every \rhoP{} where the margin is met ($1.5592$ against $1.1839$ at $\rhoP = 0$; the summaries carry no interval for \Loss{}).

### C.4 V_BR is a lower bound; the sign of exploitability is not read (`FR` I3; `RP` §3)
- Data: the cross-fit V_BR is biased low (placement chosen on at most 5 seeds per half among dozens); V is biased high (max of 14 noisy columns). They are not computed on the same things: the BR menu fixes eps = 0.6, while the held-out class has eps in {0.3, 1.0} too and V(B1) is decided by `skill-last-write-e1.0` (eps = 1.0) at rho = 0, 0.25 and 1; the BR at Delta = 8 averages 29 workflows / 11 repos, the held-out Delta = 8 columns 26-34 workflows. Exploitability is negative for B1-B4, Sentinel and the Oracle at all four rho (small and positive for B5, B6). POST HOC bracket (B.18): Sentinel at rho = 0: 0.3709 (cross-fit) to 0.6070 (naive); B1 at rho = 1: 0.1175 to 0.2739.
- MUST NOT: read a negative exploitability as "hard to exploit"; give V_BR a CI (none exists).
- Wording (LaTeX-ready): We report \VBR{} as a cross-fitted lower bound on the best-response value (bracketed post hoc by the in-sample estimate, which is biased upward), and we do not interpret the sign of $\Expl = \VBR - \Vwc$, which compares a downward-biased estimate on $\varepsilon = 0.6$ placements with an upward-biased maximum over held-out columns that include $\varepsilon \in \{0.3, 1.0\}$.

### C.5 Which columns decide V, and on what N (`FR` I4; `RP` §2.2) - POST HOC
- Data (B.17): V is a max over 14 (attacker, Delta) columns; the N = 57/16/3829 printed on every row is their union. At rho <= 0.25: V(B1) is decided by `skill-last-write-e1.0@8` (26 workflows / 10 repos / 160 episodes), V(S) by `branch-first-write-e0.6@8` (30 / 11 / 200). At rho = 0.5: B1 by `queue-mid-write-e0.6@8` (30 / 11 / 187), S by `queue-last-ingress-e0.6@4` (57 / 16 / 355). At rho = 1 both by `skill-last-write-e1.0@4` (53 / 14 / 334). Columns within 0.05 of the max: B1 4/3/3/3, S 4/3/7/4, so the max bias does not favour Sentinel.
- MAY: say Sentinel's worst case at rho <= 0.25 is an attack on the branch carrier, which only a commit audit can catch (branch is never swept).
- MUST NOT: describe V as "max over attackers" with N = 57 as if every column had 57 workflows.
- Wording (LaTeX-ready): \Vwc{} is a maximum over 14 (attacker, \Dl) columns, and at $\rhoP \le 0.25$ it is decided, for both B1 and \Sent{}, by a $\Dl = 8$ column with only 26--30 feasible workflows from 10--11 repositories; \Sent{}'s worst case there is an attack on the branch carrier, which only a commit audit can catch (post hoc).

### C.6 "-randomization" and "-transition uncertainty" do not test what their names say (`FR` I5; `RP` §4)
- Data: "-randomization" plays the tuned `pure` member with member seed 0, one schedule for every workflow; that member was chosen on dev while randomized per workflow. At rho <= 0.25 it is `L-SW-nomemory` frozen, worse than B1 (0.8471 vs 0.7981 at rho = 0); at rho >= 0.5 it is `L-BT-0.5-f0`, i.e. B1, so P5 at rho = 0.5 compares Sentinel with B1. "-transition uncertainty": the eval world is always the nominal kernel (`tools/run_draft_eval.py` calls `make_world(..., "nominal", ...)`), so it compares the robust mixture with the nominal-kernel mixture ON the nominal kernel.
- MUST NOT: call "-randomization" the best deterministic policy or read its gap as "the value of randomization"; call "-transition uncertainty" a robustness test.
- Wording (LaTeX-ready): Two ablations are narrower than their names: ``$-$randomization'' freezes the tuned pure member into one schedule for every workflow (at $\rhoP \ge 0.5$ that member is a copy of B1), so it is not the best deterministic policy, and ``$-$transition uncertainty'' replaces the robust mixture by the nominal-kernel one but is evaluated only under the nominal kernel, so it does not measure robustness to a misspecified kernel.

### C.7 rho_patch = 1 is not significant (`RP` §2, §5.1)
- Data: gain 8.79%, 98.75% CI [-27.32, 18.86]; difference 0.0171 [-0.0390, 0.0372]; `meets_margin = false`; the best baseline at rho = 1 is B1 itself. Every 95% CI of the difference at rho = 1 contains 0: detectors (strong: -15.15% [-91.38, 6.71]), transfer rows, Verified-only, match, persistent drift, every eta_Q. The only exceptions on the whole grid are two EXPLORATORY budget cells at share 0.25 where Sentinel is WORSE than B1 (B.12).
- MUST NOT: claim Sentinel beats B1 at rho = 1, or that the two are equivalent / that commit-time audit "suffices" (non-significance is not equivalence).
- Wording (LaTeX-ready): At $\rhoP = 1$, where the commit review sees delegated patches at full strength, \Sent{} and B1 cannot be told apart (gain $8.79\%$, 98.75\% CI $[-27.32, 18.86]$; difference $0.0171$, $[-0.0390, 0.0372]$); we read this as no measurable advantage for allocation, not as equivalence.

### C.9 Harm is harm under the mock agent's reception model (`RP` §10 items 6-7; `PR` Q6)
- Data: `StagedMockAgent` on real SWE-bench metadata and topics; a retrieved poisoned item is adopted with probability 0.85 (nominal kernel); harm is scored by a sealed marker oracle; no task is executed; no LLM attacker.
- MUST NOT: present absolute harm levels as what a real coding agent would suffer; call the workflows "real" without "in sequence and topic, simulated in execution".
- Wording (LaTeX-ready): Every harm number is harm under the mock agent's reception model (a retrieved poisoned item is adopted with probability $0.85$, on workflows that are real in sequence and topic but simulated in execution, scored by a sealed marker oracle), so absolute harm levels do not transfer to real agents, and the policy comparisons transfer only insofar as reception does not depend on the audit policy.

### Further boundaries (same status; one sentence each)
- **C.10 eta_Q = 0 is the naive rule, chosen by the objective (`RP` §10 item 12; `FR` I1 "Related").** Harm never rises when more items are removed, so the harm-first objective with a 10% FQ cap picks the grid's lower edge whenever the cap does not bind (dev FQ at eta_Q = 0: 6.37 / 5.97 / 4.46% at rho <= 0.5). Wording (LaTeX-ready): At $\rhoP \le 0.5$ the tuned threshold is $\etaQ = 0$, the naive quarantine-any-anomaly rule: our harm-first objective with a $10\%$ cap on \FQ{} selects the lower edge of the grid whenever the cap does not bind.
- **C.11 The main grid does not measure chi or budget (D4b); the budget sweep is EXPLORATORY and not re-tuned (`FR` M9).** Wording (LaTeX-ready): At the anchored budget \bOne{} no action is ever budget-limited, so the main grid measures where to look rather than how much to spend; everything we report about carrier-cost heterogeneity \chiMAD{} and budget comes from an exploratory sweep with no preregistered test, run with the policy tuned at \bOne{}.
- **C.12 The crossover is a reading rule, not a preregistered test (`RP` §5.3).** No interpolation; the main grid runs at one chi, so it cannot separate "uniform" and "heterogeneous" carrier-cost curves. Wording (LaTeX-ready): On the discrete \Dl{} grid, the smallest delay whose 95\% interval for the harm difference excludes zero is $\Dl = 1$ at $\rhoP \le 0.25$ and $\Dl = 2$ at $\rhoP = 0.5$, with none at $\rhoP = 1$; this reading rule was fixed after the run.
- **C.13 Transfer (`RP` §5.2; D8, D18).** Every eval row is already django -> 16 repos; the plan's development row shares behaviour keys with the held-out class, the D18 row does not. Wording (LaTeX-ready): Tuning used a single repository family, so every evaluation number is a transfer to 16 other repositories; against the six tuning-attacker columns that share no behaviour with the held-out class the gain is $45.12\%$ at $\rhoP = 0$, against $49.20\%$ on the held-out class.
- **C.14 Verified-only is 7 repos / 42 workflows (`RP` §6.4).** Wording (LaTeX-ready): Restricted to the seven SWE-bench Verified repositories (42 workflows) the gain is $49.19\%$ at $\rhoP = 0$ (95\% CI $[44.91, 54.40]$), close to the full-set value.
- **C.15 CI coverage (`FR` I4; `RP` §2.1) - POST HOC.** Wording (LaTeX-ready): Our intervals are percentile bootstraps over 16 unbalanced repository families (one family holds 15 of the 57 workflows, and only 12 families remain at $\Dl = 8$), so their true coverage may fall below the nominal level.
- **C.16 The D30 eval touch (E.1).** Wording (LaTeX-ready): Before the freeze, a smoke run of the evaluation tool touched the evaluation split with an unfrozen configuration (declared deviation D30), after which two tuning grids were widened down to zero; holding the tuned mixtures fixed, the gain's 95\% lower bound stays at or above $25.77\%$ at every \etaQ{} of the grid and every $\rhoP \le 0.5$ (post hoc).
- **C.17 B7 and the covering radius (`RP` §9).** The measured library is the small-game model's 8-policy library, not the 28-member carrier library; no Proposition-6 bound was computed. Wording (LaTeX-ready): On the 240 exactly solvable small games, the 8-policy library of the small-game model has covering radius $0.75$, maximum regret $0.3333$ and mean regret $0.0280$; these numbers do not describe the 28-member carrier library.
- **C.18 The drift sweeps are summarised on harm only (`FR` M3).** Wording (LaTeX-ready): The drift-match and persistent-drift sweeps were summarised on harm only, while drift acts through false quarantine, so they say nothing about the false-quarantine side of drift.
- **C.19 Detection delay (`FR` M9).** Wording (LaTeX-ready): Detection delay averages only over episodes with a detection and counts a blocked marked patch at commit, possibly at or after the trigger, as a detection.
- **C.20 The attacker class.** Wording (LaTeX-ready): Every guarantee is stated against the declared class, 18 scripted rules (7 held out) plus a best response by enumeration over carrier and placement at $\varepsilon = 0.6$; it contains no LLM attacker.
- **C.21 rho_patch scope.** Wording (LaTeX-ready): \rhoP{} governs only attacks placed directly in a skill or a queued call; the memory-to-skill-to-patch chain cannot yield a delegated patch at the trigger because of dormancy, and \rhoP{} was swept, not calibrated to any target harm.
- **C.22 Tuning vs evaluation averaging (`FR` M4).** Wording (LaTeX-ready): Tuning averaged harm over episodes within each column and pooled false quarantine over all \Dl{}, whereas evaluation averages per-workflow means; the tuned mixtures are therefore optimal for a slightly different objective than the one we report.
- **C.23 The bijection (D2).** Wording (LaTeX-ready): We map the four audit kinds and their prices (insertion 0.4, retrieval 0.9, delegation 1.6, commit 4.1) to the four carriers (memory, queue, skill, branch); the mapping is our assumption, and at the anchored budget it affects no result outside the exploratory budget sweep.

---

## E. Declared deviations and v1 issues (one line each)

- **E.1 D30 (eval touch, declared).** On 25/09, while the plan was being built, the assistant ran a smoke of the eval tool ON THE EVAL SPLIT with an unfrozen configuration (1 tuning seed, rho in {0.25, 1}, 3 eval seeds); afterwards three changes were made, all motivated by dev tuning runs: the eta_Q and tau5 grids were widened down to 0, eta_Q ties go to the lowest FQ, and the eta sweep switched to absolute values; the numbers were seen by the assistant only and the record (`spikes/v2-pilot/eval-touch-2509/`) has never been opened; every later smoke used `--split dev`. Chosen values sit on the new lower edges (eta_Q = 0 at rho <= 0.5, tau5 = 0 at rho >= 0.5); POST HOC sensitivity: B.9 (lowest 95% lower bound over the eta grid 36.84 / 32.37 / 25.77% at rho = 0 / 0.25 / 0.5).
- **E.2 D32 (LP tie-break, before the freeze).** The D26 LP can have many optima (at Delta = 0 many members tie at the worst case and HiGHS returns an arbitrary vertex), so a second LP keeps the optimal worst case and takes the lowest FQ%, and `pure` is ordered by worst case, then FQ%, then name; motivated on dev only (`spikes/v2/lp-degeneracy-pre-D32.txt`); it moved 2 of 72 mixtures (rho = 0, strong, Delta = 0 and "all": FQ 5.3% and 7.5% -> 0%), changed no `pure`, no tau5 and no eta_Q, and the endpoint cells (mid, Delta 4 and 8) were not degenerate (`spikes/v2/d32-effect.txt`).
- **E.3 D33 (eval tool aligned with the preregistration, after the freeze, BEFORE the run; no simulated record changed).** 10,000 resamples for every CI with `n_boot` stamped; worst-case L beside V; a failed D28 control withholds every Sentinel number; N workflows / repos / episodes and drop reasons on every row; the eval split runs and is summarised only on a clean freeze header; the D18 transfer row added; raw records not committed, pinned by sha256.
- **E.4 D34 (after the run).** The plan required the "v2 outcome -> paper frame" mapping to be written before the eval and it was not; resolution: no frame chosen after seeing numbers; the paper keeps the regime-map frame fixed on 18-19/09 before any v2 number, the headline is the preregistered endpoint (the gain curve over rho_patch at b1), secondary axes are Delta (RQ1), detector (RQ4) and eta_Q (sweep), the budget axis is EXPLORATORY, v1's budget-axis results stay out, all numbers come from v2, and #19 and #20 go to Threats.
- **E.5 #20 (v1 only).** v1's mock agent keyed its draws on the experiment seed without the workflow id, so for a given seed task t drew the same outcome in every workflow (and workflow-bootstrap CIs were too narrow); v1 was fixed and re-frozen on 25/09 (`sha256:4ff1c8f72df4`), and v2 avoids it by construction (D19: every draw keyed on `seed_of(wf_id, seed)`); no v1 number is used.
- **E.6 G4 / #19 (level 3 not used).** The level-3 detector (an LLM judge scoring a note against its repository context) was never run, and its preregistered agreement check against 38 blind human labels (Clopper-Pearson lower bound >= 0.75, i.e. >= 34/38) needs a human labeller; level 3 is not used, F_detect has no measured signal at level 3, and machine labels are not substituted for human ones.

---

## F. Notation (symbol, meaning, macro)

New macros (added to `main.tex` after the existing block; nothing removed) are marked NEW.

| Symbol | Meaning | Macro | Value / range in v2 |
|---|---|---|---|
| rho_patch | exposure of a delegated patch at commit review, as a fraction of d'(depth 1) | `\rhoP` NEW | {0, 0.25, 0.5, 1} |
| V | worst-case harm: max over the 14 held-out (attacker, Delta) columns of the column mean | `\Vwc` NEW | [0, 1] |
| V_BR | cross-fitted best-response value; a lower bound | `\VBR` NEW | [0, 1] |
| Expl | exploitability, V_BR - V; sign not interpreted | `\Expl` NEW | - |
| FQ | false-quarantine rate, % of benign objects inspected | `\FQ` NEW | % |
| eta_Q | line-8 threshold on P(payload given score) | `\etaQ` NEW | grid {0, ..., 0.3543, 0.5}; tuned 0 / 0 / 0 / 0.3543 |
| kappa | audit cost per unit of depth of a target | `\kap` NEW | 0.4 / 0.9 / 1.6 / 4.1 |
| kbar | mean of the four target costs | `\kbar` NEW | 1.75 |
| chi | cost heterogeneity, 2 MAD / kbar (v2 label) | `\chiMAD` NEW | {0, 0.5, 1.34}; reference table 1.3429 |
| chi_range | an alternative max-min / kbar formula | `\chiRange` NEW | {0, 0.7889, 2.1143} |
| b_1 | anchored budget, H x 3 x 4.1 | `\bOne` NEW | 12.3 H |
| p_attack | window-belief probability that an attack is live | `\pAtt` NEW | prior 0.5 |
| beta_world | per-task drift event rate of a carrier in the world | `\betaW` NEW | 0.314 / 0.058 / 0.033 / 0 |
| beta-hat | moment estimate of that rate from dev | `\betaHat` NEW | 0.3058 / 0.0654 / 0.0326 / 0.0141 |
| tau_5 | B5's escalation threshold | `\tauFive` NEW | tuned 0.1 / 0.1 / 0 / 0 |
| Sentinel-A1 | the tuned policy (text) | `\Sent` NEW (write `\Sent{}` before a space) | - |
| L | loss, harm + lambda_Q Q_false + lambda_T T_lost | `\Loss` (existing) | per episode |
| lambda_Q | weight on Q_false | `\lQ` (existing) | 0.54865 |
| lambda_T | weight on T_lost | `\lT` (existing) | 0.5 |
| Q_false | benign items quarantined (a count) | `\Qf` (existing) | per episode |
| T_lost | clean solved patches blocked at commit | `\Tl` (existing) | per episode |
| d' | detector separation | `\dprime` (existing) | 1.5161 / 2.2114 / 2.9598 (weak / mid / strong, depth 1) |
| Delta | trigger delay, sigma - iota | `\Dl` (existing) | {0, 1, 2, 4, 8} |
| K | number of carriers | `\Karr` (existing) | 4 |
| lambda_x | pairwise L-crossing weight (v1 notion) | `\lX` (existing) | not used by v2 |
| d'* | break-even detector quality (v1 notion) | `\dstar` (existing) | not used by v2 |
| - | anonymised pointer `\repro{path}{anchor}` | `\repro` (existing) | Section G |

Plain symbols without a macro: iota, sigma (insertion and trigger task), H (tasks per workflow, 6-14), tau (BT threshold), psi / phi (hit / false-alarm rate), tau_det (detector threshold), zeta = 0.10 (kernel shift), epsilon (attacker topic-overlap budget).

---

## G. Paths for `\repro{}` reproducibility pointers

Root: paths below are relative to the repository root. Code and run artefacts live under `auditgame/`; documentation lives under `docs/`, one level up from `auditgame/`. Never use absolute paths, user names or repository URLs.

| Pointer | Use it for |
|---|---|
| `auditgame/spikes/v2/eval-summary.json` | every main-grid number: controls, `curve_rho`, `curve_rho_vs_best`, `by_rho.<rho>.table2`, `table3_ablations`, `figure3_gain_by_delta`, `rq4_detectors`, `transfer_*`, `verified_only`, `gate_world`, `denominators`, `run` |
| `auditgame/spikes/v2/eval-sweeps-summary.json` | `eta`, `match`, `drift_visible`, `budget_EXPLORATORY` |
| `auditgame/spikes/v2/small-games.json` | B7, covering radius, regret, double oracle |
| `auditgame/reference/v2_tuned.json` | beta-hat, tau5, eta_Q, mixtures, `pure` |
| `auditgame/spikes/v2/select-log.txt` | the dev tuning log (eta_Q choice, dev harm and FQ) |
| `auditgame/spikes/v2/d32-effect.txt`, `auditgame/spikes/v2/lp-degeneracy-pre-D32.txt` | D32 and the 10-way tie |
| `auditgame/spikes/v2/eval-log.txt` | the run time and record counts (a line in that file holds an absolute path: scrub before including it in the package) |
| `auditgame/spikes/v2/eval-records.sha256` | the pinned raw records |
| `auditgame/frozen/MANIFEST.json` | the v2 freeze (`digest`) |
| `auditgame/tools/run_draft_eval.py`, `auditgame/tools/select_mixture.py`, `auditgame/tools/solve_small_games.py` | the eval, the tuning, B7 |
| `auditgame/draft_setup.py`, `auditgame/carrier_runner.py`, `auditgame/world_v2.py`, `auditgame/detector.py`, `auditgame/attackers_v2.py`, `auditgame/corpus_v2.py`, `auditgame/carrier_policies.py`, `auditgame/sentinel.py`, `auditgame/belief_v2.py`, `auditgame/metrics_v2.py`, `auditgame/gate_world.py` | model, world, attackers, corpus, policies, metrics, secondary world |
| `docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md` | D1-D34 (anchor "D30" etc.), the endpoint, P1-P6, Q1-Q12, the execution record (post-hoc findings I1, M8, the deciding-column read) |
| `docs/reports/v2-so-voi-draft.md` | the post-hoc readouts (anchor "§2.2" deciding columns; "§3" BR bracket; "§4.1" BT lock-in; "§5.5" eta sweep and D30 sensitivity; "§10" deviations and declared limits) |

Not usable as pointers: the final branch review (gitignored, not in the package); `posthoc.py`, `posthoc.json` and `check.py` (outside the repository); the raw `*.jsonl` records (not committed; archiving them is a packaging decision, `FR` M11).

Example: `\repro{auditgame/spikes/v2/eval-summary.json}{\texttt{curve\_rho}}`, `\repro{docs/preregistration/TIEN-DANG-KY-v2-thiet-lap-draft.md}{D30}`, `\repro{docs/reports/v2-so-voi-draft.md}{\S2.2, post hoc}`.
