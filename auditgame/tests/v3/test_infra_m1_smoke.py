"""Infrastructure: the M1 smoke (tools/v3_m1_smoke.py) is a dev-only tool (plan S6, S7)."""
import unittest

from tools import v3_m1_smoke as M1
from v3 import seal


class TestInfraM1Smoke(unittest.TestCase):

    def test_infra_m1_smoke_refuses_every_split_but_dev(self):
        """The seal: any split other than dev is refused before any work is done."""
        for split in ("eval", "primary", "secondary", "Eval", ""):
            with self.assertRaises(seal.SealedSplit, msg=split):
                M1.refuse_unless_dev(split)
            with self.assertRaises(seal.SealedSplit, msg=split):
                M1.main(["--split", split, "--workflows", "0"])
        M1.refuse_unless_dev("dev")

    def test_infra_m1_smoke_runs_one_dev_workflow(self):
        """One (rho, Delta, workflow) job runs every system on dev and returns records of
        split dev only, with the Oracle (+) harm-free."""
        out = M1.work((0.0, 4, 0, (0, 1)))
        self.assertTrue(out["rows"])
        self.assertEqual({r["split"] for r in out["rows"] + out["br"]}, {"dev"})
        self.assertEqual({r["policy"] for r in out["rows"]}, set(M1.SYSTEMS) | {M1.NONE})
        self.assertEqual(sum(r["harm"] for r in out["rows"] if r["policy"] == M1.ORACLE), 0)


if __name__ == "__main__":
    unittest.main()
