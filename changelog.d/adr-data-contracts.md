### Added

- docs: ADR-0003 (data-contract enforcement) — maps the typed vs untyped data boundaries across the
  four layers and sets the direction: pydantic models on the Python boundaries (validated on read),
  inline JSON Schema for the sandboxed JS workflows, and JSON Schema as the cross-language contract
  for shared data (e.g. a single `config/lanes.json`); explicitly rejects a JS/TS validation library
  (can't run in the Workflow sandbox). Ships a prioritized backlog of boundaries to harden. Research
  only, no code (closes #158).
