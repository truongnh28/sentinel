# v3 P2 — T13: Algorithm 1 lines 2–3 (the exact solve when KH ≤ 40)

27/09/2026. Branch `w4-t13`. Module `auditgame/v3/exact.py`, tests `auditgame/tests/v3/test_alg1_line23.py`, DCM shard `auditgame/v3/dcm/T13.csv`.

## What the draft asks

> "2: if game is small (KH ≤ threshold) then 3: at ← exact minimax solution by backward induction on the belief MDP" (Alg. 1)
>
> "Small games (KH ≤ 40 belief-state discretisation) are solved exactly by backward induction over a discretised belief simplex." (§7)

K = 4 carriers, so KH ≤ 40 means H ≤ 10. The eval source (D-v3-1) draws H ~ U{6..14}, so about 5/9 of eval workflows fall under line 2's threshold. On dev (the v2 corpus), 61 of 100 workflows have H ≤ 10, and none has H ≤ 5.

## What was built

**The solver.** The solver builds a sequence-form minimax LP over the defender's history tree and solves it with HiGHS through scipy.
- **Observations.** Each audit's observation is discretised to alarm or quiet. The checkpoint is merged out of the tree, because its likelihood ratio is 1 under O8.
- **Attacker.** The attacker commits to a pure placement (k, ι, σ = ι + Δ̂) before the episode.
- **Defender.** The defender optimises over every observation-dependent randomised policy, under a hard budget on every path.
- **Exactness.** Against a finite set of pure placements, this LP is the exact minimax value. The "discretised belief simplex" is the finite set of beliefs the tree reaches, so no grid error enters.

**The game (declared, L2).** The game is the v3 world reduced to the solve:
- **Hidden state.** The hidden state is z = (c over memory, queue and skill; phase).
- **Propagation.** Poison propagates to skill and queue at the rates of `agent.kernel_of`.
- **Activation at σ.** At σ, the poison activates with probability equal to the adoption rate. The route is delegated if any live poisoned source is delegated (O1).
- **Detection.** Sweep and commit detection use the same means as `observe.py`, including ρ·d′ on a delegated patch, d′√d on a direct one, A7 provenance, and a transient drift event at β_k.
- **Response.** After an alarm, the defender chooses to quarantine the audited carrier or to continue (`respond="choose"`, the primary). The sensitivity `respond="always"` quarantines on every alarm.
- **Loss.** The loss is Definition 1's, with v2's λ values:
  - harm locked at σ (C11);
  - FQ, counted per the O7 unit;
  - clean patches lost on a branch quarantine (O7).

**What the game leaves out.** The following are declared and routed to line 5 with reason `world`:
- branch seeding;
- two seeded carriers;
- reversible harm;
- persistent drift;
- hidden ingress;
- the stage world.

**The feasibility rule.** Line 3 runs only when all of the following hold. The rule was declared before measuring (plan T13; `config.LINE23_*`).
- KH ≤ 40;
- the tree has ≤ 10⁶ sequences, counted exactly before anything is built;
- build plus LP take ≤ 60 s for the workflow.

Otherwise `line23()` returns an `InfeasibleRecord` holding the states, decision nodes, strategies, runtime, a memory estimate and the peak RSS. It logs `line23: infeasible, states=…, runtime=…, memory=…`, and Sentinel runs line 5 instead (L2). When KH > 40, the draft's else-branch applies, and nothing is built.

## Tests (3, all green; about 3 s)

| Test | DCM | What it checks |
|---|---|---|
| `test_line2_exact_when_KH_le_40_or_logs_infeasibility` | DA1.l2 | H = 3 solves exactly; the plan satisfies the sequence-form flow; the policy walks it on quiet and alarm paths and logs x_t, never the draw. H = 8 gives an infeasibility record and the log line. A 1 µs cap gives a `runtime` refusal. An unmodelled world gives a `world` refusal. H = 11 goes to line 5 with nothing built |
| `test_exact_matches_smallgame_on_coverage_reduction` | D1.small | With ψ = 1, φ = 0, no propagation and window {ι..ι+Δ}, the tree solve equals `smallgame.solve` to 1e-6 on 192 games: every 240-grid game with H ≤ 5, plus H = 6 at K = 2 |
| `test_library_never_beats_exact_value` | D5.2.l3 | No stand-in policy, evaluated exactly in the same tree, beats the exact value (every ρ, H ∈ {3, 4}, Δ̂ ∈ {0, 1, 2}, plus coverage games). The exact plan re-evaluated gives the LP value back |

The 28 library members belong to T11. Until they land, the stand-ins are:
- B1, uniform, insertion, rotation, recheck and idle, each with and without quarantine on alarm;
- the stationary commit/sweep mixes r ∈ {0, 0.25, 0.5, 0.75, 1}.

## The measured frontier

Setup: primary world, cell ρ = 0.5, χ = 1.33, mid detector, K_d = 2, b1 budget, Δ̂ = 1 (the O3 prior, which gives the most placements). The machine is an M5 running one process. K is the number of audit targets: commit, then memory, queue and skill. K = 4 is the v3 game. Raw rows come from `python -m v3.exact --frontier`.

