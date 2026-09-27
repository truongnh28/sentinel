"""Algorithm 1 line 7 and draft S7 "Belief update": the particle filter (T9).

Each test protects the DCM rows of v3/dcm/T09.csv that name it; its docstring carries the
row ids and the verbatim draft sentence.  Run from auditgame/.
"""
import dataclasses
import unittest

import numpy as np

from core import CARRIERS, seed_of
from v3 import api as A
from v3 import belief_exact as BE
from v3 import belief_pf as BP
from v3 import config as C

SEED = 20260927


def _ctx(H=8, rho=0.5, delta=4, world=C.PRIMARY, k_d=C.K_D_PRIMARY, postmortems=(),
         seed=SEED):
    cell = C.Cell(rho=rho, delta=delta, k_delegated=k_d)
    return A.EpisodeContext(world=world, cell=cell, wf_id="wf-line7", seed=seed, H=H,
                            budget=1e9, depths=cell.depths(), kappa=cell.kappa(),
                            delegated=cell.delegated(), postmortems=tuple(postmortems),
                            rng_seed=seed_of(seed, "line7-test"))


def _nothing(t, checkpoint=True):
    return A.Observation(t=t, requested=None, bought=None, checkpoint=checkpoint)


def _sweep(t, target, scores, written_at, depth=1):
    a = A.AuditAction(target, depth)
    return A.Observation(t=t, requested=a, bought=a, scores=tuple(float(s) for s in scores),
                         alarm=any(s > 1.2 for s in scores), written_at=tuple(written_at),
                         checkpoint=True)


def _commit(t, s, depth=1, provenance=None):
    a = A.AuditAction("commit", depth)
    return A.Observation(t=t, requested=a, bought=a, scores=(float(s),), alarm=s > 1.2,
                         written_at=(t,), checkpoint=True, provenance=provenance)


def _run(b, obs_by_t, upto):
    for t in range(upto + 1):
        b.update(t, obs_by_t.get(t, _nothing(t)))
    return b


def _window(t):
    """iota < t < sigma: inserted before t, triggering after t."""
    return lambda st: st["attacked"] & (st["iota"] < t) & (st["sigma"] > t)


@dataclasses.dataclass(frozen=True)
class PostMortemWithAudits(A.PostMortem):
    """A post-mortem that also carries the defender's audits: the interface need of O11
    (api.PostMortem has `alarms` only), reported with T9."""
    audits: tuple = ()                     # ((t, target, depth, n_inspected), ...)


