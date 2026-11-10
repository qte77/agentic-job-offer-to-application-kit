### Changed

- `make relevance_headless` now runs its `claude -p` slices read-only (no `--permission-mode
  acceptEdits`). The screen only reads its batches and reports through the workflow journal; with
  write access, agents had left scratch files with personal data in the repo root. Verified
  read-only on a 4-batch screen and two tailor runs (2026-11-09).
- `AGENT_LEARNINGS.md`: two new entries on headless runs (the 10-minute `-p` wait limit, dying
  containers and silent batch gaps; scratch files from write-enabled agents), and the env-token
  entry no longer prints a machine-specific command.
