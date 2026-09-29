"""Sentinel v3 -- the simulation built to the letter of draft FSE-2027-15 (07/09/2026).

Plan: docs/plans/v3-p2-plan.md.  Design and decisions: sentinel-v3.md.

v3 IMPORTS from the v2 modules in auditgame/ and never patches them: the v2 freeze
(frozen/MANIFEST.json, sha256:c789fa7362e0) and the D35 freeze must stay clean, and
tests/v3/test_infra_v2_intact.py checks that on every run of tests/run_v3.py.

The two frozen modules are `config` (switches, cells, decided values) and `api` (the
shared interface every later task codes against).  They change only through a separate
"interface patch" merged into branch v3 before the tasks that depend on it (plan S2).
"""
