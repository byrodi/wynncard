# wynncard

[![CI](https://github.com/byrodi/wynncard/actions/workflows/ci.yml/badge.svg)](https://github.com/byrodi/wynncard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/byrodi/wynncard)](https://github.com/byrodi/wynncard/releases)
[![License](https://img.shields.io/github/license/byrodi/wynncard)](LICENSE)

Wynncraft item tooltips rendered as PNG cards with the game's own fonts and sprites.

The card is the tooltip the game and the Wynntils mod draw, laid out in Minecraft pixels and scaled up,
so it looks like a screenshot of the real item.

## Web editor

[byrodi.github.io/wynncard](https://byrodi.github.io/wynncard/) makes cards in the browser, with nothing to install.

1. Pick any gear item, paste one Wynntils shared in chat, or start from scratch.
2. Change any stat and its base; sliders stop only on values the base can roll.
3. Switch roll percentages, the frame and Wynnpool scales on or off.
4. Download a PNG, copy the image, copy the item for Wynncraft chat, or share a link.

The editor runs this library through [Pyodide](https://pyodide.org), so its cards are the same pixels as Python's.
The first visit downloads about 7 MB.

## Features

- Describe any item by hand with `Item`, or load one from the Wynnpool and Wynnventory APIs.
- Every gear identification known by API name, with the mod's names, units and order.
- Roll percentages coloured like the mod, flat or lerped, or hidden for the plain game look.
- Rarity frames, shiny frames, emblems, element strips, requirement diamonds, major ids.
- Output as PNG bytes or a Pillow image at any integer scale.
- Items as plain JSON-ready dicts, and the full list of values each identification can roll.
- Reads and writes the item codes Wynntils shares in Wynncraft chat.

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

### As JSON

`to_dict` turns an `Item` into a dict keyed by its field names, with defaults left out; `from_dict` reads one
back and raises `ValueError` naming the first bad key. This is the format the web editor and its share links
use.

```python
from wynncard import from_dict, render

render(from_dict({"name": "Spring", "tier": "mythic", "type": "bow",
                  "identifications": [{"stat": "manaRegen", "value": 39, "roll": 100.0}]}))
```

An identification's `stat` is an API name or a Wynntils key and brings the printed name, unit and position from
the stat table. For a stat the table does not know, `name`, `unit` and `inverted` set them by hand.

### Rolls

`rolls.values(base, inverted)` lists every value an identification with that base value (the item API's `raw`)
can roll, from the worst roll to the best, and `rolls.percentage(value, base, inverted)` gives the roll
percentage. Both follow Wynntils: 30 to 130 percent of a positive base, 70 to 130 percent of a negative one,
spell costs worked out on the negated base. `inverted` is the stat table's flag for spell costs.

```python
from wynncard import rolls

rolls.values(-3, inverted=True)       # [-1, -2, -3, -4]: a 3rd Spell Cost of -3 rolls -1 to -4
rolls.percentage(16, 20)              # 50.0
```

### Wynntils chat items

Wynntils shares an item in chat as a run of private-use characters. `wynntils.decode` finds the code in a piece of
text and returns the item as a dict; `wynntils.to_item` makes a card of it, with the base data of a gear item taken
from the item API. `wynntils.encode` writes a code the mod shows as an item: a gear item by its name, anything else
as crafted gear.

```python
from wynncard import render, wynntils

item = wynntils.to_item(wynntils.decode(chat_line), info)   # info: the item from the Wynncraft API
png = render(item)
```

### Render options

`render(item, **options)` returns PNG bytes, `render_image` the Pillow image.

- `scale`: output pixels per Minecraft pixel, 4 by default.
- `color_lerp`: slide roll colours between the stops instead of snapping to the flat five.
- `rolls`: `False` hides the roll percentages.
- `frame`: `False` leaves the text on a transparent canvas.
- `min_width`: the narrowest text block in Minecraft pixels, 140 like the game.

## HTTP server

`wynncard-server/` wraps the library in a small HTTP service for callers in other languages:
`POST /card` with a listing or item as JSON answers `image/png`. See its [README](wynncard-server/README.md).

## Building the site

The site lives in `web/` (Svelte, TypeScript, Vite) and needs Node 22.18 or newer. Its data comes from
`tools/build_site_data.py`: the library zipped for Pyodide, the stat table, the link preview, and a preset for every
gear item of the Wynncraft item database, each checked against the roll range the API states and carrying
Wynnpool's weights when it has any. If the Wynnpool request fails, the build warns and the presets go without
weights.

```
pip install -e .
python tools/build_site_data.py web/public    # --source and --weights read saved copies instead
cd web && npm ci && npm run dev
```

`npm run check` runs svelte-check, ESLint and Prettier, `npm test` the unit tests, `npm run build` writes `web/dist`.
The Pages workflow does the same on every push to `main` and once a day, so new items reach the site without a
commit. The pixel font in `web/src/assets` is made from the game's font by `tools/build_font.py`.

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
