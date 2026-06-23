### Changed

- ui: the Inter font is now served as WOFF2 (~64% smaller than the previous TTF — 68KB → 24KB per
  weight) with the TTF kept only as a legacy `@font-face` fallback. Generated from the vendored TTF
  via `fonttools`; still offline-first, no CDN. (#112)
