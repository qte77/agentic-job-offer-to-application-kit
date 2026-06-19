### Changed

- `ui/` theme toggle now mirrors the canonical `qte77.github.io` control: an `auto`/`light`/`dark`
  cycle button applied as `data-theme` on `<html>` (was a three-button segmented control on a `body`
  class), with an inline `<head>` anti-flash script and a `:focus-visible` ring. Theme logic moved to
  a self-contained `ui/theme.js`; the chart rebuilds on a `themechange` event. The `?theme=` URL param
  was dropped to match the canonical toggle. The button keeps a dynamic `aria-label` announcing state.
