### Added

- Dashboard theme toggle a11y: a polite `aria-live` region (`#theme-status`) now announces the selected
  mode to screen readers on change (the focused button's changed `aria-label` alone isn't re-read), and
  a `::before` width-sizer reserves the widest label so the pill no longer resizes as it cycles
  auto/light/dark. Additive only — the converged theme cycle, tokens, fonts, and favicon are unchanged.
