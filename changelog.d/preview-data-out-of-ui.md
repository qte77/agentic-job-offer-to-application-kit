### Changed

- build: `make preview` now serves real trends from a **throwaway assembled copy** of `ui/` (mirroring
  the gh-pages deploy) instead of writing them into the source tree — so the `ui/` code directory
  never holds data. Drops the `make trends-local` target and the `ui/public/data/trends.ndjson`
  gitignore entry; the `data` branch stays the single source of truth.
