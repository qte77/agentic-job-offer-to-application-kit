### Fixed

- `ats-check` no longer flags a bare `---` thematic break / Setext underline as a table — the
  table check now requires a pipe (a GFM delimiter row always has one). A clean single-column
  tailored CV with `---` section separators now passes the gate instead of failing with a spurious
  "table detected" warning.
