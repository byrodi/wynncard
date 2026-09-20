"""Adapters from the public item APIs to `Item`.

`from_wynnpool` takes the item as `https://api.wynnpool.com/item/<name>` returns it (the same shape as
the Wynncraft v3 item API). `from_market` layers a Wynnventory Trade Market listing on top of it: the
listing carries the rolled values, the overall percentage, rerolls and the shiny stat, the item data
carries everything else.
"""
import math

from .model import Identification, Item, Requirements, Scale, Shiny
from .stats import ELEMENTS, SKILLS


def _raw(value) -> int:
    """Base stats come either as a number or as `{"min", "raw", "max"}`."""
    return value.get("raw", value.get("max")) if isinstance(value, dict) else value


def _element(key: str) -> str:
    return key.removeprefix("base").removesuffix("Damage").removesuffix("Defence").lower() or "neutral"


def from_wynnpool(info: dict) -> Item:
    """A base item with its unrolled (`raw`) identifications."""
    damage, defence, health = {}, {}, None
    for key, value in (info.get("base") or {}).items():
        if key == "baseHealth":
            health = _raw(value)
        elif key.endswith("Damage") and _element(key) in ELEMENTS + ("neutral",):
            damage[_element(key)] = (value["min"], value["max"])
        elif key.endswith("Defence") and _element(key) in ELEMENTS:
            defence[_element(key)] = _raw(value)
    req = info.get("requirements") or {}
    restriction = (info.get("restriction") or "").lower().replace(" ", "_")
    return Item(
        name=info.get("displayName") or info.get("internalName") or info.get("id") or "?",
        tier=(info.get("tier") or "normal").lower(),
        kind=info.get("type") or "",
        type=(info.get("subType") or "").lower(),
        emblem=info.get("emblem") or "diamond_1",
        elements=list(info.get("elements") or []),
        restriction="" if restriction == "none" else restriction,
        attack_speed=info.get("attackSpeed") or "",
        average_dps=info.get("averageDps"),
        health=health, damage=damage, defence=defence,
        requirements=Requirements(level=req.get("level") or 0, class_name=req.get("classRequirement") or "",
                                  quest=req.get("quest") or "", **{s: req.get(s) or 0 for s in SKILLS}),
        identifications=[Identification.from_api(api, _raw(value))
                         for api, value in (info.get("identifications") or {}).items()],
        major_ids=dict(info.get("majorIds") or {}),
    )


def from_market(listing: dict, info: dict | None = None, scales: list[dict] | None = None) -> Item:
    """A rolled copy from a Wynnventory listing, on top of the Wynnpool item when given.

    `scales` are Wynnpool weight scales as `[{"profile": "Main", "score": 94.6}]`.
    """
    item = from_wynnpool(info) if info else Item(name=listing.get("name") or "?",
                                                 type=(listing.get("type") or "").lower())
    if listing.get("rarity"):
        item.tier = listing["rarity"].lower()
    item.overall_roll = listing.get("overall_roll")
    item.rerolls = listing.get("reroll_count") or 0
    shiny = listing.get("shiny_stat")
    if isinstance(shiny, dict):
        item.shiny = Shiny((shiny.get("statType") or {}).get("displayName") or "Shiny", shiny.get("value") or 0)
    item.scales = [Scale(scale["profile"], scale["score"]) for scale in scales or []]

    rolled = []
    for roll in listing.get("stat_rolls") or []:
        actual = roll.get("statActualValue") or {}
        stat_type = actual.get("statType") or {}
        value = actual.get("value")
        if value is None:
            continue
        try:
            percentage = float(roll.get("rollPercentage"))
        except (TypeError, ValueError):
            percentage = math.nan
        key = stat_type.get("key") or stat_type.get("apiName") or ""
        if key.startswith("SPELL_"):
            value = -value  # the market API counts a cost reduction up, the tooltip shows a negative cost
        found = Identification.from_api(key, value, None if math.isnan(percentage) else percentage)
        if found.key == key and found.name == key:  # not in the table: take the listing's own labels
            found.name = stat_type.get("displayName") or roll.get("displayName") or key
            found.unit = {"PERCENT": "%", "PER_3_S": "/3s", "PER_5_S": "/5s", "TIER": " tier"}.get(
                stat_type.get("unit"), "")
        rolled.append(found)
    if rolled:
        item.identifications = rolled
    return item
