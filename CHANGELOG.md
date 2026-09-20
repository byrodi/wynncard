# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- A tooltip no longer draws the divider of a section it has no data for, so a market listing
  rendered without the Wynnpool item has no empty lines above its identifications.

## [0.2.0] - 2026-09-20

### Added

- `Item` model: describe any item by hand, every field but the name optional.
- `Identification.from_api` with the full gear stat table taken from Wynntils.
- `from_wynnpool` and `from_market` adapters for the Wynnpool item API and Wynnventory listings.
- Render options `rolls`, `frame` and `min_width`, plus `render_image` for a Pillow image.
- Untradable and quest-item marks, quest requirement, shiny frame and the set tier on the card.
- `WYNNCARD_ASSETS` to point the library at assets kept outside the package.

### Changed

- **Breaking:** `render_card(listing, item_data, scales)` is replaced by `render(from_market(listing, item_data, scales))`.
- Identifications follow the mod's default order: skills, misc, defence, damage, spell costs.

[unreleased]: https://github.com/byrodi/wynncard/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/byrodi/wynncard/releases/tag/v0.2.0
