### Added

- tests: offline coverage for the ingest network helpers `get_json` / `get_bytes` (#53 follow-up) —
  non-200 responses raise `FetchError` (status + polyfetch backend in the message, so a junk error
  body never reaches `json.loads`), and 200 responses parse/return with the backend passed through;
  `get_json` sends an `Accept: application/json` header while `get_bytes` does not. Exercised via a
  fake `polyfetch_scrape` module, so they run under `pytest -m "not network"`.
