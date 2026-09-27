# v3/dcm -- draft compliance matrix shards

One CSV shard per task: `T<nn>.csv` (`T01`, ..., `T22`; T16a and T16b share `T16.csv`).
A task edits only its own shard, so parallel worktrees never conflict (plan S5, S9).
`tools/v3_dcm.py --render` merges the shards into `docs/v3/DCM.md` (T0 and T23 only);
never edit `DCM.md` by hand.

## Format

- UTF-8. The first line is the pin, exactly:
  `# draft-pdf-sha256: c37643f0971c3457c176c39607e1be6782007c85988c053e4b5ab0aa8be7263a`
- The second line is the header:
  `id,where,quote,level,c_ref,decision,module,test,phase,result_ref`
- One row = one draft sentence + the one test that protects it. An id can appear in
  several rows and several shards; `(id, test)` must be unique.

| column | content |
|---|---|
| `id` | `D<section>.<name>`: `D4.state`, `DF1.t2`, `DA1.l5`, `D5.3.rand`, `D7.pf2048`, ... |
| `where` | section / page / paragraph of the draft |
| `quote` | one sentence, verbatim from `docs/v3/draft-2026-09-07.txt`; `…` (U+2026) elides |
| `level` | `L0` / `L1` / `L2`, or a combination such as `L0+L1` |
| `c_ref` | C1-C16, Q1-Q14, O1-O16, D-v3-n, v2 D-numbers; `;`-separated |
| `decision` | how v3 builds it, one sentence |
| `module` | path under `auditgame/` |
| `test` | `tests/v3/<file>.py::<Class>::<test_name>` |
| `phase` | `P2` / `P3` / `P4` / `P5`: the phase that makes the test green |
| `result_ref` | the table cell or record field that receives the result (filled at P5) |

## Quotes

The check normalises both sides with Unicode NFKC and collapses whitespace. NFKC turns the
PDF's mathematical italic letters into plain ones, so write `(k, ι, σ, ε)`, not the
italic code points. pdftotext keeps the PDF's spacing and hyphen-joins (for example
`st = (ct , ι, σ)`, `CPUminutes`): copy the text as it is in the pinned file, or elide
around the damage with `…`.

## Tests

- The test's name is the draft sentence it protects; its docstring contains the row's
  `id` (checked) and the verbatim quote (convention).
- One `unittest.TestCase` per file, named `Test` + the CamelCase file stem without
  `test_`: `test_s4_state_payload.py` -> `TestS4StatePayload`. The seeded rows use this.
- Every test in `tests/v3/` needs a DCM row unless its file is `test_infra_*.py`.
- A shard may name tests only in the test files its task owns (plan S9 table,
  `tools/v3_dcm.OWNED_TESTS`).

## Pending rows

T0 seeded the rows that carry an explicit draft id in the plan (S10) into the owning
task's shard, so each task starts from its rows and edits them in its own shard (rename a
test, fix a class name, add rows for the tests the plan lists without an id). Until a
task writes its test file, its rows are PENDING: `tests/run_v3.py` accepts that and
prints the count; `tools/v3_dcm.py --check` does not. Once the file exists, every row
naming it must point to a test that exists.

    cd auditgame
    ../.venv/bin/python tools/v3_dcm.py --pending
    ../.venv/bin/python tools/v3_dcm.py --check      # strict: the six checks of plan S5
