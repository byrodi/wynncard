# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `wynncard-server`: an HTTP service that takes an item as JSON on `POST /card` and answers the card
  as PNG, or a batch of up to 100 items as a JSON array of base64 PNGs.
- Web editor on GitHub Pages: presets for every gear item with roll sliders, items built from scratch,
  PNG export, copy to clipboard and share links. It runs the library in the browser through Pyodide.
- `from_dict` and `to_dict`: an `Item` as a JSON-ready dict with defaults left out.
- `rolls.values` and `rolls.percentage`: every value an identification can roll and its roll
  percentage, as Wynntils works them out.
- `tools/build_site_data.py` builds the site's presets from the Wynncraft item database and checks
  every roll range against the API; `tools/build_font.py` turns the game's font into a web font.

### Changed

- Drawing is 3 to 9 times faster: tinted glyphs are cached instead of recoloured for every character.

### Fixed

- A tooltip no longer draws the divider of a section it has no data for, so a market listing
  rendered without the Wynnpool item has no empty lines above its identifications.
- Shiny cards use the first frame of the animated shiny sprites; the whole strip was stretched over
  the card and striped it.
- A shiny tracker with no requirements above it gets one divider, not two.

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
