"""Wynncraft item cards as PNG, rendered the way the game and the Wynntils mod draw their tooltips.

    from wynncard import Item, Identification, render

    item = Item("Spring", tier="mythic", kind="weapon", type="bow", average_dps=820,
                identifications=[Identification.from_api("manaRegen", 30, roll=72.5)])
    open("spring.png", "wb").write(render(item, scale=4))

`sources.from_wynnpool` and `sources.from_market` build an `Item` from the public item APIs,
`spec.from_dict` and `spec.to_dict` move one to and from JSON, and `rolls` lists the values an
identification can roll.
"""
from . import rolls
from .model import Identification, Item, Requirements, Scale, Shiny
from .render import render, render_image
from .sources import from_market, from_wynnpool
from .spec import from_dict, to_dict

__all__ = ["Item", "Identification", "Requirements", "Scale", "Shiny", "render", "render_image",
           "from_wynnpool", "from_market", "from_dict", "to_dict", "rolls"]
__version__ = "0.2.0"
