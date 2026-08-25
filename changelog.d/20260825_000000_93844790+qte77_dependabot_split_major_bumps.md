### Changed

- `.github/dependabot.yml`: each ecosystem's update group now splits `minor`/`patch` from `major`.
  A single catch-all group with no `update-types` filter let a major bump ride in alongside safe
  ones and block the whole PR — happened twice in one round (`complexipy` 5→7 in #381, breaching
  the repo's own `<6` pin from the #279/#288 incident; `astral-sh/setup-uv` 9→10 in #382). Majors
  now land in their own group for review; routine bumps keep merging together.
