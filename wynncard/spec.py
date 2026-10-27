"""Items as JSON-ready dicts: the format of the web editor, its share links and future HTTP callers.

The keys are `Item`'s field names. Only `name` is required: a missing key keeps the field's default, and
`to_dict` leaves defaults out, so a dict carries only what differs from an empty item. Damage ranges are
`[low, high]` lists. An identification is `{"stat", "value", "roll"}`: `stat` is a Wynncraft API name or
a Wynntils key and brings the printed name, unit and position from the stat table; `name`, `unit` and
`inverted` override them, which is how a stat the table does not know gets its label.

    {"name": "Spring", "tier": "mythic", "type": "bow", "damage": {"water": [170, 310]},
     "identifications": [{"stat": "manaRegen", "value": 39, "roll": 100.0}]}
"""
import dataclasses

from .model import Identification, Item, Requirements, Scale, Shiny

_FIELDS = tuple(f.name for f in dataclasses.fields(Item))
_REQUIREMENTS = tuple(f.name for f in dataclasses.fields(Requirements))
_DEFAULT = Item("")
_KINDS = {str: "a string", int: "a whole number", (int, float): "a number", list: "a list", dict: "an object",
          bool: "true or false"}


def from_dict(data: dict) -> Item:
    """The item a dict describes; ValueError names the first key that is unknown or of the wrong type."""
    _known(_typed(data, dict, "item"), _FIELDS, "item")
    item = Item(_typed(data.get("name"), str, "name"))
    if not item.name:
        raise ValueError("name must not be empty")
    for key in ("tier", "kind", "type", "emblem", "restriction", "attack_speed"):
        if key in data:
            setattr(item, key, _typed(data[key], str, key))
    for key in ("average_dps", "health"):
        if data.get(key) is not None:
            setattr(item, key, _typed(data[key], int, key))
    item.elements = [_typed(e, str, "elements") for e in _typed(data.get("elements", []), list, "elements")]
    item.damage = {element: _range(value, f"damage.{element}")
                   for element, value in _typed(data.get("damage", {}), dict, "damage").items()}
    item.defence = {element: _typed(value, int, f"defence.{element}")
                    for element, value in _typed(data.get("defence", {}), dict, "defence").items()}
    requirements = _known(_typed(data.get("requirements", {}), dict, "requirements"), _REQUIREMENTS, "requirements")
    item.requirements = Requirements(**{key: _typed(value, str if key in ("class_name", "quest") else int,
                                                    f"requirements.{key}") for key, value in requirements.items()})
    item.identifications = [_identification(stat) for stat in _typed(data.get("identifications", []), list,
                                                                      "identifications")]
    item.major_ids = {name: _typed(lore, str, f"major_ids.{name}")
                      for name, lore in _typed(data.get("major_ids", {}), dict, "major_ids").items()}
    if data.get("overall_roll") is not None:
        item.overall_roll = float(_typed(data["overall_roll"], (int, float), "overall_roll"))
    item.rerolls = _typed(data.get("rerolls", 0), int, "rerolls")
    if data.get("shiny") is not None:
        shiny = _known(_typed(data["shiny"], dict, "shiny"), ("name", "value"), "shiny")
        item.shiny = Shiny(_typed(shiny.get("name"), str, "shiny.name"), _typed(shiny.get("value"), int, "shiny.value"))
    for scale in _typed(data.get("scales", []), list, "scales"):
        scale = _known(_typed(scale, dict, "scales"), ("profile", "score"), "scales")
        item.scales.append(Scale(_typed(scale.get("profile"), str, "scales.profile"),
                                 float(_typed(scale.get("score"), (int, float), "scales.score"))))
    return item


def to_dict(item: Item) -> dict:
    """The dict form of an item with defaults left out; `from_dict` turns it back into the same card."""
    out = {"name": item.name}
    for key in _FIELDS[1:]:
        value = getattr(item, key)
        if value == getattr(_DEFAULT, key):
            continue
        if key == "damage":
            value = {element: [low, high] for element, (low, high) in value.items()}
        elif key == "requirements":
            value = {k: getattr(value, k) for k in _REQUIREMENTS if getattr(value, k) != getattr(Requirements(), k)}
        elif key == "identifications":
            value = [_identification_dict(stat) for stat in value]
        elif key == "shiny":
            value = {"name": value.name, "value": value.value}
        elif key == "scales":
            value = [{"profile": scale.profile, "score": scale.score} for scale in value]
        elif isinstance(value, (list, dict)):
            value = type(value)(value)
        out[key] = value
    return out


def _identification(data) -> Identification:
    _known(_typed(data, dict, "identifications"), ("stat", "value", "roll", "name", "unit", "inverted"),
           "identification")
    roll = data.get("roll")
    stat = Identification.from_api(_typed(data.get("stat"), str, "identification stat"),
                                   _typed(data.get("value"), (int, float), "identification value"),
                                   None if roll is None else float(_typed(roll, (int, float), "identification roll")))
    for key, kind in (("name", str), ("unit", str), ("inverted", bool)):
        if key in data:
            setattr(stat, key, _typed(data[key], kind, f"identification {key}"))
    return stat


def _identification_dict(stat: Identification) -> dict:
    """Only what the stat table would not fill in again: a known stat is just its key, value and roll."""
    out = {"stat": stat.key or stat.name, "value": stat.value}
    if stat.roll is not None:
        out["roll"] = stat.roll
    known = Identification.from_api(out["stat"], stat.value)
    for key in ("name", "unit", "inverted"):
        if getattr(stat, key) != getattr(known, key):
            out[key] = getattr(stat, key)
    return out


def _range(value, key: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{key} must be a [low, high] pair")
    return _typed(value[0], int, key), _typed(value[1], int, key)


def _known(data: dict, keys, where: str) -> dict:
    unknown = sorted(set(data) - set(keys))
    if unknown:
        raise ValueError(f"unknown {where} key: {unknown[0]}")
    return data


def _typed(value, kind, key: str):
    """`value` when it is of `kind`; a bool never passes for a number, though Python counts it as an int."""
    if isinstance(value, bool) and kind is not bool or not isinstance(value, kind):
        raise ValueError(f"{key} must be {_KINDS[kind]}")
    return value
