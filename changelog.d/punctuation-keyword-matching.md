### Fixed

- Keyword pre-filter (`ingest.build_patterns`) now matches tech terms with punctuation as whole
  tokens — `c++`, `.net`, `node.js`, `ci-cd`, `c#` — and no longer leaks a short term into a larger
  token (`c` is not matched inside `c++`), while plain words still match before ordinary sentence
  punctuation. Pinned by a hypothesis property. (#97)
