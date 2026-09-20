# wynncard

Renders a Wynncraft item as a PNG of its in-game tooltip: the same fonts, sprites, frames and layout
the game and the Wynntils mod draw, scaled up so it looks like a screenshot.

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

Every `Item` field but the name is optional; a section with no data is not drawn. `Identification.from_api`
knows every gear stat by its Wynncraft API name or Wynntils key and fills the printed name, the unit,
the position in the list and the "lower is better" flag of spell costs. Stats it does not know print as
given and sort last.

## From the APIs

```python
from wynncard import from_wynnpool, from_market, render

item = from_wynnpool(requests.get("https://api.wynnpool.com/item/Spring").json())   # base item
item = from_market(listing, item_data, scales)                                     # one rolled copy
png = render(item)
```

- `from_wynnpool(info)` takes the Wynnpool item (same shape as the Wynncraft v3 item API) with its
  unrolled `raw` identifications.
- `from_market(listing, info=None, scales=None)` takes a Wynnventory Trade Market listing (`name`,
  `rarity`, `overall_roll`, `reroll_count`, `stat_rolls`, `shiny_stat`) and lays its rolls over the
  Wynnpool item. `scales` are Wynnpool weight scales, `[{"profile": "Main", "score": 94.6}]`.

## Render options

`render(item, **options)` returns PNG bytes, `render_image` the Pillow image.

- `scale` - output pixels per Minecraft pixel; 4 by default, 1 gives the raw game size.
- `color_lerp` - `False` snaps roll colours to the five flat stops, `True` slides between them like the
  mod's lerp option.
- `rolls` - `False` hides the roll percentages, giving the plain game tooltip.
- `frame` - `False` leaves the text on a transparent canvas.
- `min_width` - the narrowest text block in Minecraft pixels; 140 like the game.

Layout follows Wynntils' `IdentifiableTooltipBuilder`: emblem and name, rarity/type banners with the
untradable or quest-item mark, element strip, DPS or health with attack speed and base damage or
defence, the Wynnpool scales, requirement diamonds with quest, class and level, the shiny stat, the
reroll counter, identifications in the mod's default order (skills, misc, defence, damage, spell costs)
with value and roll, and the major ids. Shiny items get the shiny frame. Requirement marks are drawn
neutral, because a card describes an item, not whether a particular character can wear it.

Python 3.11+, Pillow the only dependency. Tests: `python -m unittest discover -s tests`.

## Layout of the package

- `model.py` - `Item` and its parts, the input to everything else.
- `stats.py` - the identification table, built the way Wynntils builds its stat registry.
- `sources.py` - adapters from the Wynnpool and Wynnventory JSON.
- `tooltip.py` - `Item` to tooltip lines: runs of `(text, font, colour)` in Minecraft pixels.
- `mcfont.py` - Minecraft bitmap fonts: bitmap and space providers, glyph metrics, drawing.
- `render.py` - lines onto the nine-slice frame, scaled up, to PNG.

## Assets

`wynncard/assets/mc` holds the fonts, sprites and tooltip frames taken from the Wynncraft resource
pack, plus the scales icon from Wynntils. They belong to Wynncraft and to the Wynntils project, not to
this repository, so keep it private. `mcfont.py` implements the part of Minecraft's font stack they
need: bitmap providers, the space font for kerning, and `round(inked width * scale) + 1` advances.

The package ships them, so installing it is enough; `WYNNCARD_ASSETS` points the library at a copy kept
elsewhere. To refresh them from a newer pack, run `python tools/extract_assets.py [pack.zip | downloads
dir]`; without an argument it takes the newest pack the launcher downloaded from the server (macOS,
Windows and Linux locations are known). The pack's zip headers are obfuscated and its PNG checksums are
deliberately broken, so the extractor reads entries by offset and rebuilds each image.
