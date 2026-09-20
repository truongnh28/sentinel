# P2 Ceiling OpenCode Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, smoke-compatible command that executes the frozen P2 ceiling arm through OpenCode.

**Architecture:** Keep OpenCode wire behavior in `p2_arms.OpenCodePilotClient`. Add a thin `run_ceiling()` adapter in the same module that creates that client and delegates ceiling semantics, corpus validation, advice loading, persistence, and classification to `p2_run.run_p2(CEILING_ARM)`.

**Tech Stack:** Python 3 standard library, `unittest`, existing `p2_arms` and `p2_run` runners.

## Global Constraints

- Reuse `OpenCodePilotClient`; do not duplicate headers, request body, or HTTP retry code.
- Freeze `deepseek-v4.1-flash`, `CONTROL_BASE_URL`, `CONTROL_SEEDS`, temperature `0.0`, and `max_steps=30`.
- Use `fingerprint=False` so the ceiling smoke makes no extra provider request.
- Preserve `--ceiling` as report input; execution output is `--ceiling-out`.
- Refuse an existing destination unless `--force` is explicit.
- Do not run the online smoke until offline tests are green.

---

### Task 1: Test and implement the ceiling adapter

**Files:**

- Modify: `auditgame/tests/gate1_integrity/test_p2_arms.py`
- Modify: `auditgame/spikes/p2_arms.py`

**Interfaces:**

- Consumes: `p2_run.run_p2(*, arm, out_path, limit, seeds, client, repos, rows, no_clone, fingerprint, model, temperature, max_steps, on_row)`.
- Produces: `run_ceiling(*, out_path=DEFAULT_CEILING_OUT, limit=None, seeds=CONTROL_SEEDS, client=None, repos=None, rows=None, no_clone=False, model=CONTROL_MODEL, base_url=CONTROL_BASE_URL, temperature=CONTROL_TEMPERATURE, max_steps=CONTROL_MAX_STEPS, on_row=None) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_run_ceiling_delegates_to_frozen_arm_with_injected_client -v`

Expected: FAIL because `p2_arms.run_ceiling` is undefined.

- [ ] **Step 3: Write minimal implementation**

```python
def run_ceiling(*, out_path=DEFAULT_CEILING_OUT, limit=None,
                seeds=CONTROL_SEEDS, client=None, repos=None, rows=None,
                no_clone=False, model=CONTROL_MODEL, base_url=CONTROL_BASE_URL,
                temperature=CONTROL_TEMPERATURE, max_steps=CONTROL_MAX_STEPS,
                on_row=None):
    client = make_control_client(model=model, base_url=base_url) if client is None else client
    return p2_run.run_p2(
        arm=p2_run.CEILING_ARM, out_path=out_path, limit=limit, seeds=tuple(seeds),
        client=client, repos=repos, rows=rows, no_clone=no_clone, model=model,
        temperature=temperature, max_steps=max_steps, fingerprint=False, on_row=on_row,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_run_ceiling_delegates_to_frozen_arm_with_injected_client -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add auditgame/spikes/p2_arms.py auditgame/tests/gate1_integrity/test_p2_arms.py
git commit -m "feat(p2): add ceiling OpenCode adapter"
```

### Task 2: Test and implement safe ceiling CLI routing

**Files:**

- Modify: `auditgame/tests/gate1_integrity/test_p2_arms.py`
- Modify: `auditgame/spikes/p2_arms.py`

**Interfaces:**

- Consumes: `run_ceiling(**kwargs)` from Task 1 and `p2_run.refuse_to_overwrite(path, force)`.
- Produces: CLI `--run-ceiling --ceiling-out PATH [--limit N --seeds CSV --no-clone --force]`.

- [ ] **Step 1: Write the failing tests**

```python
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
    self.out.write_text('{"instance_id":"paid"}\\n', encoding="utf-8")
    with mock.patch.object(p2_arms, "run_ceiling") as run:
        self.assertEqual(p2_arms.main(["--run-ceiling", "--ceiling-out", str(self.out)]), 2)
    run.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_ceiling_cli_uses_the_frozen_opencode_configuration tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_ceiling_cli_refuses_to_overwrite_paid_output -v`

Expected: FAIL because `--run-ceiling` and `--ceiling-out` are unrecognized.

- [ ] **Step 3: Write minimal implementation**

Add `--run-ceiling` and `--ceiling-out`. Before constructing a client, parse `--seeds` and call `p2_run.refuse_to_overwrite(a.ceiling_out, force=a.force)`. Call `run_ceiling` with the frozen settings and `p2_run._print_row`; print the row/classified/refused summary. Catch the same preflight credential/refusal errors as `--run-control` and return `2`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_ceiling_cli_uses_the_frozen_opencode_configuration tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_ceiling_cli_refuses_to_overwrite_paid_output -v`

Expected: PASS.

- [ ] **Step 5: Run regression suite**

Run: `python3 -m unittest tests.gate1_integrity.test_p2_arms -v`

Expected: PASS with no regressions in the control runner or report logic.

- [ ] **Step 6: Commit**

```bash
git add auditgame/spikes/p2_arms.py auditgame/tests/gate1_integrity/test_p2_arms.py
git commit -m "feat(p2): expose safe ceiling execution CLI"
```

### Task 3: Execute and inspect online ceiling smoke

**Files:**

- Create: `auditgame/spikes/p2-ceiling-smoke.jsonl`

**Interfaces:**

- Consumes: successful Task 2 CLI and `.env` credentials loaded by the existing client.
- Produces: a fresh one-instance JSONL file with one terminal row and one summary row.

- [ ] **Step 1: Verify destination does not exist**

Run: `test ! -e spikes/p2-ceiling-smoke.jsonl`

Expected: exit 0.

- [ ] **Step 2: Execute the online smoke**

Run: `set -a; source ../.env; set +a; python3 spikes/p2_arms.py --run-ceiling --limit 1 --no-clone --ceiling-out spikes/p2-ceiling-smoke.jsonl`

Expected: one terminal row and a summary; a structured refusal remains valid transport evidence.

- [ ] **Step 3: Inspect only non-secret result fields**

Run: `python3 -c "import json, pathlib; p=pathlib.Path('spikes/p2-ceiling-smoke.jsonl'); rows=[json.loads(x) for x in p.read_text().splitlines()]; print([{k:r.get(k) for k in ('instance_id','arm','tier','mode','reason','tokens_in','tokens_out')} for r in rows])"`

Expected: exactly one non-summary `ceiling` row and one `summary` row; no credential values are printed.
