# wynncard

[![CI](https://github.com/byrodi/wynncard/actions/workflows/ci.yml/badge.svg)](https://github.com/byrodi/wynncard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/byrodi/wynncard)](https://github.com/byrodi/wynncard/releases)
[![License](https://img.shields.io/github/license/byrodi/wynncard)](LICENSE)

Wynncraft item tooltips rendered as PNG cards with the game's own fonts and sprites.

The card is the tooltip the game and the Wynntils mod draw, laid out in Minecraft pixels and scaled up,
so it looks like a screenshot of the real item.

## Features

- Describe any item by hand with `Item`, or load one from the Wynnpool and Wynnventory APIs.
- Every gear identification known by API name, with the mod's names, units and order.
- Roll percentages coloured like the mod, flat or lerped, or hidden for the plain game look.
- Rarity frames, shiny frames, emblems, element strips, requirement diamonds, major ids.
- Output as PNG bytes or a Pillow image at any integer scale.

## Requirements

Python 3.11 or newer and Pillow.

## Installation

```
pip install git+https://github.com/byrodi/wynncard
```

## Example

```python
from wynncard import Item, Identification, Requirements, render

item = Item("Spring", tier="mythic", kind="weapon", type="bow", emblem="diamond_5", elements=["water"],
            attack_speed="normal", average_dps=820, damage={"neutral": (135, 185), "water": (170, 310)},
            requirements=Requirements(level=98, class_name="archer", intelligence=120),
            identifications=[Identification.from_api("manaRegen", 39, roll=100.0),
                             Identification.from_api("4thSpellCost", -11, roll=88.9)],
            overall_roll=91.2, rerolls=3)
open("spring.png", "wb").write(render(item, scale=4))
```

This writes a mythic bow card with its DPS, damage, requirements and two rolled identifications.

Every `Item` field but the name is optional; a section with no data is not drawn. `Identification.from_api`
takes a Wynncraft API stat name (`manaRegen`) or a Wynntils key (`MISC_MANA_REGEN`); unknown names print
as given and sort last.

### From the APIs

```python
from wynncard import from_wynnpool, from_market, render

item = from_wynnpool(requests.get("https://api.wynnpool.com/item/Spring").json())   # base item
item = from_market(listing, item_data, scales)                                     # one rolled copy
png = render(item)
```

`from_wynnpool` takes the Wynnpool item (same shape as the Wynncraft v3 item API) with its unrolled
identifications. `from_market` lays a Wynnventory Trade Market listing over it: rolls, overall
percentage, rerolls and shiny stat. `scales` are Wynnpool weight scales, `[{"profile": "Main", "score": 94.6}]`.

### Render options

`render(item, **options)` returns PNG bytes, `render_image` the Pillow image.

- `scale`: output pixels per Minecraft pixel, 4 by default.
- `color_lerp`: slide roll colours between the stops instead of snapping to the flat five.
- `rolls`: `False` hides the roll percentages.
- `frame`: `False` leaves the text on a transparent canvas.
- `min_width`: the narrowest text block in Minecraft pixels, 140 like the game.

## Assets

`wynncard/assets/mc` holds the fonts, sprites and tooltip frames from the Wynncraft resource pack and the
scales icon from Wynntils. The package ships them; `WYNNCARD_ASSETS` points the library at a copy kept
elsewhere. To refresh them from a newer pack, run `python tools/extract_assets.py [pack.zip | downloads dir]`;
without an argument it takes the newest pack the launcher downloaded from the server on macOS, Windows
or Linux.

## License

The code is under the [MIT License](LICENSE).

The files under `wynncard/assets` are not: the fonts, sprites and frames belong to Wynncraft Studios and
the scales icon to the Wynntils project. They are included so the cards match the game and are used here
without a written grant from either owner. Do not reuse them outside this purpose.
