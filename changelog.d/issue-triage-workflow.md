### Added

- ci: AI issue-triage workflow — on newly **opened** issues, runs `qte77/gha-issue-triage`
  (SHA-pinned to v0.3.0) for duplicate detection, relevance/feasibility scoring, and auto-labeling.
  Backend defaults to **GitHub Models** (`openai/gpt-4.1`) via the built-in token (zero-secret),
  with least-privilege permissions (`contents: read`, `issues: write`, `models: read`).
