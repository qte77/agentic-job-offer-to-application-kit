### Fixed

- `scripts/build_ui_shortlist.py`: the preview dashboard now lists rows by `score` descending
  instead of by lane-file glob path. `engineering` holds the large majority of rows, so a
  high-scoring offer in an alphabetically later lane was buried hundreds of positions down
  (HumanLayer at row 417 of 467, Nomadic ML at 467). The sort is **stable** — equal scores keep
  their lane-path then in-file order, so the output stays deterministic for snapshot comparison —
  and a missing, `null` or non-numeric `score` sorts to the bottom rather than raising. `stale`
  filtering is unchanged.
