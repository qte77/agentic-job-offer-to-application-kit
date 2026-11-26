### Changed

- Release workflows (`bump-my-version.yaml`, `tag-release.yaml`, `publish-release.yaml`) re-pinned to the `qte77/.github` v0.1.2 tag commit in tag form (`@aeef158f…  # v0.1.2`), so Dependabot can follow qte77/.github releases (#538). The called files are unchanged except `bump-version`, which gains the optional `scriv_pin` input (not used here).
