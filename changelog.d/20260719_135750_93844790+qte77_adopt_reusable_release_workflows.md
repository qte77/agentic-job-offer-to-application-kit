### Changed

- Release CI now delegates to the estate-standard reusable workflows in `qte77/.github` (#193):
  `bump-my-version.yaml`, `tag-release.yaml`, and `publish-release.yaml` are thin `uses:` callers
  (SHA-pinned) instead of inline steps. Behavior and the operator commands are unchanged; the bump
  now commits via the GitHub API (signed), and the never-delete-tags / idempotent guardrails are
  centralized upstream.
