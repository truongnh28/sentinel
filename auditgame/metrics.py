"""
metrics.py -- The three-tier metric stack.  (B5)

Spec: docs/thesis/eval/SPEC-Tang-Do-va-Test.md, Parts 4-5, SS6.4, SS8.3.

Three jobs, each closing a hole that was actually measured:

  1. gain() returns None once the denominator stops meaning anything.  The old
     experiment.py divided by max(h_B1, 1e-9): as h_B1 -> 0 the ratio explodes or
     flips sign -- precisely in the Delta=0 cell we most need to read.
  2. report_header() enforces FORMAT.  Gate 3 cannot be enforced by assertions;
     a table missing these lines is not a results table.
  3. The three terms of L, and lambda* instead of inventing a lambda.
"""
from __future__ import annotations

# Below this the ratio stops meaning anything -- report ABSOLUTE Delta-harm.
GAIN_FLOOR = 0.05

#: Default weights of the composite loss.  NOT derived from anything -- the
#: manuscript never published them, and they sit in the "ask the advisor"
#: parameter list.  They exist so a table can be printed at all; the REPORTABLE
#: quantity is lambda_q_star() below, which says where the ranking changes.
#: Anything stated at a single lambda_Q is a statement about that lambda_Q.
LAMBDA_Q = 0.10
LAMBDA_T = 0.50


def gain(h_b1: float, h_sentinel: float, floor: float = GAIN_FLOOR):
    """Percent reduction in worst-case harm vs B1 -- or None if meaningless.

    Returns None, NOT 0 and NOT NaN: None forces the caller to handle it, while 0
    would quietly average in and turn "unreadable" into "no benefit".
    """
    if h_b1 < floor:
        return None
    return 100.0 * (h_b1 - h_sentinel) / h_b1


def report_header(config_sha: str, n_feasible: int, n_total: int,
                  n_survived: int, lock_sha: str) -> str:
    """The five mandatory lines of every results table (SS8.3).

    They pre-answer the first five questions a reviewer asks.  A bare number
    without them FORCES THE READER TO TRUST US -- which is the very thing this
    framework exists to avoid having to beg for.
    """
    pct = (100.0 * n_survived / n_feasible) if n_feasible else float("nan")
    return (f"config     sha256:{config_sha[:12]}...\n"
            f"feasible   {n_feasible}/{n_total}\n"
            f"survived   {n_survived}/{n_feasible} ({pct:.0f}%)\n"
            f"env        lock:{lock_sha[:12]}")


def loss(harm: float, q_false: float, t_lost: float,
         lambda_Q: float = LAMBDA_Q, lambda_T: float = LAMBDA_T) -> float:
    """L = E[harm] + lambda_Q E[Q_false] + lambda_T E[T_lost].  (Toan-canh SSA.4)

    Why three terms and not one.  With lambda_Q = lambda_T = 0, the policy
    "quarantine all K carriers at t=1" drives harm to 0 and is therefore optimal --
    while shutting the system down completely.  SSA.4 calls the one-term model
    "trivially solvable and useless", and every number measured before this
    function existed scored exactly that model.

    Measured consequence on the mock: the ranking flips at lambda_Q ~ 0.05.  Below
    it Sentinel wins; above it B5 does, because Sentinel buys its harm advantage by
    quarantining 6.3x more (Q_false 1.700 against 0.272).
    """
    return harm + lambda_Q * q_false + lambda_T * t_lost


def lambda_q_star(cells: dict, lambda_T: float = LAMBDA_T, hi: float = 5.0):
    """The smallest lambda_Q > 0 at which the L-ranking stops naming the same policy.

    `cells` is {policy -> (harm, q_false, t_lost)}.  Returns None if no weight in
    (0, hi] changes the winner -- either one policy dominates on every term, or
    Q_false is not actually being measured.

    REPORT THIS INSTEAD OF PICKING A WEIGHT.  "Sentinel is best" is a claim about
    the policy only if it survives the plausible range of lambda_Q; if the flip sits
    at 0.05, the real claim is "a false quarantine costs under a twentieth of a
    slipped payload", which a reader can judge for their own setting.  Same move as
    eps*: an unanswerable parameter becomes a result.

    Solved EXACTLY, not by bisection.  For each policy L is affine in lambda_Q with
    slope q_false, so the winner changes only where two of those lines cross.  An
    earlier bisection assumed the winner moves monotonically toward lower Q_false;
    it does not, because a policy can carry a large T_lost that keeps it out of the
    running at every lambda_Q (measured: B1 has Q_false 0.000 and T_lost 0.453).
    """
    names = list(cells)
    if len(names) < 2:
        return None

    def L(k, lq):
        return loss(*cells[k], lambda_Q=lq, lambda_T=lambda_T)

    base = min(names, key=lambda k: L(k, 0.0))
    crossings = set()
    for k in names:
        if k == base:
            continue
        dh = (cells[k][0] - cells[base][0]) + lambda_T * (cells[k][2] - cells[base][2])
        dq = cells[k][1] - cells[base][1]
        if abs(dq) < 1e-12:
            continue
        x = -dh / dq                          # L_k(x) == L_base(x)
        if 1e-9 < x <= hi:
            crossings.add(x)
    for x in sorted(crossings):
        nudge = x + 1e-6
        if min(names, key=lambda k: L(k, nudge)) != base:
            return x
    return None