**Largest solvable H within the declared limits (≤ 10⁶ sequences, ≤ 60 s):**

| K (targets) | respond = choose (primary) | respond = always |
|---|---|---|
| 1 | H = 9 (349,524 seq, 14.2 s) | H = 10 (59,048 seq, 1.4 s) |
| 2 | H = 7 (960,799 seq, 20.5 s) | H = 8 (292,968 seq, 8.2 s) |
| 3 | H = 5 (111,110 seq, 1.3 s) | H = 7 (549,028 seq, 25.1 s) |
| **4** | **H = 5 (402,233 seq, 14.4 s; LP 13.5 s)** | **H = 6 (332,150 seq, 9.3 s)** |

For every row, the sequence cap binds first: the next H has more than 10⁶ sequences. Branching grows as (1 + 3K)^H with choose and (1 + 2K)^H with always.

**K = 4, respond = choose: the evidence beyond the frontier.** Runtime and memory are extrapolated linearly from the H = 5 solve (35.7 µs per sequence). The LP is superlinear, so these are **lower bounds**.

| H | KH | sequences | decision nodes | placements | runtime ≥ | memory ≥ |
|---|---|---|---|---|---|---|
| 5 | 20 | 402,233 | 154,705 | 12 | 14.4 s (measured) | 1.4 GiB (est.) |
| 6 | 24 | 5,229,042 | 2,011,170 | 15 | 187 s | 22 GiB |
| 7 | 28 | 67,977,559 | 26,145,215 | 18 | 40 min | 348 GiB |
| 8 | 32 | 883,708,280 | 339,887,800 | 21 | 8.8 h | 5.1 TiB |
| 9 | 36 | 11,488,207,653 | 4,418,541,405 | 24 | 4.7 days | 76 TiB |
| 10 | 40 | 149,346,699,502 | 57,441,038,270 | 27 | 62 days | 1.1 PiB |

The peak RSS of the frontier process reached 2.7 GiB, at the K = 4, H = 5 solve.

## Reading

- **Line 3 almost never runs on real workflows.** Line 3 is exact and runs for K = 4 only when H ≤ 5 (H ≤ 6 with the forced response). Every workflow on dev and eval has H ≥ 6. So in the primary configuration, line 3 never runs on a real workflow. Every workflow with 6 ≤ H ≤ 10 gets an infeasibility record and runs line 5 (L2): 61/100 on dev, and about 5/9 of eval by construction. This confirms risk R1 of the plan, whose estimate was (|A|·|O|)^H ≈ 10^10–10^13 at H = 10. The measured count is 1.5·10^11.
- **Line 3 as the validation oracle** (§5.2) is feasible where the draft uses it: the small games of H ≤ 6. T21 can call `build_tree`, `solve_tree` and `evaluate`.
- **The loss saturates at 0.85.** In the v3 game at ρ = 0.5 and Δ̂ = 1, the exact value saturates at 0.85 (never auditing = the adoption rate) from H ≥ 4. The O7 accounting drives this: a late branch quarantine loses about 0.62·t clean patches at λ_T = 0.5, which costs more than the harm it averts. So the attacker's best placement is late, and no audit policy pays there. This is a property of the declared loss, not of the solver. It is recorded here because line 5 faces the same trade-off.

## Choices (for review)

1. **Sequence-form LP, not a belief-grid DP.** Both are "backward induction on the belief MDP". The LP gives the minimax value against a policy-aware attacker exactly, with no discretisation error. A Bayes DP over a belief grid would solve a different, averaged game.
2. **Binary observation (alarm / quiet).** This is the discretisation the draft names. The raw scores are not in the tree.
3. **The defender chooses the response after an alarm** ("choose") as the primary, because the draft's defender "chooses validation, quarantine or continuation". The forced response is kept as a sensitivity.
4. **When the plan runs, Sentinel's lines 8–9 would override the response.** `ExactLine3Policy` then leaves the tree, logs it, and returns None; T15 decides how the two combine.
5. **The feasibility limits come from config** (`LINE23_MAX_SEQUENCES = 10^6`, `LINE23_MAX_SECONDS = 60`), set in W0 before this measurement.

## Addendum 27/09: O7 decided

The author decided (L1) that a branch quarantine removes only the poisoned lineage: the marked patches, plus every item whose `derived_from` chain reaches a poisoned item. Clean patches stay. Memory, skill and queue keep whole-carrier removal. The runner (`Episode.removed_by_quarantine`) and the exact game (`Game.branch_lineage = True`, the default) use the same accounting. `branch_lineage=False` keeps the old game, so the finding above stays reproducible.

At ρ = 0.5, χ = 1.33, mid detector, b1 and Δ̂ = 1:

| H | whole branch (old) | poisoned lineage (new) |
|---|---|---|
| 3 | 0.739 | 0.502 |
| 4 | 0.828 | 0.547 |
| 5 | 0.850 (= no-audit loss) | 0.582 |

With the lineage rule the value no longer depends on λ_T (`test_exact_branch_quarantine_loses_no_clean_patch`).
