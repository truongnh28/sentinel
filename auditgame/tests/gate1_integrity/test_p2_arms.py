"""
test_p2_arms.py -- Gate 1 tests for P2 three-arm coordination and readout logic.
"""
import io
import json
import pathlib
import tempfile
import types
import unittest
import urllib.error
from unittest import mock

from spikes import p2_arms


class TestP2Arms(unittest.TestCase):
    def test_empty_store_has_no_items(self):
        store = p2_arms.empty_store()
        self.assertEqual(len(store.live()), 0)

    def test_summarize_arm_rows(self):
        rows = [
            {"mode": "A", "instance_id": "i1", "tokens_in": 100, "tokens_out": 20},
            {"mode": "A", "instance_id": "i2", "tokens_in": 200, "tokens_out": 30},
            {"mode": "REFUSED", "instance_id": "i3", "tokens_in": 50, "tokens_out": 10},
            {"mode": "VACUOUS_ANCHOR", "instance_id": "i4", "tokens_in": 150, "tokens_out": 25},
            {"type": "summary", "model": "test"},
        ]
        s = p2_arms.summarize_arm_rows(rows, arm_name="test_arm", model_name="test_model")
        self.assertEqual(s.instances, 4)
        self.assertEqual(s.classified, 2)
        self.assertEqual(s.refused, 1)
        self.assertEqual(s.vacuous_anchor, 1)
        self.assertEqual(s.patch_produced, 3)
        self.assertAlmostEqual(s.patch_rate, 0.75)
        self.assertEqual(s.adopted, 0)
        self.assertAlmostEqual(s.adoption_rate, 0.0)
        self.assertEqual(s.tokens_in, 500)
        self.assertEqual(s.tokens_out, 85)

    def test_compare_arms_delta(self):
        main_rows = [
            {"mode": "A", "instance_id": "i1"},
            {"mode": "REFUSED", "instance_id": "i2"},
        ]  # patch_rate = 1/2 = 0.5
        ctrl_rows = [
            {"mode": "A", "instance_id": "i1"},
            {"mode": "A", "instance_id": "i2"},
        ]  # patch_rate = 2/2 = 1.0
        cmp_res = p2_arms.compare_arms(main_rows, control_rows=ctrl_rows)
        self.assertIsNotNone(cmp_res["delta_patch_rate"])
        self.assertAlmostEqual(cmp_res["delta_patch_rate"], 0.5)

    def test_hypothesis_i_length_bottleneck(self):
        main_rows = [{"mode": "A", "instance_id": "i1"}]  # adopted = 0
        ceil_rows = [{"mode": "B", "instance_id": "i1"}]  # adopted = 1
        cmp_res = p2_arms.compare_arms(main_rows, ceiling_rows=ceil_rows)
        readout = cmp_res["readout"]
        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_LENGTH_BOTTLENECK)
        self.assertEqual(readout["code"], "(i)")
        self.assertEqual(readout["section"], "Model section")

    def test_hypothesis_ii_memory_ignored(self):
        # High patch rate (e.g. 50%), both required comparison arms present,
        # but 0 adoptions at both feasible and ceiling advice lengths.
        main_rows = [
            {"mode": "A", "instance_id": f"i{k}"} for k in range(5)
        ] + [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(5)
        ]
        ctrl_rows = [
            {"mode": "A", "instance_id": f"i{k}"} for k in range(5)
        ] + [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(5)
        ]
        ceil_rows = [
            {"mode": "A", "instance_id": f"c{k}"} for k in range(3)
        ]
        cmp_res = p2_arms.compare_arms(
            main_rows, control_rows=ctrl_rows, ceiling_rows=ceil_rows)
        readout = cmp_res["readout"]
        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_MEMORY_IGNORED)
        self.assertEqual(readout["code"], "(ii)")
        self.assertIn("Threats", readout["section"])

    def test_missing_required_arm_is_undecided(self):
        main_rows = [
            {"mode": "A", "instance_id": f"i{k}"} for k in range(5)
        ]
        ceil_rows = [
            {"mode": "A", "instance_id": f"c{k}"} for k in range(3)
        ]

        readout = p2_arms.compare_arms(
            main_rows, ceiling_rows=ceil_rows)["readout"]

        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_UNDECIDED)
        self.assertEqual(readout["section"], "(chưa vào bài)")
        self.assertIn("control", readout["rationale"])

    def test_hypothesis_iii_task_unsolved(self):
        # Low patch rate (< 20%)
        main_rows = [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(10)
        ] + [
            {"mode": "A", "instance_id": "i1"}
        ]  # 1/11 = 9.1%
        ctrl_rows = [
            {"mode": "REFUSED", "instance_id": f"r{k}"} for k in range(10)
        ] + [{"mode": "A", "instance_id": "i1"}]
        cmp_res = p2_arms.compare_arms(main_rows, control_rows=ctrl_rows)
        readout = cmp_res["readout"]
        self.assertEqual(readout["hypothesis"], p2_arms.HYPOTHESIS_TASK_UNSOLVED)
        self.assertEqual(readout["code"], "(iii)")
        self.assertEqual(readout["section"], "Limitations")

    def test_render_markdown_report_contains_table_and_readout(self):
        main_rows = [
            {"mode": "A", "instance_id": "i1", "tokens_in": 100, "tokens_out": 20, "proxy": True, "hidden": True, "patch": "diff", "tier": "high"},
            {"mode": "REFUSED", "instance_id": "i2", "tokens_in": 50, "tokens_out": 10, "proxy": None, "hidden": None, "patch": "", "tier": "low", "reason": "empty"},
        ]
        cmp_res = p2_arms.compare_arms(main_rows)
        cmp_res["main_rows"] = main_rows
        md = p2_arms.render_markdown_report(cmp_res)
        self.assertIn("# P2 — Báo Cáo Ba Arm", md)
        self.assertIn("| Arm | Model | Mục đích |", md)
        self.assertIn("### Phán quyết:", md)

    def test_control_must_cover_the_same_instances_as_main(self):
        main_rows = [{"mode": "A", "instance_id": "i1"}]
        ctrl_rows = [{"mode": "A", "instance_id": "different"}]

        with self.assertRaises(p2_arms.PairingRefused) as e:
            p2_arms.compare_arms(main_rows, control_rows=ctrl_rows)

        self.assertIn("paired instance", str(e.exception))

    def test_control_must_use_the_same_model_temperature_and_seed(self):
        main_rows = [{
            "mode": "A", "instance_id": "i1", "model": "m",
            "temperature": 0.0, "seed": 7,
        }]
        ctrl_rows = [{
            "mode": "A", "instance_id": "i1", "model": "other",
            "temperature": 0.0, "seed": 7,
        }]

        with self.assertRaises(p2_arms.PairingRefused) as e:
            p2_arms.compare_arms(main_rows, control_rows=ctrl_rows)

        self.assertIn("model", str(e.exception))


class TestControlArmRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name) / "control.jsonl"

    def test_writes_instance_major_rows_then_summary(self):
        selected = list(p2_arms.CONTROL_TESTS[:2])
        corpus = {
            t.instance_id: {
                "instance_id": t.instance_id,
                "repo": t.repo,
                "base_commit": "0" * 40,
                "problem_statement": "test",
            }
            for t in selected
        }

        class Repos:
            def __init__(self):
                self.preflighted = None

            def preflight(self, tasks):
                self.preflighted = [t.task_id for t in tasks]

        repos = Repos()
        calls = []

        def fake_instance(test, instance, **kw):
            calls.append((test.instance_id, kw["seed"]))
            return {
                "instance_id": test.instance_id,
                "arm": "control",
                "tier": "control",
                "mode": "A",
                "model": kw["model"],
                "seed": kw["seed"],
                "tokens_in": 10,
                "tokens_out": 2,
            }

        with mock.patch.object(p2_arms, "run_control_instance", fake_instance):
            result = p2_arms.run_control(
                out_path=self.out,
                limit=2,
                seeds=(11, 12),
                rows=corpus,
                client=object(),
                repos=repos,
                model="paired-model",
            )

        self.assertEqual(calls, [
            (selected[0].instance_id, 11),
            (selected[0].instance_id, 12),
            (selected[1].instance_id, 11),
            (selected[1].instance_id, 12),
        ])
        self.assertEqual(repos.preflighted, [t.instance_id for t in selected])
        written = [json.loads(line) for line in self.out.read_text().splitlines()]
        self.assertEqual(written[:-1], result["rows"])
        self.assertEqual(written[-1]["type"], "summary")
        self.assertEqual(written[-1]["arm"], "control")
        self.assertEqual(written[-1]["replicates"], [11, 12])
        self.assertEqual(written[-1]["rows"], 4)

    def test_control_instance_reaches_agent_with_no_planted_item(self):
        test = p2_arms.CONTROL_TESTS[0]
        instance = {
            "instance_id": test.instance_id,
            "repo": test.repo,
            "base_commit": "0" * 40,
            "problem_statement": "test",
        }
        observed = {}

        class Loop:
            def __init__(self, **kw):
                observed["loop"] = kw

            def run(self, t, task, store, seed, marker, **kw):
                observed["live_items"] = list(store.live())
                observed["seed"] = seed
                return types.SimpleNamespace(
                    tokens_in=10, tokens_out=2, exchanges=())

        class Repos:
            def prepare(self, task):
                return pathlib.Path(self_dir)

            def patch(self, task, repo_path):
                return p2_arms.fixtures.gold(test.instance_id)

        self_dir = self.tmp.name
        with mock.patch.object(p2_arms.agent_llm, "ReActLoop", Loop):
            row = p2_arms.run_control_instance(
                test,
                instance,
                client=object(),
                repos=Repos(),
                seed=20260917,
                model=p2_arms.CONTROL_MODEL,
            )

        self.assertEqual(observed["live_items"], [])
        self.assertEqual(row["arm"], "control")
        self.assertEqual(row["advice_chars"], 0)
        self.assertEqual(row["advice_tokens"], 0)
        self.assertEqual(row["mode"], "A")

    def test_preflight_refusal_happens_before_output_or_model_call(self):
        selected = list(p2_arms.CONTROL_TESTS[:1])
        corpus = {
            t.instance_id: {
                "instance_id": t.instance_id,
                "repo": t.repo,
                "base_commit": "0" * 40,
                "problem_statement": "test",
            }
            for t in selected
        }

        class RefusingRepos:
            def preflight(self, tasks):
                raise p2_arms.p2_run.RepoRefused("wrong checkout")

        with self.assertRaises(p2_arms.p2_run.RepoRefused):
            p2_arms.run_control(
                out_path=self.out,
                limit=1,
                seeds=(20260917,),
                rows=corpus,
                client=object(),
                repos=RefusingRepos(),
            )

        self.assertFalse(self.out.exists())

    def test_cli_uses_the_frozen_pilot_pairing(self):
        captured = {}

        def fake_run(**kw):
            captured.update(kw)
            return {
                "rows": [],
                "summary": {"rows": 0, "classified": 0, "refused": 0},
                "out": str(self.out),
            }

        with mock.patch.object(p2_arms, "run_control", fake_run):
            code = p2_arms.main([
                "--run-control",
                "--control-out", str(self.out),
            ])

        self.assertEqual(code, 0)
        self.assertEqual(captured["seeds"], p2_arms.CONTROL_SEEDS)
        self.assertEqual(captured["model"], p2_arms.CONTROL_MODEL)
        self.assertEqual(
            captured.get("base_url"),
            "https://opencode.ai/zen/go/v1",
        )
        self.assertEqual(captured["temperature"], p2_arms.CONTROL_TEMPERATURE)
        self.assertEqual(captured["max_steps"], p2_arms.CONTROL_MAX_STEPS)
        self.assertFalse(captured["fingerprint"])

    def test_frozen_control_configuration_matches_pilot_on_disk(self):
        rows = p2_arms.load_rows_from_file(p2_arms.DEFAULT_PILOT)
        measured = [r for r in rows if r.get("type") != "summary"]

        self.assertEqual(
            {r["instance_id"] for r in measured},
            {t.instance_id for t in p2_arms.CONTROL_TESTS},
        )
        self.assertEqual({r["model"] for r in measured}, {p2_arms.CONTROL_MODEL})
        self.assertEqual(
            {r["temperature"] for r in measured},
            {p2_arms.CONTROL_TEMPERATURE},
        )
        self.assertEqual({r["seed"] for r in measured}, set(p2_arms.CONTROL_SEEDS))

    def test_opencode_client_sends_the_pilot_headers_and_reasoning_body(self):
        captured = {}

        def fake_post(url, body, headers, timeout):
            captured.update(
                url=url, body=body, headers=headers, timeout=timeout)
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

        client = p2_arms.OpenCodePilotClient(
            api_key="secret-key",
            session_id="secret-session",
        )
        with mock.patch.object(p2_arms.agent_llm, "post", fake_post):
            reply = client.complete(
                [{"role": "user", "content": "hello"}],
                model=p2_arms.CONTROL_MODEL,
                temperature=0.0,
            )

        self.assertEqual(reply.text, "ok")
        self.assertEqual(
            captured["url"],
            "https://opencode.ai/zen/go/v1/chat/completions",
        )
        self.assertEqual(
            captured["headers"]["x-opencode-session"],
            "secret-session",
        )
        self.assertEqual(captured["headers"].get("User-Agent"), "auditgame-p2/1.0")
        self.assertEqual(captured["body"]["thinking"], {"type": "enabled"})
        self.assertEqual(captured["body"]["reasoning_effort"], "high")
        self.assertIs(captured["body"]["stream"], False)

    def test_opencode_client_refuses_when_session_header_is_missing(self):
        with mock.patch.dict(
                "os.environ",
                {"DEEPSEEK_API_KEY": "secret-key"},
                clear=True):
            with self.assertRaises(p2_arms.ControlCredentialRefused) as e:
                p2_arms.make_control_client()

        self.assertIn("SESSION_ID", str(e.exception))

    @staticmethod
    def http_error(code):
        return urllib.error.HTTPError(
            "https://opencode.invalid/chat/completions",
            code,
            "test failure",
            hdrs=None,
            fp=io.BytesIO(),
        )

    def test_retries_5xx_then_returns_success(self):
        outcomes = [
            self.http_error(500),
            self.http_error(503),
            {"choices": [{"message": {"content": "ok"}}]},
        ]
        calls = []
        sleeps = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        client = p2_arms.OpenCodePilotClient(
            api_key="key", session_id="session", sleep=sleeps.append)
        with mock.patch.object(p2_arms.agent_llm, "post", fake_post):
            reply = client.complete([{"role": "user", "content": "hello"}])

        self.assertEqual(reply.text, "ok")
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [1, 2])
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(calls[1], calls[2])

    def test_six_5xx_attempts_exhaust_with_declared_backoff(self):
        calls = []
        sleeps = []

        def always_500(*args, **kwargs):
            calls.append((args, kwargs))
            raise self.http_error(500)

        client = p2_arms.OpenCodePilotClient(
            api_key="key", session_id="session", sleep=sleeps.append)
        with mock.patch.object(p2_arms.agent_llm, "post", always_500):
            with self.assertRaises(p2_arms.ControlRetriesExhausted) as e:
                client.complete([{"role": "user", "content": "hello"}])

        self.assertEqual(len(calls), 6)
        self.assertEqual(sleeps, [1, 2, 4, 8, 16])
        self.assertIn("6 attempts", str(e.exception))
        self.assertIn("HTTP 500", str(e.exception))

    def test_4xx_is_not_retried(self):
        calls = []
        sleeps = []

        def forbidden(*args, **kwargs):
            calls.append((args, kwargs))
            raise self.http_error(403)

        client = p2_arms.OpenCodePilotClient(
            api_key="key", session_id="session", sleep=sleeps.append)
        with mock.patch.object(p2_arms.agent_llm, "post", forbidden):
            with self.assertRaises(urllib.error.HTTPError) as e:
                client.complete([{"role": "user", "content": "hello"}])

        self.assertEqual(e.exception.code, 403)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sleeps, [])

    def test_cli_refuses_to_overwrite_a_paid_control_run(self):
        self.out.write_text('{"instance_id":"paid"}\n', encoding="utf-8")
        with mock.patch.object(p2_arms, "run_control") as run:
            code = p2_arms.main([
                "--run-control",
                "--control-out", str(self.out),
            ])

        self.assertEqual(code, 2)
        run.assert_not_called()
        self.assertIn("paid", self.out.read_text(encoding="utf-8"))

    def test_run_ceiling_delegates_to_frozen_arm_with_injected_client(self):
        client = object()
        captured = {}

        def fake_run_p2(**kwargs):
            captured.update(kwargs)
            return {"rows": [], "summary": {}, "out": str(self.out)}

        with mock.patch.object(p2_arms.p2_run, "run_p2", fake_run_p2):
            p2_arms.run_ceiling(out_path=self.out, limit=1, seeds=(20260917,),
                                client=client, repos=object(), rows={}, no_clone=True)

        self.assertIs(captured["arm"], p2_arms.p2_run.CEILING_ARM)
        self.assertIs(captured["client"], client)
        self.assertEqual(captured["seeds"], (20260917,))
        self.assertEqual(captured["model"], p2_arms.CONTROL_MODEL)
        self.assertEqual(captured["temperature"], p2_arms.CONTROL_TEMPERATURE)
        self.assertEqual(captured["max_steps"], p2_arms.CONTROL_MAX_STEPS)
        self.assertFalse(captured["fingerprint"])

    def test_ceiling_cli_uses_the_frozen_opencode_configuration(self):
        captured = {}
        with mock.patch.object(p2_arms, "run_ceiling", side_effect=lambda **kw: captured.update(kw) or {
            "rows": [], "summary": {"rows": 0, "classified": 0, "refused": 0}, "out": str(self.out)}):
            self.assertEqual(p2_arms.main(["--run-ceiling", "--ceiling-out", str(self.out)]), 0)
        self.assertEqual(captured["seeds"], p2_arms.CONTROL_SEEDS)
        self.assertEqual(captured["model"], p2_arms.CONTROL_MODEL)
        self.assertEqual(captured["base_url"], p2_arms.CONTROL_BASE_URL)
        self.assertFalse(captured["fingerprint"])

    def test_ceiling_cli_refuses_to_overwrite_paid_output(self):
        self.out.write_text('{"instance_id":"paid"}\n', encoding="utf-8")
        with mock.patch.object(p2_arms, "run_ceiling") as run:
            self.assertEqual(p2_arms.main(["--run-ceiling", "--ceiling-out", str(self.out)]), 2)
        run.assert_not_called()




if __name__ == "__main__":
    unittest.main()
