# wynncard

Renders a Wynncraft item as a PNG card shaped like the in-game tooltip: emblem and icon, name with the
overall roll, rarity and element chips, DPS with attack speed and base damage, the Wynnpool scales, the
requirement diamonds, powder slots and rerolls, the identifications in tooltip order with value and roll
percentage, and the major ids.

```python
from wynncard import render_card

png = render_card(listing, item_data, scales, icon_bytes)
```

- `listing` - a Wynnventory Trade Market listing (`name`, `rarity`, `overall_roll`, `reroll_count`, `stat_rolls`,
  optional `shiny`). The rolled values and percentages come from here. It is the only required argument.
- `item_data` - the Wynnpool item (`https://api.wynnpool.com/item/<name>`): type, attack speed, average DPS,
  elements, requirements, powder slots, base damage and major ids.
- `scales` - `[{"profile": "Main", "score": 94.6}]`, the Wynnpool weight scales scored against the roll.
- `icon_bytes` - the item texture, for example from `https://cdn.wynncraft.com/nextgen/itemguide/3.3/<icon>.webp`.

Everything but the listing is optional, so a card still renders when the other sources are down.

Python 3.11+, Pillow the only dependency. Tests: `python -m unittest discover -s tests`.

The two fonts in `wynncard/assets` are Wynncraft's own `ascii` and `common` faces, converted from the WOFF files
wynnpool.com serves; the game icons live in the private use area of `common`. They belong to Wynncraft, not to
this project.
