"""
GATE 1 -- INTEGRITY for the CARRIER SCORE REFERENCE TABLE generator.

Red here means reference/score_table.json is no longer the file
reference/gen_score_table.py produces -- and then every tau_sel a policy reads is
a number with no recipe behind it.

WHY THESE TESTS EXIST NOW.  The table gained d'-keyed rows (d0.0 .. d3.0) so the
d' sweep can calibrate tau_sel at the d' it is actually running.  Adding rows to a
FROZEN artifact is only safe if the addition cannot move the rows that were
already there, and "cannot" has to be checked, not argued: the per-setting RNG is
`random.Random(SEED ^ hash_name(name))`, so the claim is that each setting draws
from its OWN stream and never from a shared one.

FAST PATH, DELIBERATE.  A full regeneration is ~23 minutes (31 cells x 19 tables
x 800k samples), which no test suite can carry.  The whole generator IS run here,
with N_MAX cut to 1: n=0 returns a constant and consumes no draws, so n=1 is the
FIRST cell every setting's stream feeds and a truncated run is a faithful PREFIX
of the real one.  That costs ~17s and buys the real thing -- build() itself, all
19 tables, in their real order -- so a shared RNG, a reordered registry, a changed
seed, a changed M and a changed aggregation rule all land on these cells and all
show up here.  M is NOT reduced: reducing it would compare against numbers the
committed file does not contain.

WHAT THE FAST PATH GIVES UP.  Only the n = 0 / n = 1 prefix of each frozen table is
compared, so an edit deeper in a committed table is invisible here; the complete
pin is `gen_score_table.py --check`, at ~23 minutes.  Said again at the test.

Naming convention: test names are English and each name is the SENTENCE the test
protects; the thesis sentence it defends lives in the mandatory
`Thesis claim (vi):` docstring line.
"""
from __future__ import annotations
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

import dprime_sweep as S

