<!--
A new scriv changelog fragment.

Uncomment the section that is right (remove the HTML comment wrapper).
For top level release notes, leave all the headers commented out.
-->

<!--
### Added

- A bullet item for the Added category.

-->
<!--
### Changed

- A bullet item for the Changed category.

-->
<!--
### Deprecated

- A bullet item for the Deprecated category.

-->
<!--
### Removed

- A bullet item for the Removed category.

-->
### Fixed

- `pack_plan.select()` now excludes `refresh.py`-flagged `stale` (delisted/dead) offers, so a
  closed posting can no longer reach a full LLM tailor pass. `docs/quickstart.md`'s pipeline now
  shows `refresh` before `pack-plan` so the flag is set before it's read.
- `cc-workflow-relevance.js`'s aggregated return and `persist_scored`'s summary line now surface
  `locationFlaggedCount`/`tenureFlaggedCount` (previously computed per batch, then silently
  dropped before reaching either output) (#370).
<!--
### Security

- A bullet item for the Security category.

-->