def _requirements_lock_sha() -> str:
    """sha256 of the pinned `requirements.lock` -- the ENVIRONMENT half of a
    results table's evidence.

    Not a parameter of `results_table`: the running environment is not a
    per-call choice, it is a fact about the machine the table was printed on,
    read straight from the lock file that pinned it (PLAN.md Task 0, Buoc 0.6:
    "Header bang ket qua in sha256 cua lock file canh sha256 cau hinh").
    """
    import hashlib, pathlib
    lock = pathlib.Path(__file__).resolve().parent.parent / "requirements.lock"
    return hashlib.sha256(lock.read_bytes()).hexdigest()


def results_table(cells: dict, config_sha: str, n_feasible: int,
                  n_total: int, n_survived: int) -> str:
    """A results table that CARRIES ITS OWN EVIDENCE.

    Wraps report_header -- it does not replace it.  `cells` is
    {policy name -> {"harm": float, "per_wf": list}}.  B1 and Sentinel are both
    required, since Delta-harm is defined through that pair.

    The CI resamples BY WORKFLOW, not by case: cases from one workflow share a task
    chain and the same clean-run outcome, so they are not independent and resampling
    by case gives FALSELY NARROW intervals.
    """
    import runner
    b1, sn = cells["B1 audit-at-commit"], cells["Sentinel"]
    dh = b1["harm"] - sn["harm"]
    lo, hi = runner.bootstrap_paired(b1["per_wf"], sn["per_wf"])
    g = gain(b1["harm"], sn["harm"])
    gain_text = f"{g:+.1f}%" if g is not None else "-- (denominator < 0.05)"
    return (report_header(config_sha, n_feasible, n_total, n_survived,
                          _requirements_lock_sha()) + "\n"
            + f"d-harm     {dh:+.3f}  CI95 [{lo:+.3f} ; {hi:+.3f}]  gain {gain_text}")


def config_sha(*, pi0: float, aggregation: str, tau_sel, theta: float, scope: str) -> str:
    """sha256 over the FROZEN parameters that must sit in ONE hash cell together
    (Global Constraints, "Gia phai tra" #2): pi0, the aggregation rule, tau_sel,
    theta, and the dataset scope.  `experiment.py` calls this to build the
    config_sha it passes to `results_table` -- see Step 7.5.

    Keyword-only and named per field on purpose: a positional signature lets a
    caller silently reorder two arguments of the same type (tau_sel and theta are
    both numbers) and get a DIFFERENT hash for the SAME configuration, which is
    the one failure mode a freeze exists to rule out.

    theta sat outside every hash for as long as CarrierStore.retrieve used `==`
    instead of it -- it was not a parameter yet, just an implicit 1.0.  Adding a
    field here without a test that moves the digest (test_config_sha_moves_when_
    theta_moves) is exactly the gap that let that go unnoticed.
    """
    import hashlib
    blob = (f"pi0={pi0!r}|aggregation={aggregation!r}|tau_sel={tau_sel!r}|"
            f"theta={theta!r}|scope={scope!r}")
    return hashlib.sha256(blob.encode()).hexdigest()


def spend_table(spent: dict, budget: float) -> str:
    """Budget CONSUMED per policy, next to the cap.

    "Every policy runs on the same budget B" is true of the CAP and false of the
    SPEND.  Measured: B5 reaches B1's harm on 0.40 of a 17.95 budget while B1
    spends 16.40 and Sentinel 6.47.  A harm table without this one reads three
    policies as comparable when one of them declined to play.
    """
    w = max(len(k) for k in spent) if spent else 10
    out = [f"{'policy':<{w}}{'spent':>9}{'cap':>9}{'used':>8}"]
    out.append("-" * (w + 26))
    for k, v in sorted(spent.items(), key=lambda kv: -kv[1]):
        out.append(f"{k:<{w}}{v:>9.2f}{budget:>9.2f}{100.0*v/budget:>7.0f}%")
    return "\n".join(out)
