### Changed

- Hardened the GitHub Actions workflows (`ci.yaml`, `codeql.yaml`): deny-all top-level
  `permissions: {}` with least-privilege per job, `concurrency` cancellation, `timeout-minutes`,
  and `persist-credentials: false` on checkout.
