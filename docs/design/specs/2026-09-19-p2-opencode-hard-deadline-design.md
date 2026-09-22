# P2 OpenCode Hard Request Deadline Design

## Incident and goal

The ceiling full run reached three durable rows, then waited indefinitely in an SSL read while its TCP connection remained established. `urllib`'s socket timeout is not a total-response deadline when the peer continues to dribble bytes. The experiment runner must convert that state into a recorded, bounded transport failure rather than hold a paid run forever.

The partial output is archived separately and will not be combined with a later run. A new full run starts on a fresh JSONL file, so every result row uses one transport policy.

## Design

`OpenCodePilotClient` will enforce a 600-second wall-clock deadline around each `agent_llm.post` call with POSIX `SIGALRM`. This is deliberately the same numerical limit as the configured socket timeout, but it measures the entire call and therefore covers a live socket that never finishes its body. The client runs in the CLI main thread on macOS, where `SIGALRM` is available.

Expiry raises a dedicated `ControlRequestDeadlineExceeded` transport error. It is retryable under the existing five backoffs (1, 2, 4, 8, 16 seconds), together with HTTP 5xx. A 4xx remains one-attempt fail-fast. After the initial attempt plus five retries, the client raises `ControlRetriesExhausted`; `p2_run.run_instance` records that task as a structured `REFUSED` row and continues to the next instance.

The deadline handler restores the previous alarm handler and timer in a `finally` block. It therefore cannot leak into later local work after a successful call, exception, or retry.

## Scope and invariants

This changes transport liveness only. It does not change the endpoint, headers, credentials, model, thinking configuration, seed, temperature, steps, ceiling advice, classification, or the ceiling arm's exclusion from the primary statistic. The clean restart is the sole data source; the archived partial and earlier corrupt output are audit artifacts only.

## Verification

Tests will show that the deadline wrapper arms and restores `SIGALRM`, that a deadline expiry consumes the same declared backoff/retry budget as a 5xx, and that 4xx responses remain non-retryable. Offline P2 tests must pass before a fresh full five-instance run is started. The final JSONL must contain five parseable instance rows plus one parseable summary row before any result is interpreted.

## Self-review

The retry class is explicit, the retry count is unchanged, and a full restart avoids mixing observations taken under different liveness behavior. The macOS/POSIX constraint is explicit rather than silently relying on a nonportable signal mechanism.
