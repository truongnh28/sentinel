# P2 OpenCode Hard Deadline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound each OpenCode request so a live but unfinished response becomes a recorded retry/refusal instead of an indefinite experiment stall.

**Architecture:** Add a scoped POSIX signal deadline around the existing post call in `OpenCodePilotClient`; reuse the existing five-attempt loop and JSONL refusal behavior. A clean rerun consumes a fresh output file; archived partial rows are never merged.

**Tech Stack:** Python standard library `signal`, `contextlib`, `unittest`, existing OpenCode client.

## Global Constraints

- Hard deadline is 600 seconds and restores prior signal state in `finally`.
- Deadline expiry is retryable with 5xx; 4xx remains fail-fast.
- No change to experiment endpoint, payload, model, seed, advice, scoring, or arm membership.

---

### Task 1: Deadline helper and retry behavior

**Files:**

- Modify: `auditgame/tests/gate1_integrity/test_p2_arms.py`
- Modify: `auditgame/spikes/p2_arms.py`

**Interfaces:**

- Produces: `ControlRequestDeadlineExceeded(TimeoutError)` and a scoped deadline used by `OpenCodePilotClient.complete`.

- [ ] **Step 1: Write a failing retry test**

```python
def test_deadline_expiry_retries_then_succeeds(self):
    outcomes = [p2_arms.ControlRequestDeadlineExceeded("600s"),
                {"choices": [{"message": {"content": "ok"}}]}]
    sleeps = []
    with mock.patch.object(p2_arms.agent_llm, "post", side_effect=outcomes):
        reply = p2_arms.OpenCodePilotClient(api_key="key", session_id="session",
            sleep=sleeps.append).complete([{"role": "user", "content": "x"}])
    self.assertEqual(reply.text, "ok")
    self.assertEqual(sleeps, [1])
```

- [ ] **Step 2: Run the test and observe RED**

Run: `python3 -m unittest tests.gate1_integrity.test_p2_arms.TestControlArmRunner.test_deadline_expiry_retries_then_succeeds -v`

Expected: FAIL because deadline expiry is not retryable.

- [ ] **Step 3: Implement minimal behavior**

Add a signal-scoped context manager that installs an alarm handler raising `ControlRequestDeadlineExceeded`, preserves/restores the prior handler and timer, and wraps `agent_llm.post`. Extend the existing retry branch to retry that exception under `CONTROL_RETRY_DELAYS` and exhaust as `ControlRetriesExhausted`.

- [ ] **Step 4: Verify GREEN**

Run the Task 1 test again; expected PASS.

### Task 2: Regression verification and clean rerun

**Files:**

- Create: `auditgame/spikes/p2-ceiling-raw.jsonl`

- [ ] **Step 1: Run P2 regression suite**

Run: `python3 -m unittest discover -s tests -p 'test_p2*.py' -v`

Expected: PASS.

- [ ] **Step 2: Commit production change and tests**

Run: `git add auditgame/spikes/p2_arms.py auditgame/tests/gate1_integrity/test_p2_arms.py && git commit -m "fix(p2): bound OpenCode request duration"`

- [ ] **Step 3: Fresh full run after confirming output absent**

Run: `test ! -e spikes/p2-ceiling-raw.jsonl && set -a; source ../.env; set +a; python3 spikes/p2_arms.py --run-ceiling --no-clone --ceiling-out spikes/p2-ceiling-raw.jsonl`

Expected: five parseable instance rows and one summary row, with `REFUSED` allowed only as a structured row.
