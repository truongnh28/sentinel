# Public repository hygiene

**Date:** 2026-09-22  
**Scope:** PDF tracking, machine-specific absolute paths, and the paper link index.

## Goal

Keep the working repository useful while making its public Git state portable and free of redistributed paper PDFs. Local PDFs remain available to the author.

## Design

1. Ignore `docs/paper/*.pdf` and remove the currently tracked PDFs from the Git index with `git rm --cached`. This preserves the files in the local working tree and removes them from the next public commit. Existing Git history is not rewritten.
2. Remove machine-specific `/Users/truong.nh/...` values from tracked files:
   - untrack and ignore the generated `auditgame/carriers/repo.path` pointer;
   - use repository-relative paths in machine-readable artifacts where the field remains useful;
   - use portable placeholders or plain descriptions in documentation.
3. Make `docs/paper/Paper-List-and-Code.md` the public replacement for local PDFs:
   - cover every numbered research paper represented by the local PDF set;
   - add missing #24 and #25 entries;
   - correct stale “not downloaded” statements for #13, #18, and #20;
   - list non-numbered supplementary papers separately;
   - link to an authoritative landing page (publisher, DOI, arXiv, or official project page), not to local PDF files;
   - keep internal Sentinel drafts in a separate local-artifact section without claiming a public source URL.

## Verification

- No tracked PDF remains under `docs/paper/`.
- The local PDF files still exist after index cleanup.
- No tracked text file contains `/Users/truong.nh` or `file:///Users/truong.nh`.
- Every numbered PDF prefix in the local set has a corresponding paper-list entry.
- Every external paper-list entry has a non-local source URL.
- Existing Python sources still compile, and the working tree contains only the intended cleanup changes.

## Out of scope

- Rewriting published Git history.
- Changing experimental code, gates, projected results, or sealed data.
- Determining redistribution rights for files that remain only on the author's machine.
