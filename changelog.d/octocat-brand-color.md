### Fixed

- ui: the GitHub octocat in the header **Repo**/**Issues** links is no longer tinted with the
  theme text color (`currentColor`) — GitHub's logo guidelines forbid recoloring its mark. It now
  renders in GitHub's permitted colors: **black on light themes, white on dark** (new `--gh-logo`
  token), so it stays theme-legible without being recolored to the palette.
