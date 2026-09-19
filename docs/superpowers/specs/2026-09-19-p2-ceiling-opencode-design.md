# P2 Ceiling OpenCode Runner Design

## Goal

Run the pre-registered five-instance ceiling arm through the same OpenCode
transport that was validated for the P2 control smoke, without changing the
arm's data or statistical role.

## Boundary

`spikes/p2_arms.py` will expose `run_ceiling()` and a `--run-ceiling` CLI
mode.  It constructs the existing `OpenCodePilotClient` through
`make_control_client()` and delegates all ceiling-arm execution to
`p2_run.run_p2(arm=p2_run.CEILING_ARM, ...)`.

The runner freezes the smoke-compatible protocol: `deepseek-v4.1-flash`,
the OpenCode base URL, `DEEPSEEK_API_KEY`, `SESSION_ID`, enabled thinking,
high reasoning effort, the pilot user agent, and the existing five-retry
policy for HTTP 5xx responses.  It uses the fixed pilot seed,
temperature zero, maximum 30 steps, and disables model fingerprinting so the
run creates no unrelated provider request.

## CLI and data safety

`--run-ceiling` writes to `--ceiling-out`, defaulting to
`spikes/p2-ceiling-raw.jsonl`.  The command refuses an existing destination
unless `--force` is supplied.  Its `--limit`, `--seeds`, and `--no-clone`
arguments have the same meanings as the control runner.

The existing `--ceiling` argument remains the report input path; it is not
repurposed as an execution destination.  Ceiling remains outside the primary
P2 statistic because `CEILING_ARM.in_statistic` is empty.

## Errors and evidence

Credential errors are refused before model work.  Non-5xx HTTP failures are
not retried; 5xx failures follow the frozen retry policy.  A terminal online
smoke row, including a structured refusal, is evidence that the runner and
its JSONL persistence path work.  One smoke row does not estimate the
ceiling advice effect.

## Tests

Offline tests will prove that `run_ceiling()` delegates to the frozen
`CEILING_ARM` with the supplied OpenCode client and fixed execution settings,
and that the CLI neither overwrites an existing destination nor routes its
arguments incorrectly.  After those tests pass, one online `--limit 1`
smoke run will use a fresh output file.

## Self-review

No arm composition, advice payload, scoring rule, or report statistic changes
are included.  The execution/output names are distinct, and every network
setting is inherited from the already-tested OpenCode client rather than
duplicated.
