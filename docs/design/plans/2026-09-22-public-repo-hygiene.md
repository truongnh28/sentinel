# Public Repository Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove redistributed PDFs and machine-specific paths from the public Git state while preserving local working files and providing a complete authoritative paper-link index.

**Architecture:** Git ignore/index rules separate local research material and generated runtime pointers from public source. Tracked documentation uses portable relative paths or descriptive placeholders. `Paper-List-and-Code.md` becomes the public, link-first inventory for research sources.

**Tech Stack:** Git, Markdown, JSON, shell verification, authoritative web sources.

## Global Constraints

- Preserve every local PDF file; remove it only from the Git index.
- Do not rewrite Git history.
- Do not modify experimental code, gates, projected results, or sealed data.
- Use publisher, DOI, arXiv, or official project pages for external paper links.

---

### Task 1: Remove PDFs from the public Git index

**Files:**
- Modify: `.gitignore`
- Untrack: `docs/paper/*.pdf`

- [ ] **Step 1:** Record the local PDF count and tracked PDF count.
- [ ] **Step 2:** Add an ignore rule for `docs/paper/*.pdf`.
- [ ] **Step 3:** Run `git rm --cached -- docs/paper/*.pdf` so local files remain.
- [ ] **Step 4:** Verify local and tracked counts: local count is unchanged and `git ls-files 'docs/paper/*.pdf'` is empty.

### Task 2: Remove machine-specific paths

**Files:**
- Modify: `.gitignore`
- Untrack: `auditgame/carriers/repo.path`
- Modify: `auditgame/results/M3-run.json`
- Modify: `docs/guides/HUONG-DAN-VA-BAO-CAO-TONG-HOP.md`
- Modify: `docs/reports/t5-delta-empirical.md`
- Modify: `docs/thesis/eval/PLAN.md`

- [ ] **Step 1:** Add an ignore rule and untrack the generated `repo.path` pointer while preserving the local file.
- [ ] **Step 2:** Replace the artifact's absolute repository path with `auditgame/workspace/pytest-dev/pytest`.
- [ ] **Step 3:** Replace documentation paths with repository-relative references, `/path/to/...` examples, or portable descriptions.
- [ ] **Step 4:** Verify `git grep` finds neither `/Users/truong.nh` nor `file:///Users/truong.nh` in tracked text.

### Task 3: Complete the public paper index

**Files:**
- Modify: `docs/paper/Paper-List-and-Code.md`

- [ ] **Step 1:** Compare all numbered local PDF prefixes with the numbered table and identify missing entries.
- [ ] **Step 2:** Verify authoritative landing-page links for missing #24 and #25 and the non-numbered supplementary research papers.
- [ ] **Step 3:** Remove local-PDF hyperlinks and stale download-status claims, while keeping filenames as plain local inventory text where useful.
- [ ] **Step 4:** Add a separate internal-artifact section for the three Sentinel PDFs without inventing public URLs.
- [ ] **Step 5:** Verify every numbered local PDF prefix has a corresponding index entry and every external entry contains an HTTP(S) source URL.

### Task 4: Final verification

**Files:**
- Verify only; no planned modifications.

- [ ] **Step 1:** Run `git diff --check`.
- [ ] **Step 2:** Compile all tracked Python files with the project interpreter.
- [ ] **Step 3:** Run `uv sync --locked --offline --dry-run`.
- [ ] **Step 4:** Confirm the local PDF count is unchanged, no PDF or `repo.path` remains tracked, no personal absolute path remains, and the diff is limited to this cleanup.
- [ ] **Step 5:** Commit the cleanup as one focused change.