_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _generator():
    """Load reference/gen_score_table.py by path -- reference/ is not a package."""
    spec = importlib.util.spec_from_file_location(
        "gen_score_table", _ROOT / "reference" / "gen_score_table.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GEN = _generator()


def _build_with_n_max(n_max: int) -> dict:
    """The real build(), truncated to n <= n_max.  M is untouched.

    A fresh module object each time, so the constant is never left patched on a
    module another test may import.
    """
    mod = _generator()
    mod.N_MAX = n_max
    return mod.build()


TABLE = json.loads((_ROOT / "reference" / "score_table.json").read_text(encoding="utf-8"))
LEGACY = ("weak", "mid", "strong")


class AddingRowsCannotMoveTheRowsAlreadyThere(unittest.TestCase):
    """The three declared settings are FROZEN.  Extending the generator is an
    ADDITIVE change or it is not allowed at all."""

    def test_each_frozen_setting_still_draws_from_its_own_name_keyed_stream(self):
        """The n=1 cell of weak/mid/strong must come back bit-for-bit from build().

        Thesis claim (vi): "phep do nay la CONG THEM -- khong lam xe dich bat ky
        con so da dong bang nao".

        This is the byte-identity acceptance criterion in test form, and it runs
        the EXTENDED build() -- all 19 tables, in the order the real run uses --
        so it sees what a hand-written per-setting comparison would not: one RNG
        shared across settings, or the d'-keyed rows moved ahead of the declared
        ones.  Compared against the COMMITTED file, not against a second run of
        the same code, so it survives a wholesale rewrite of the generator.

        WHAT THIS DOES NOT COVER, said here so nobody reads it as more than it
        is.  It pins the n = 0 / n = 1 PREFIX of each legacy table -- the first
        cells the stream feeds -- so a shared RNG, a reordered registry, a
        changed seed, a changed M and a changed aggregation rule all land on it.
        A hand-edit DEEPER in a frozen table (say at n = 15) passes here
        untouched.  The COMPLETE pin is `python3 reference/gen_score_table.py
        --check`, which rebuilds all 19 tables and compares every cell -- ~23
        minutes, which is why it cannot live in the suite.  This test is the
        fast tripwire, not the full check.
        """
        truncated = _build_with_n_max(1)
        for name in LEGACY:
            with self.subTest(setting=name):
                self.assertEqual(
                    json.dumps(truncated[name]["rows"][:2], sort_keys=True),
                    json.dumps(TABLE["tables"][name]["rows"][:2], sort_keys=True),
                    f"[{name}] the extended generator no longer reproduces the "
                    f"committed n=0/n=1 rows: the frozen table moved under what "
                    f"was supposed to be an additive change")

    def test_the_frozen_settings_keep_their_declared_psi_and_phi_pair(self):
        """weak/mid/strong stay keyed by (psi, phi), not by d'.

        Thesis claim (vi): "ba diem khai bao weak/mid/strong chep tu ban thao
        goc -- (0.75, 0.20), (0.85, 0.12), (0.92, 0.06)".

        The d'-keyed rows take d' as their input.  If that path ever swallowed
        the declared settings too, their phi would snap to 0.12 and `weak` and
        `strong` would silently become different detectors.
        """
        for name in LEGACY:
            psi, phi = GEN.SETTINGS[name]
            t = TABLE["tables"][name]
            with self.subTest(setting=name):
                self.assertEqual((t["psi"], t["phi"]), (psi, phi))
                dp, tau = GEN.d_prime_and_tau(psi, phi)
                self.assertEqual((t["d_prime"], t["tau_detector"]), (dp, tau))


class TheSweepGridHasItsOwnCalibratedRows(unittest.TestCase):
    """The reason the table was extended: tau_sel keyed by the SWEPT d'."""

    def test_the_table_carries_one_d_prime_keyed_row_for_every_point_of_the_sweep_grid(self):
        """Every grid point the sweep visits must have a table row of its own.

        Thesis claim (vi): "quet nay giu setting='mid' o moi d' ... la mot
        confound that o vung d' xa 2,211" -- go confound bang cach sinh bang
        theo d' cho DUNG cac diem cua luoi.

        A missing name is not a soft failure: scoring.tau_sel is a dict lookup and
        the sweep would die mid-run with a KeyError.
        """
        for dp in S.GRID:
            name = GEN.sweep_setting_name(dp)
            with self.subTest(d_prime=dp):
                self.assertIn(name, TABLE["tables"],
                              f"no tau_sel row calibrated at d'={dp}")

    def test_only_d_prime_moves_across_the_d_prime_keyed_rows(self):
        """phi is FIXED at 0.12 on every d'-keyed row, exactly as the sweep is.

        Thesis claim (vi): "moi diem tren duong cong co CUNG MOT ti le bao dong
        gia" -- neu phi troi theo d' thi hang tau_sel moi lai dua vao mot chieu
        thu hai va khong con go duoc confound nao ca.
        """
        phis, taus = set(), set()
        for dp in S.GRID:
            t = TABLE["tables"][GEN.sweep_setting_name(dp)]
            phis.add(t["phi"])
            taus.add(t["tau_detector"])
            with self.subTest(d_prime=dp):
                self.assertAlmostEqual(t["d_prime"], dp, places=12,
                                       msg="a d'-keyed row is not at its own d'")
        self.assertEqual(phis, {GEN.SWEEP_PHI},
                         f"phi moved across the d'-keyed rows: {sorted(phis)}")
        self.assertEqual(len(taus), 1,
                         "tau_detector moved across the d'-keyed rows")

    def test_the_table_gained_the_sweep_grid_and_nothing_else(self):
        """Exactly 3 + 16 tables: no stray name, no silently dropped setting.

        Thesis claim (vi): "file nhan DUNG 16 bang moi" -- mot ten thua la mot
        phep do khong ai yeu cau va khong ai tai lap.
        """
        expected = set(LEGACY) | {GEN.sweep_setting_name(dp) for dp in S.GRID}
        self.assertEqual(set(TABLE["tables"]), expected)


class RegeneratingTheFrozenTableIsDeliberate(unittest.TestCase):
    """A plain `python3 gen_score_table.py` must not silently replace the artifact.

    score_table.json is FROZEN and three consumers read it.  An unguarded write
    also poisons the verification that is supposed to catch it: --check compares a
    fresh build against the file on disk, so running the generator first and
    --check second compares the file against itself and prints MATCH whatever the
    generator did.  The guard has to refuse BEFORE the build, not after: the build
    is ~23 minutes and a refusal that arrives afterwards has already burned them.
    """

    #: 31 rows so main()'s summary print (n = 0..30) has cells to read; the numbers
    #: are irrelevant here -- what is under test is WHETHER the file is written.
    STUB_ROWS = [dict(n=n, mean_p=0.1, se_mean_p=0.0,
                      tau_sel={str(k): 0.1 for k in range(1, 5)},
                      mean_cubic=0.0, se_cubic=0.0) for n in range(31)]

    def _stubbed(self, out: pathlib.Path):
        """A generator whose OUT is a temp file and whose build() is counted.

        build() is the 23-minute part, so it is replaced -- and the replacement
        RECORDS ITS CALLS, which is how "refused before building" is asserted
        rather than assumed.
        """
        mod = _generator()
        mod.OUT = out
        builds = []

        def stub_build(progress=None):
            builds.append(1)
            return {"mid": dict(psi=0.85, phi=0.12, d_prime=1.0, tau_detector=1.0,
                                var_lambda=1.0, bound_coefficient_C=1.0,
                                n_min_bound_useful=1.0, rows=self.STUB_ROWS)}

        mod.build = stub_build
        return mod, builds

    @staticmethod
    def _run(mod, argv):
        """main() with a controlled argv, its output swallowed."""
        saved = sys.argv
        sys.argv = ["gen_score_table.py", *argv]
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                return mod.main()
        finally:
            sys.argv = saved

    def test_a_plain_run_refuses_to_overwrite_an_existing_table(self):
        """The frozen file survives an accidental `python3 gen_score_table.py`.

        Thesis claim (vi): "KHONG sua tay. Sua script roi sinh lai" -- va cung
        KHONG sinh lai de len mot artifact dong bang chi vi go nham mot lenh.
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "score_table.json"
            out.write_text("FROZEN", encoding="utf-8")
            mod, builds = self._stubbed(out)
            rc = self._run(mod, [])
            self.assertNotEqual(rc, 0, "an unguarded run reported success")
            self.assertEqual(out.read_text(encoding="utf-8"), "FROZEN",
                             "the existing table was overwritten by a plain run")
            self.assertEqual(builds, [],
                             "the refusal arrived AFTER the 23-minute build")

    def test_the_explicit_flag_still_regenerates_the_table(self):
        """The regeneration workflow stays possible -- it just has to be asked for.

        Thesis claim (vi): "sinh lai bang chinh script, khong sua tay".
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "score_table.json"
            out.write_text("FROZEN", encoding="utf-8")
            mod, builds = self._stubbed(out)
            self.assertEqual(self._run(mod, ["--force"]), 0)
            self.assertEqual(builds, [1])
            self.assertIn("provenance", json.loads(out.read_text(encoding="utf-8")))

    def test_check_needs_no_flag_and_still_writes_nothing(self):
        """--check is the non-destructive verification and stays untouched.

        Thesis claim (vi): "--check sinh lai roi SO SANH, khong ghi gi".
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "score_table.json"
            mod, _ = self._stubbed(out)
            self.assertEqual(self._run(mod, ["--force"]), 0)
            written = out.read_bytes()
            mod, builds = self._stubbed(out)
            self.assertEqual(self._run(mod, ["--check"]), 0,
                             "--check no longer matches the file it just wrote")
            self.assertEqual(out.read_bytes(), written, "--check wrote to the file")
            self.assertEqual(builds, [1], "--check did not rebuild before comparing")


if __name__ == "__main__":
    unittest.main()
