### Fixed

- `persist-offer` now removes a review-aid check file (`cv-stuffing-check.md` and the other
  `CHECKS` sidecars) when re-persisting a pack whose check comes back clean. Before, a re-tailored
  or hand-fixed pack kept the warning file from its earlier run, so the offer dir reported a
  problem the current CV no longer had.
