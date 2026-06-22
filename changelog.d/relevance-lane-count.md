### Fixed

- docs: the relevance workflow no longer hardcodes the lane count ("5 lanes" / "five target lanes")
  in its `meta.description`, header, and agent prompt — they now say "the target lanes" (the prompt
  still enumerates the actual lane keys), so the wording stays correct if the lane set changes.
