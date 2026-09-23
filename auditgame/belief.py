"""Sequential belief over ATTACK WINDOWS -- Toan-canh section 5.1 and 5.4.

WHAT THE DOCUMENT ASKS FOR, and what was here before.

Section 5.1 defines b_t as a distribution over (c, iota, sigma): WHICH carrier,
WHEN it was inserted, WHEN it detonates. That triple is what lets the defender
"act on the delay" -- an alarm at task t raises the posterior on insertions at
t' < t whose trigger is at t'' > t, which is looking backwards and forwards at
once. A stateless policy cannot do that.

`policies.Sentinel.belief` was a dict of FOUR FLOATS, one per carrier, updated
by an exponential moving average. It has no time axis at all, so it could not
express the claim of 5.1 even in principle. `SSGReceding`'s own docstring
already said as much: "needs a posterior over WINDOWS which does not exist
yet". This module is that posterior.

SECTION 5.4 FALLS OUT OF THE SAME OBJECT, rather than being a second mechanism.
Benign drift is asked to be "a separate latent cause with its own rate beta",
competing to explain an alarm. Here that is one extra hypothesis, NULL, sitting
in the same normalised posterior as the windows. An alarm raises the windows it
is consistent with AND the null together; only their RATIO moves. When beta is
large the null absorbs most of the evidence and nothing gets quarantined -- and
that is exactly the usability mechanism section 5.4 describes, expressed as a
probability rather than as a threshold tweak.

WHAT THIS IS NOT.  Section 5.1 says "particle filter, 2048 particles". The
window space here is SMALL -- K x |Delta| x H is a few hundred cells -- so the
posterior is computed EXACTLY by enumeration. A particle filter approximates a
distribution that cannot be enumerated; using one here would add sampling noise
and buy nothing. Recorded as a deliberate deviation, not an omission.

DETERMINISTIC. No sampling anywhere; the same observations always give the same
posterior.
"""
from __future__ import annotations

import costs
import scoring


class WindowBelief:
    """Posterior over {(k, iota, sigma)} U {NULL}.

    NULL is "no attack; benign drift explains what we have seen" -- section
    5.4's competing cause, carried in the same normalisation so the two
    hypotheses actually compete instead of being compared to a fixed bar.
    """

    NULL = "null"

    def __init__(self, carriers, H: int, deltas, beta: float = costs.BETA_DEFAULT,
                 pi_attack: float = 0.5):
        """`beta` is the drift rate of section 5.4; `pi_attack` the prior that
        an attack exists at all, split evenly over the feasible windows.

        beta enters as the NULL's prior mass, not as a smoothing constant: a
        world with more benign churn is a world where "drift did it" starts out
        more plausible, which is what the parameter means in the document.
        """
        self.carriers = list(carriers)
        self.H = H
        self.deltas = tuple(deltas)
        self.beta = beta
        self.windows = [(k, i, i + d)
                        for k in self.carriers
                        for d in self.deltas
                        for i in range(H - d)]
        if not self.windows:                      # N3: say why, do not return {}
            raise ValueError(
                f"no feasible window for carriers={self.carriers} H={H} "
                f"deltas={self.deltas}: a belief over an empty support would "
                f"normalise to the null alone and read as 'nothing is under "
                f"attack', which is a claim, not an absence of data")
        w = pi_attack / len(self.windows)
        self.b = {win: w for win in self.windows}
        self.b[self.NULL] = 1.0 - pi_attack

    # ---------------------------------------------------------------- update

    def active(self, win, t: int) -> bool:
        """Is this window LIVE at t -- inserted, not yet detonated.

        Half-open on purpose: at t == sigma the payload has already been
        retrieved (runner reads P1/P2 BEFORE this task's audit can act), so a
        window that detonates at t is no longer something an audit at t can
        prevent.
        """
        _k, i, s = win
        return i <= t < s

    def update(self, t: int, signals: dict) -> None:
        """Bayes on one task's carrier posteriors.

        signals[c].p is already a per-carrier posterior (scoring.carrier_score,
        mean-Lambda). Its evidence ratio against the prior is p / PI0, the same
        quantity `policies.UPDATE_RULES["ratio"]` uses -- reused rather than
        re-derived so the two cannot drift apart.

        A window (k, i, s) live at t predicts carrier k is poisoned, so it earns
        the ratio of carrier k. Every other hypothesis -- windows not live, and
        the null -- predicts all carriers are clean, so they earn the ratio of
        NOT seeing evidence. Both are applied to the SAME posterior and then
        normalised, which is where the competition in 5.4 happens.
        """
        ev = {}
        for c in self.carriers:
            sig = signals.get(c)
            p = getattr(sig, "p", sig)
            p = scoring.PI0 if p is None else float(p)
            ev[c] = max(p, 1e-12) / scoring.PI0
        # "no carrier fired" evidence for the hypotheses that predict silence
        quiet = 1.0
        for c in self.carriers:
            quiet *= max(1.0 - min(ev[c] * scoring.PI0, 1.0 - 1e-12), 1e-12)
        quiet /= max((1.0 - scoring.PI0) ** len(self.carriers), 1e-12)

        post = {}
        for win in self.windows:
            k, _i, _s = win
            post[win] = self.b[win] * (ev[k] if self.active(win, t) else quiet)
        # The null also has to explain the drift it is named for: beta scales
        # how much silence it is allowed to claim credit for.
        post[self.NULL] = self.b[self.NULL] * (quiet ** (1.0 - self.beta))

        z = sum(post.values())
        if z <= 0.0:
            return                                 # keep the prior; see N3 above
        self.b = {h: v / z for h, v in post.items()}

    # ----------------------------------------------------------------- reads

    def p_attack(self) -> float:
        """Total mass on "some window is real" -- one minus the null."""
        return 1.0 - self.b[self.NULL]

    def carrier_mass(self, t: int) -> dict:
        """Mass per carrier over windows LIVE at t -- what a policy can act on.

        This is the quantity `Sentinel.belief` was standing in for, except it
        now comes from a posterior with a time axis, so an alarm at t can raise
        a window inserted earlier whose trigger is still ahead.
        """
        out = {c: 0.0 for c in self.carriers}
        for win in self.windows:
            if self.active(win, t):
                out[win[0]] += self.b[win]
        return out

    def window_mass(self) -> dict:
        """The full posterior over windows, for the LP's min-over-windows term."""
        return {w: self.b[w] for w in self.windows}
