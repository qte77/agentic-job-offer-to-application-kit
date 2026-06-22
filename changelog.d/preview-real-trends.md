### Added

- build: `make preview` now bundles the real `data`-branch trends into `ui/public/data/trends.ndjson`
  (same-origin, git-ignored) via a new `make trends-local` target, so the **local** dashboard shows
  real market data too — not just the live site. Offline-first: prefers a local `results/trends.ndjson`
  or an existing `data` / `origin/data` ref, and only `git fetch`es as a last resort.
