<!--
A new scriv changelog fragment.
-->

### Fixed

- The market-trends **granularity** dropdown (#285) now shares the time-frame picker's styling
  (border / background / padding / focus ring) instead of rendering as an unstyled native select —
  the rule targets `.range-picker select` rather than the `#trends-range` id.