class TestAlg1Line7(unittest.TestCase):

    # ---- D7.pf2048, D5.1.belief ----------------------------------------------------

    def test_line7_particle_filter_has_2048_particles_over_c_iota_sigma(self):
        """D7.pf2048: "A particle filter (2048 particles) over (c, ι, σ) with the benign-drift
        process as a competing transition"
        D5.1.belief: "Sentinel maintains bt , a distribution over (c, ι, σ), updated from
        alarm observations and checkpoint outcomes with the benign-drift process as a
        competing explanation."

        The factory is an api.BeliefFactory; the belief is an api.BeliefAPI of exactly
        config.PF_PARTICLES = 2048 numpy particles, each carrying c in {0,1}^4, iota and
        sigma; it is moved by alarms, and the checkpoint enters with likelihood ratio 1
        (O8), so two filters that differ only in the checkpoint outcome agree."""
        self.assertEqual(C.PF_PARTICLES, 2048)
        ctx = _ctx()
        b = BP.make_belief(ctx, None)
        self.assertIsInstance(b, A.BeliefAPI)
        self.assertEqual(b.n, 2048)
        st = b.particles()
        for key in ("attacked", "c", "iota", "sigma"):
            self.assertIsInstance(st[key], np.ndarray)
            self.assertEqual(len(st[key]), 2048)
        self.assertTrue(np.all(st["c"] < 16))
        att = st["attacked"]
        self.assertTrue(np.all(st["sigma"][att] - st["iota"][att] >= 0))
        self.assertTrue(np.all(st["sigma"][att] < ctx.H))
        for h in b.sample(8, seed_of(SEED, "draws")):
            self.assertIsInstance(h, A.Hypothesis)
            self.assertEqual(len(h.c), len(CARRIERS))
            self.assertEqual(h.iota is None, not h.attacked)
        # the exact enumerator is the same kind of object
        self.assertIsInstance(BE.make_exact_belief(ctx, None), A.BeliefAPI)

        # checkpoint outcomes: ratio 1 (O8)
        b1, b2 = BP.make_belief(ctx, 4), BP.make_belief(ctx, 4)
        for t in range(4):
            b1.update(t, _nothing(t, checkpoint=True))
            b2.update(t, _nothing(t, checkpoint=False))
        self.assertEqual(b1.distribution(), b2.distribution())
        # alarm observations: a memory sweep that fires on the item written at task 1
        # moves Pr[c[memory] = 1] away from the same sweep without the alarm
        quiet, b3 = BP.make_belief(ctx, 4), BP.make_belief(ctx, 4)
        for b in (quiet, b3):
            _run(b, {}, 2)
        quiet.update(3, _sweep(3, "memory", [0.1, 0.2, 0.4, -0.3], [0, 1, 2, 3]))
        b3.update(3, _sweep(3, "memory", [0.1, 4.0, 0.4, -0.3], [0, 1, 2, 3]))
        self.assertGreater(b3.carrier_mass()["memory"], quiet.carrier_mass()["memory"] + 0.1)
        # the O16 features of the line-5 table
        f = b3.bin_features()
        self.assertIsInstance(f, A.BinFeatures)
        self.assertAlmostEqual(f.p_attack, b3.p_attack(), places=12)
        self.assertEqual(f.top_carrier, "memory")
        deleg = BP.mask_of(ctx.delegated)
        self.assertAlmostEqual(f.delegated_mass, b3.mass(lambda s: (s["c"] & deleg) != 0),
                               places=12)
        self.assertEqual(f.delegated_high, f.delegated_mass > C.BIN_DELEGATED_MASS_THRESHOLD)
        self.assertLessEqual(b3.p_poisoned(), b3.p_attack() + 1e-12)
        self.assertGreaterEqual(b3.expected_harm(), 0.0)
        self.assertLessEqual(b3.expected_harm(), 1.0)
        # lines 8-9 remove the carrier: its bit is 0 in every particle
        b3.condition_on_quarantine(3, "memory")
        self.assertEqual(b3.carrier_mass()["memory"], 0.0)

    # ---- the exact benchmark -------------------------------------------------------

    def test_pf_matches_exact_posterior_on_small_cases(self):
        """D7.pf2048: "A particle filter (2048 particles) over (c, ι, σ) with the benign-drift
        process as a competing transition"

        On small workflows (H = 3..5) and scripted observation sequences over every audit
        target, alarm and silence, the 2048-particle filter's posterior over (attacked, c,
        iota, sigma) is within the TV distance declared before the run
        (belief_pf.PF_EXACT_TV_MAX, mean over every task of every case) of the exact
        enumerator that runs the same model, and its read-outs (p_poisoned, p_attack,
        carrier_mass) within PF_EXACT_MARGINAL_MAX on average."""
        cases = []
        for H in (3, 4, 5):
            for rho in (0.0, 0.5):
                for dhat in (None, 1, 2):
                    cases.append((H, rho, dhat))
        tvs, errs = [], []
        for ci, (H, rho, dhat) in enumerate(cases):
            ctx = _ctx(H=H, rho=rho, delta=4, seed=SEED + ci)
            rng = np.random.default_rng(seed_of(SEED, "pf-vs-exact", ci))
            pf = BP.make_belief(ctx, dhat)
            ex = BE.make_exact_belief(ctx, dhat)
            for t in range(H):
                g = rng.integers(0, 5)
                if g == 4:
                    o = _nothing(t)
                elif C.TARGETS[g] == "commit":
                    o = _commit(t, rng.choice([rng.normal(), 3.0]), depth=1)
                else:
                    target = C.TARGETS[g]
                    w = sorted(set(int(x) for x in rng.integers(0, t + 1, size=t + 1)))
                    s = rng.normal(size=len(w))
                    if rng.random() < 0.5:
                        s[rng.integers(0, len(w))] = 3.0
                    o = _sweep(t, target, s, w, depth=ctx.depths[target])
                pf.update(t, o)
                ex.update(t, o)
                tvs.append(BP.total_variation(pf.distribution(), ex.distribution()))
                cm_p, cm_e = pf.carrier_mass(), ex.carrier_mass()
                errs.extend([abs(pf.p_poisoned() - ex.p_poisoned()),
                             abs(pf.p_attack() - ex.p_attack())]
                            + [abs(cm_p[k] - cm_e[k]) for k in CARRIERS])
        self.assertLessEqual(float(np.mean(tvs)), BP.PF_EXACT_TV_MAX,
                             f"mean TV {np.mean(tvs):.4f}, max {np.max(tvs):.4f}")
        self.assertLessEqual(float(np.mean(errs)), BP.PF_EXACT_MARGINAL_MAX,
                             f"mean read-out error {np.mean(errs):.4f}")
        self.assertEqual(BP.PF_EXACT_TV_MAX, 0.12)          # declared before the run
        self.assertEqual(BP.PF_EXACT_MARGINAL_MAX, 0.03)

    # ---- D4.drift, D5.4.drift ------------------------------------------------------

    def test_drift_is_a_competing_cause(self):
        """D4.drift: "A latent process independently modifies carriers benignly at rate β,
        with observation statistics matched to poisoning events."
        D5.4.drift: "The belief update treats benign modification as a distinct latent
        cause with its own rate β, estimated online."

        An alarm on an item written THIS task can be a fresh drift write (transient drift,
        D6), so the higher beta_memory the less it raises Pr[c[memory] = 1]; with beta = 0
        (the '- benign-drift modelling' ablation) the alarm is evidence of poison only.
        An alarm on an item written EARLIER cannot be transient drift: beta barely moves
        what it says."""
        ctx = _ctx(H=8, rho=0.5)
        fresh = _sweep(3, "memory", [0.2, -0.4, 0.1, 3.5], [0, 1, 2, 3])
        old = _sweep(3, "memory", [0.2, 3.5, 0.1, -0.2], [0, 1, 2, 3])

        def post(betas, obs, factory):
            b = factory(ctx, 1, betas={"memory": betas, "skill": 0.058, "queue": 0.033,
                                       "branch": 0.0})
            _run(b, {}, 2)
            b.update(3, obs)
            return b.carrier_mass()["memory"]

        for factory in (BE.make_exact_belief, BP.make_belief):
            grid = (0.0, 0.1, 0.314, 0.6)
            pf = [post(beta, fresh, factory) for beta in grid]
            po = [post(beta, old, factory) for beta in grid]
            for a, b in zip(pf, pf[1:]):
                self.assertGreater(a, b, f"{factory.__name__}: fresh alarm {pf}")
            drop_fresh = pf[0] - pf[-1]
            drop_old = abs(po[0] - po[-1])
            self.assertGreater(drop_fresh, 0.1)
            self.assertLess(drop_old, drop_fresh / 5, f"{factory.__name__}: {pf} {po}")
        # the drift share each carrier's items get is beta_k / (r_k + beta_k)
        m = BP.BeliefModel.for_context(ctx, 1, betas={"memory": 0.314})
        self.assertAlmostEqual(m.drift_share("memory"), 0.314 / 1.314)
        self.assertEqual(m.drift_share("skill"), 0.0)
        hidden = dataclasses.replace(C.PRIMARY, ingress_visible=False)
        mh = BP.BeliefModel.for_context(_ctx(world=hidden), 1, betas={"memory": 0.314})
        self.assertEqual(mh.drift_share("memory"), 0.0)     # drift is an ingress write (H8)

    # ---- DA1.l7 --------------------------------------------------------------------

    def test_belief_moves_after_commit_alarm_when_rho_positive(self):
        """DA1.l7: "execute at ; observe o t ; bt +1 ← Update(bt , at , o t , β)"

        In both provenance worlds the commit review updates the belief with strength
        rho: after a commit alarm at t, Pr[a marked patch entered the branch at t] rises
        with rho and, for rho > 0, above what it is with nothing bought; A7 adds the
        provenance score, which moves it even at rho = 0 (C1, O9)."""
        t = 5
        alarm = _commit(t, 3.0)

        def harmed(rho, obs, factory, world=C.PRIMARY):
            b = factory(_ctx(H=8, rho=rho, world=world), 4)
            _run(b, {}, t - 1)
            b.update(t, obs)
            return b.mass(lambda s: s["harmed"] & (s["sigma"] == t))

        for factory in (BE.make_exact_belief, BP.make_belief):
            quiet = harmed(0.5, _nothing(t), factory)
            moved = [harmed(r, alarm, factory) for r in C.RHO_GRID]
            for a, b in zip(moved, moved[1:]):
                self.assertLess(a, b, f"{factory.__name__}: {moved}")
            for r, v in zip(C.RHO_GRID, moved):
                if r > 0:
                    self.assertGreater(v, quiet, f"{factory.__name__}: rho {r}")
            a7 = dataclasses.replace(C.PRIMARY, provenance="A7")
            with_prov = harmed(0.0, _commit(t, 3.0, provenance=3.0), factory, a7)
            self.assertGreater(with_prov, moved[0] + 0.05, f"{factory.__name__}")
            # A0 has no provenance channel: a provenance field changes nothing there
            self.assertAlmostEqual(harmed(0.0, _commit(t, 3.0, provenance=3.0), factory),
                                   moved[0], places=12)

    def test_commit_alarm_is_uninformative_on_delegated_path_at_rho_zero_in_a0(self):
        """D2.artifact: "An audit that observes only the artifact cannot distinguish “this
        patch is the product of a poisoned skill” from “this patch is ordinary”, because the
        distinguishing evidence is the skill’s provenance."

        In A0 at rho = 0, the commit score leaves the odds of 'this task's patch is marked
        and came through a delegated carrier' against 'this task's patch is clean' exactly
        where they were: an alarm and a quiet score give the same odds.  A direct marked
        patch still moves (the commit review is not blind), and at rho > 0 the delegated
        odds move too."""
        t = 3

        def odds(rho, s, factory):
            b = factory(_ctx(H=8, rho=rho), 1)
            _run(b, {}, t - 1)
            b.update(t, _commit(t, s))
            st, marked, deleg, w = b.last
            dele = w[marked & deleg].sum()
            direct = w[marked & ~deleg].sum()
            clean = w[~marked].sum()
            self.assertGreater(dele, 0.0)
            self.assertGreater(direct, 0.0)
            return dele / clean, direct / clean

        for factory in (BE.make_exact_belief, BP.make_belief):
            d_hi, x_hi = odds(0.0, 3.5, factory)
            d_lo, x_lo = odds(0.0, -0.5, factory)
            self.assertAlmostEqual(d_hi / d_lo, 1.0, places=9, msg=factory.__name__)
            self.assertGreater(x_hi / x_lo, 10.0)
            d_hi, _ = odds(0.5, 3.5, factory)
            d_lo, _ = odds(0.5, -0.5, factory)
            self.assertGreater(d_hi / d_lo, 2.0)
        # f of Prop. 6.1 (T11's band): a commit-only policy in A0 at rho = 0 cannot inform
        # an attack seeded in a delegated carrier (2 of the 4 carriers at K_d = 2); at
        # rho > 0, or with every target buyable, no attack hypothesis is uninformable
        b0 = BP.make_belief(_ctx(H=8, rho=0.0), 1)
        self.assertAlmostEqual(b0.uninformable_share(("commit",)), 0.5, places=12)
        self.assertEqual(b0.uninformable_share(), 0.0)
        self.assertEqual(BP.make_belief(_ctx(H=8, rho=0.5), 1).uninformable_share(("commit",)),
                         0.0)
        self.assertEqual(b0.prior_p_attack(), BP.PRIOR_P_ATTACK)

    # ---- D5.1.delay ----------------------------------------------------------------

    def test_alarm_at_t_raises_earlier_insertions_with_later_triggers(self):
        """D5.1.delay: "an alarm at task t raises the posterior on insertions at t ′ < t with
        triggers at t ′′ > t"

        A memory sweep at t = 5 whose alarm is on a note written at task 2 raises the
        posterior mass of iota < 5 < sigma above both the prior (nothing bought) and a
        quiet sweep of the same items; the mass lands on iota = 2."""
        t = 5
        w = [0, 1, 2, 3, 4, 5]
        loud = _sweep(t, "memory", [0.1, -0.2, 3.5, 0.3, -0.1, 0.2], w)
        quiet = _sweep(t, "memory", [0.1, -0.2, 0.0, 0.3, -0.1, 0.2], w)
        for factory in (BE.make_exact_belief, BP.make_belief):
            got = {}
            for name, o in (("prior", _nothing(t)), ("quiet", quiet), ("loud", loud)):
                b = factory(_ctx(H=10), 4)
                _run(b, {}, t - 1)
                b.update(t, o)
                got[name] = (b.mass(_window(t)),
                             b.mass(lambda s: s["attacked"] & (s["iota"] == 2)
                                    & ((s["kmask"] & BP.MEMORY) != 0)))
            self.assertGreater(got["loud"][0], got["prior"][0] + 0.1, f"{factory.__name__} {got}")
            self.assertGreater(got["loud"][0], got["quiet"][0] + 0.1, f"{factory.__name__} {got}")
            self.assertGreater(got["loud"][1], 0.5, f"{factory.__name__} {got}")

    # ---- D7.beta -------------------------------------------------------------------

    def test_beta_estimated_online_from_clean_workflows(self):
        """D7.beta: "β is estimated online from clean workflows."

        O11: beta starts at the dev clean-run estimate and moves with the same-cell
        post-mortems toward the drift rate their clean audits show; alarms inside
        (k, [iota, sigma)) do not count; with no post-mortem the base is used; a
        post-mortem that carries no audits leaves beta at the base and says why."""
        from v3 import observe as O
        ctx0 = _ctx(H=10, rho=0.5, delta=4)
        cell = ctx0.cell
        base = BP.beta_base()
        self.assertEqual(set(base), set(CARRIERS))
        self.assertAlmostEqual(base["memory"], 0.3058, places=3)
        est0 = BP.estimate_beta((), cell)
        self.assertEqual(est0.betas, base)
        m0 = BP.BeliefModel.for_context(ctx0, None)
        self.assertEqual(m0.betas, base)

        det = cell.detector()
        tau = det.tau_det

        def world_pms(beta_true, n_wf, attack_alarms=False):
            rng = np.random.default_rng(seed_of(SEED, "beta", beta_true))
            pms = []
            psi_m = O.p_alarm(O.DRIFT_MATCH * det.d_prime, tau)
            phi = O.p_alarm(0.0, tau)
            for i in range(n_wf):
                audits, alarms = [], []
                for t in range(10):
                    n = 3
                    drift = rng.random() < beta_true
                    p_none = (1 - phi) ** (n - 1) * ((1 - psi_m) if drift else (1 - phi))
                    fired = rng.random() > p_none
                    inside = 2 <= t < 6
                    if attack_alarms and inside:
                        fired = True                       # the poison itself
                    audits.append((t, "memory", 1, n))
                    if fired:
                        alarms.append((t, "memory"))
                pms.append(PostMortemWithAudits(
                    cell_id=C.cell_id(cell), wf_id=f"wf{i}", order=i, seed=1, k=("memory",),
                    iota=2, sigma=6, harm=0.0, H=10, alarms=tuple(alarms),
                    audits=tuple(audits)))
            return pms

        few = BP.estimate_beta(world_pms(0.05, 3), cell).betas["memory"]
        many = BP.estimate_beta(world_pms(0.05, 400), cell).betas["memory"]
        self.assertLess(abs(many - 0.05), 0.03, many)
        self.assertLess(abs(many - 0.05), abs(few - 0.05) + 1e-9)
        self.assertLess(many, base["memory"])
        high = BP.estimate_beta(world_pms(0.6, 400), cell).betas["memory"]
        self.assertLess(abs(high - 0.6), 0.06, high)
        # alarms inside (k, [iota, sigma)) are the poison, not drift: they do not count
        att = BP.estimate_beta(world_pms(0.05, 400, attack_alarms=True), cell).betas["memory"]
        self.assertAlmostEqual(att, many, places=12)
        # the factory reads ctx.postmortems (O11)
        ctx = _ctx(H=10, rho=0.5, delta=4, postmortems=world_pms(0.05, 400))
        self.assertAlmostEqual(BP.make_belief(ctx, None).model.betas["memory"], many, places=12)
        # api.PostMortem has no audits: skipped with a reason, beta stays at the base
        plain = A.PostMortem(cell_id=C.cell_id(cell), wf_id="wf-plain", order=0, seed=1,
                             k=("memory",), iota=2, sigma=6, harm=0.0, H=10,
                             alarms=((0, "memory"),))
        est = BP.estimate_beta((plain,), cell)
        self.assertEqual(est.betas, base)
        self.assertTrue(any("audits" in n for n in est.notes))
        # another cell's post-mortem is not used (O11: same cell)
        other = dataclasses.replace(world_pms(0.6, 1)[0], cell_id="000000000000")
        self.assertEqual(BP.estimate_beta((other,), cell).betas, base)


if __name__ == "__main__":
    unittest.main()
