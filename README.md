# wynncard

Renders a Wynncraft item as a PNG of its in-game tooltip: the same fonts, sprites, frames and layout
the game and the Wynntils mod draw, scaled up so it looks like a screenshot.

```python
from wynncard import render_card

png = render_card(listing, item_data, scales)
```

- `listing` - a Wynnventory Trade Market listing (`name`, `rarity`, `overall_roll`, `reroll_count`,
  `stat_rolls`, optional `shiny_stat`). The rolled values and percentages come from here, and it is the
  only required argument.
- `item_data` - the Wynnpool item (`https://api.wynnpool.com/item/<name>`): type, emblem, attack speed,
  average DPS, elements, requirements, base damage and major ids.
- `scales` - `[{"profile": "Main", "score": 94.6}]`, Wynnpool weight scales scored against the roll.
- `scale` - how many times to blow the tooltip up; 4 by default, 1 gives raw Minecraft pixels.
- `color_lerp` - `True` (the default) slides roll percentages between the colour stops, `False` snaps
  them to the five flat colours the mod uses with lerping turned off.

Without `item_data` the card still renders, only with the sections the listing alone can fill.

Layout follows Wynntils' `IdentifiableTooltipBuilder`: emblem and name, rarity/type/element banners,
DPS with attack speed and base damage, the Wynnpool scales, requirement diamonds, the reroll banner,
identifications in tooltip order with value and roll percentage, and the major ids. Requirement marks
are drawn neutral, because a card describes an item, not whether a particular character can wear it.

Python 3.11+, Pillow the only dependency. Tests: `python -m unittest discover -s tests`.

## Assets

`wynncard/assets/mc` holds the fonts, sprites and tooltip frames taken from the Wynncraft resource
pack, plus the scales icon from Wynntils. They belong to Wynncraft and to the Wynntils project, not to
this repository, so keep it private. `mcfont.py` implements the part of Minecraft's font stack they
need: bitmap providers, the space font for kerning, and `round(inked width * scale) + 1` advances.

To refresh them from a newer pack, run the extractor against the copy Minecraft downloaded from the
server (`~/Library/Application Support/minecraft/downloads/**`). The pack's zip headers are obfuscated
and its PNG checksums are deliberately broken, so the extractor reads entries by offset and rebuilds
each image.
