"""Items the way Wynntils shares them in chat: a run of private-use characters the mod turns into an item.

Wynntils packs an item into bytes, two per character from Unicode's Supplementary Private Use Area-A
(U+F0000 on), with Area-B for an odd last byte and two edge values. The bytes are blocks, each a
one-byte id and its data: start (format version), type, name, identifications, powders, rerolls,
shiny, and for crafted gear its type, durability, requirements, damage, defence and stats, then end.
After Wynntils' ItemEncodingModel and models/items/encoding; `encode` writes format version 3, which
stores identification values directly, and `decode` also reads versions 1 and 2.

A named gear item travels as its name with its identifications, rerolls, shiny and powders; the mod
fills in everything else from its own item database. With extended encoding each identification also
carries its base value, so changed bases arrive as they were. Crafted gear carries all of its stats,
and its name follows the code as ordinary quoted chat text.

`decode` and `encode` speak plain dicts:

    {"kind": "gear", "name": "Weathered", "extended": False,
     "identifications": [{"stat": "MISC_MANA_STEAL", "value": 10, "base": None, "fixed": False}],
     "rerolls": 2, "shiny": {"name": "Mobs Killed", "value": 120}, "powder_slots": 3, "powders": [["fire", 6]]}

Crafted gear (`"kind": "crafted"`) adds `type`, `attack_speed`, `average_dps`, `damage`, `health`,
`defence` and `requirements` in the shape `spec.from_dict` uses. `to_item` turns a decoded dict into
an `Item`, filling a gear item's base data from the item API when it is given.

The stat and shiny ids come from Wynntils' static data (Reference/id_keys.json and
Data-Storage/shiny_stats.json on cdn.wynntils.com), kept in `assets/wynntils`.
"""
import functools
import json
import re
from pathlib import Path

from . import rolls, stats
from .model import Identification, Item, Requirements, Shiny
from .sources import from_wynnpool

START, TYPE, NAME, IDENTIFICATIONS, POWDERS, REROLLS, SHINY = 0, 1, 2, 3, 4, 5, 6
GEAR_TYPE, DURABILITY, REQUIREMENTS, DAMAGE, DEFENCE, CUSTOM_IDENTIFICATIONS, END = 7, 8, 9, 10, 11, 12, 255
VERSION = 2  # format version 3; its id byte is 2
KINDS = {0: "gear", 3: "crafted"}  # 1 tome, 2 charm, 4 crafted consumable, 5 mount: not cards this library draws
GEAR_TYPES = ("spear", "wand", "dagger", "bow", "relik", "ring", "bracelet", "necklace",
              "helmet", "chestplate", "leggings", "boots")
CLASSES = ("", "mage", "archer", "warrior", "assassin", "shaman")
ELEMENTS = ("earth", "thunder", "water", "fire", "air")  # Wynntils' ETWFA order, also the damage types 0-4
DAMAGE_TYPES = ELEMENTS + ("neutral",)
ATTACK_SPEEDS = ("superFast", "veryFast", "fast", "normal", "slow", "verySlow", "superSlow")
VANILLA_METER = 4  # identification flag: one more byte, the game's own roll meter, follows

_AREA_A, _AREA_B = 0xF0000, 0x100000
_CODE = re.compile("(?P<data>[\U000F0000-\U000FFFFD\U00100000-\U0010FFFD]+)(?: \"(?P<name>[^\"]+)\")?")
_SAFE_NAME = re.compile(r"[a-zA-Z0-9'\-.,!? ]{1,50}")  # what Wynntils shows of a crafted name
_ASSETS = Path(__file__).parent / "assets" / "wynntils"


@functools.cache
def _stat_ids() -> dict[str, int]:
    """Wynntils' numeric key of each stat, by Wynntils stat key."""
    by_api = json.loads((_ASSETS / "id_keys.json").read_text())
    return {stat.key: by_api[stat.api] for stat in stats.TYPES if stat.api in by_api}


@functools.cache
def _shiny_names() -> dict[int, str]:
    return {int(key): name for key, name in json.loads((_ASSETS / "shiny_stats.json").read_text()).items()}


def decode(text: str) -> dict:
    """The item in the first Wynntils code found in `text`; ValueError when there is none or it is broken."""
    match = _CODE.search(text)
    if match is None:
        raise ValueError("no Wynntils item code in the text")
    reader = _Reader(_to_bytes(match["data"]))
    if reader.byte() != START:
        raise ValueError("a Wynntils item code begins with a start block")
    version = reader.byte()
    if version > VERSION:
        raise ValueError(f"Wynntils item format {version + 1} is newer than this library knows")
    out = {"kind": "", "name": match["name"] or "", "extended": False, "identifications": [], "rerolls": 0,
           "shiny": None, "powder_slots": 0, "powders": []}
    while (block := reader.byte()) != END:
        _BLOCKS.get(block, _unknown_block)(reader, version, out)
    if not out["kind"]:
        raise ValueError("the Wynntils item code has no type block")
    return out


def encode(data: dict) -> str:
    """The Wynntils chat code for a gear or crafted item given as `decode` returns it."""
    kind = data.get("kind")
    out = bytearray([START, VERSION, TYPE, {"gear": 0, "crafted": 3}.get(kind, 255)])
    if kind == "gear":
        name = data.get("name") or ""
        if not name or not name.isascii():
            raise ValueError("a gear item needs its name in plain ASCII")
        out += bytes([NAME]) + name.encode("ascii") + b"\0"
        out += _identifications(data.get("identifications") or [], bool(data.get("extended")))
        out += _powders(data)
        if data.get("rerolls"):
            out += bytes([REROLLS, min(int(data["rerolls"]), 255)])
        out += _shiny(data.get("shiny"))
    elif kind == "crafted":
        out += _crafted(data)
        out += _powders(data)
    else:
        raise ValueError("kind must be gear or crafted")
    text = _to_text(bytes(out) + bytes([END]))
    name = (data.get("name") or "").strip()
    if kind == "crafted" and _SAFE_NAME.fullmatch(name):
        text += f' "{name}"'
    return text


def to_item(decoded: dict, info: dict | None = None) -> Item:
    """The card of a decoded item. For gear, `info` is its Wynncraft or Wynnpool item: base data and bases."""
    if decoded["kind"] == "crafted":
        item = Item(decoded["name"] or f"Crafted {decoded.get('type', '').title()}".strip(),
                    kind=_kind(decoded.get("type", "")), type=decoded.get("type", ""),
                    attack_speed=decoded.get("attack_speed", ""), average_dps=decoded.get("average_dps"),
                    health=decoded.get("health"), damage={k: tuple(v) for k, v in decoded.get("damage", {}).items()},
                    defence=dict(decoded.get("defence", {})),
                    requirements=Requirements(**decoded.get("requirements", {})))
        item.identifications = [Identification.from_api(stat["stat"], stat["value"])
                                for stat in decoded["identifications"]]
    else:
        item = from_wynnpool(info) if info else Item(decoded["name"])
        bases = {}
        for api, value in ((info or {}).get("identifications") or {}).items():
            stat = stats.lookup(api)
            if stat is not None:
                bases[stat.key] = (value["raw"], False) if isinstance(value, dict) else (value, True)
        identifications = []
        for stat in decoded["identifications"]:
            base, fixed = (stat["base"], stat["fixed"]) if stat["base"] is not None else bases.get(stat["stat"], (None, False))
            value = stat["value"]
            if value is None:  # versions 1 and 2: the value comes from the internal roll and the base
                if base is None:
                    continue
                value = rolls.value_at(base, stat["internal_roll"], stats.lookup(stat["stat"]).inverted)
            found = Identification.from_api(stat["stat"], value)
            if base is not None and not fixed:
                found.roll = rolls.percentage(value, base, found.inverted)
            identifications.append(found)
        decoded_keys = {stat["stat"] for stat in decoded["identifications"]}
        for key, (base, fixed) in bases.items():  # the code leaves out stats that never roll
            if fixed and key not in decoded_keys:
                identifications.append(Identification.from_api(key, base))
        item.identifications = identifications
        rolled = [stat.roll for stat in identifications if stat.roll is not None]
        item.overall_roll = sum(rolled) / len(rolled) if rolled else None
        item.rerolls = decoded["rerolls"]
    if decoded["shiny"]:
        item.shiny = Shiny(decoded["shiny"]["name"], decoded["shiny"]["value"])
    return item


# ---------------------------------------------------------------- decoding blocks

class _Reader:
    def __init__(self, data: bytes):
        self.data, self.position = data, 0

    def byte(self) -> int:
        if self.position >= len(self.data):
            raise ValueError("the Wynntils item code ends too early")
        self.position += 1
        return self.data[self.position - 1]

    def varint(self) -> int:
        """Zig-zag LEB128, as UnsignedByteUtils.decodeVariableSizedInteger."""
        value = shift = 0
        while True:
            byte = self.byte()
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                return (value >> 1) ^ -(value & 1)

    def text(self) -> str:
        end = self.data.find(b"\0", self.position)
        if end < 0:
            raise ValueError("the item name is not terminated")
        value, self.position = self.data[self.position:end].decode("ascii", "replace"), end + 1
        return value


def _type(reader: _Reader, version: int, out: dict) -> None:
    kind = reader.byte()
    if kind not in KINDS:
        raise ValueError("only gear and crafted gear can become a card; this Wynntils item is something else")
    out["kind"] = KINDS[kind]


def _name(reader: _Reader, version: int, out: dict) -> None:
    name = reader.text()
    if out["kind"] != "crafted":  # Wynntils takes a crafted item's name from the chat text, never from the code
        out["name"] = name


def _identification_list(reader: _Reader, version: int, out: dict) -> None:
    count, extended = reader.byte(), reader.byte() == 1
    fixed_count = reader.byte() if extended else 0
    out["extended"] = extended
    for index in range(fixed_count + count):
        stat = _stat(reader.byte())
        fixed = index < fixed_count
        base = reader.varint() if extended else None
        if fixed:
            out["identifications"].append({"stat": stat, "value": base, "base": base, "fixed": True})
            continue
        if version < 2:  # versions 1 and 2 carry the internal roll, not the value
            out["identifications"].append({"stat": stat, "value": None, "base": base, "fixed": False,
                                           "internal_roll": reader.byte()})
            continue
        value = reader.varint()
        if reader.byte() & VANILLA_METER:
            reader.byte()
        out["identifications"].append({"stat": stat, "value": value, "base": base, "fixed": False})


def _powder_list(reader: _Reader, version: int, out: dict) -> None:
    slots, count = reader.byte(), reader.byte()
    bits = "".join(f"{reader.byte():08b}" for _ in range((count * 5 + 7) // 8))
    powders = []
    for index in range(min(count, slots)):
        value = int(bits[index * 5:index * 5 + 5], 2)
        if value:
            element, tier = divmod(value, 6)
            if tier == 0:  # a tier 6 powder is written as tier 0 of the next element
                element, tier = element - 1, 6
            powders.append([ELEMENTS[element], tier])
    out["powder_slots"], out["powders"] = slots, powders


def _rerolls(reader: _Reader, version: int, out: dict) -> None:
    out["rerolls"] = reader.byte()


def _shiny_stat(reader: _Reader, version: int, out: dict) -> None:
    stat = reader.byte()
    if version >= 1:
        reader.byte()  # shiny rerolls, which the card does not show
    out["shiny"] = {"name": _shiny_names().get(stat, "Shiny"), "value": reader.varint()}


def _gear_type(reader: _Reader, version: int, out: dict) -> None:
    out["type"] = GEAR_TYPES[reader.byte()]


def _durability(reader: _Reader, version: int, out: dict) -> None:
    if version < 2:
        reader.byte()  # the old crafted effectiveness
    reader.varint(), reader.varint()


def _requirements(reader: _Reader, version: int, out: dict) -> None:
    requirements = {"level": reader.byte(), "class_name": CLASSES[reader.byte()]}
    for _ in range(reader.byte()):
        skill = stats.SKILLS[reader.byte()]  # read before the value: an assignment evaluates its right side first
        requirements[skill] = reader.varint()
    out["requirements"] = requirements


def _damage(reader: _Reader, version: int, out: dict) -> None:
    if version >= 2:
        out["average_dps"] = reader.varint()
    out["attack_speed"] = ATTACK_SPEEDS[reader.byte()]
    out["damage"] = {}
    for _ in range(reader.byte()):
        element = DAMAGE_TYPES[reader.byte()]
        out["damage"][element] = [reader.varint(), reader.varint()]


def _defence(reader: _Reader, version: int, out: dict) -> None:
    out["health"] = reader.varint()
    out["defence"] = {ELEMENTS[reader.byte()]: reader.varint() for _ in range(reader.byte())}


def _custom_identifications(reader: _Reader, version: int, out: dict) -> None:
    for _ in range(reader.byte()):
        stat = _stat(reader.byte())
        value = reader.varint()  # versions 1 and 2 stored the maximum, version 3 the value
        if version >= 2 and reader.byte() & VANILLA_METER:
            reader.byte()
        out["identifications"].append({"stat": stat, "value": value, "base": None, "fixed": False})


def _unknown_block(reader: _Reader, version: int, out: dict) -> None:
    raise ValueError(f"unknown block {reader.data[reader.position - 1]} in the Wynntils item code")


_BLOCKS = {TYPE: _type, NAME: _name, IDENTIFICATIONS: _identification_list, POWDERS: _powder_list,
           REROLLS: _rerolls, SHINY: _shiny_stat, GEAR_TYPE: _gear_type, DURABILITY: _durability,
           REQUIREMENTS: _requirements, DAMAGE: _damage, DEFENCE: _defence,
           CUSTOM_IDENTIFICATIONS: _custom_identifications}


def _stat(wynntils_id: int) -> str:
    """Our stat key for a Wynntils numeric key, or the key itself as text when the table lacks it."""
    return next((key for key, number in _stat_ids().items() if number == wynntils_id), f"wynntils:{wynntils_id}")


# ---------------------------------------------------------------- encoding blocks

def _identifications(identifications: list[dict], extended: bool) -> bytes:
    rolled = [stat for stat in identifications if not stat.get("fixed")]
    fixed = [stat for stat in identifications if stat.get("fixed")] if extended else []
    out = bytearray([IDENTIFICATIONS, len(rolled), int(extended)])
    if extended:
        out.append(len(fixed))
        for stat in fixed:
            base = stat["value"] if stat.get("base") is None else stat["base"]
            out += bytes([_stat_id(stat["stat"])]) + _varint(_whole(base))
    for stat in rolled:
        out.append(_stat_id(stat["stat"]))
        if extended:
            if stat.get("base") is None:
                raise ValueError(f"extended encoding needs the base of {stat['stat']}")
            out += _varint(_whole(stat["base"]))
        out += _varint(_whole(stat["value"])) + b"\0"  # no flags: no perfect roll mark, icon or meter
    return bytes(out) if rolled or fixed else b""


def _powders(data: dict) -> bytes:
    powders, slots = data.get("powders") or [], int(data.get("powder_slots") or 0)
    if not powders and not slots:
        return b""
    bits = "".join(f"{ELEMENTS.index(element) * 6 + tier:05b}" for element, tier in powders)
    bits += "0" * (-len(bits) % 8)
    return bytes([POWDERS, slots, len(powders)]) + bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def _shiny(shiny: dict | None) -> bytes:
    if not shiny:
        return b""
    stat = next((number for number, name in _shiny_names().items() if name == shiny.get("name")), None)
    if stat is None:
        raise ValueError(f"Wynntils has no shiny tracker called {shiny.get('name')}")
    return bytes([SHINY, stat, 0]) + _varint(_whole(shiny["value"]))


def _crafted(data: dict) -> bytes:
    if data.get("type") not in GEAR_TYPES:
        raise ValueError("crafted gear needs one of the twelve gear types")
    out = bytearray([GEAR_TYPE, GEAR_TYPES.index(data["type"])])
    out += bytes([DURABILITY]) + _varint(100) + _varint(100)
    requirements = data.get("requirements") or {}
    skills = [(index, requirements[skill]) for index, skill in enumerate(stats.SKILLS) if requirements.get(skill)]
    out += bytes([REQUIREMENTS, min(max(int(requirements.get("level") or 0), 0), 255),
                  CLASSES.index(requirements.get("class_name") or ""), len(skills)])
    for index, value in skills:
        out += bytes([index]) + _varint(_whole(value))
    damage = data.get("damage") or {}
    if damage or data.get("attack_speed") or data.get("average_dps"):
        out += bytes([DAMAGE]) + _varint(_whole(data.get("average_dps") or 0))
        out += bytes([ATTACK_SPEEDS.index(data.get("attack_speed") or "normal"), len(damage)])
        for element, (low, high) in damage.items():
            out += bytes([DAMAGE_TYPES.index(element)]) + _varint(_whole(low)) + _varint(_whole(high))
    defence = data.get("defence") or {}
    if data.get("health") or defence:
        out += bytes([DEFENCE]) + _varint(_whole(data.get("health") or 0)) + bytes([len(defence)])
        for element, value in defence.items():
            out += bytes([ELEMENTS.index(element)]) + _varint(_whole(value))
    identifications = data.get("identifications") or []
    if identifications:
        out += bytes([CUSTOM_IDENTIFICATIONS, len(identifications)])
        for stat in identifications:
            out += bytes([_stat_id(stat["stat"])]) + _varint(_whole(stat["value"])) + b"\0"
    return bytes(out)


def _stat_id(key: str) -> int:
    stat = stats.lookup(key)
    if stat is None or stat.key not in _stat_ids():
        raise ValueError(f"Wynntils has no key for the stat {key}")
    return _stat_ids()[stat.key]


def _whole(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise ValueError(f"{value!r} is not a whole number")
    return int(value)


def _varint(value: int) -> bytes:
    """Zig-zag LEB128, as UnsignedByteUtils.encodeVariableSizedInteger."""
    value = (value << 1) ^ (value >> 63)
    out = bytearray()
    while True:
        byte, value = value & 0x7F, value >> 7
        if not value:
            return bytes(out + bytes([byte]))
        out.append(byte | 0x80)


def _kind(gear_type: str) -> str:
    index = GEAR_TYPES.index(gear_type) if gear_type in GEAR_TYPES else -1
    return "weapon" if 0 <= index < 5 else "accessory" if 5 <= index < 8 else "armour" if index >= 8 else ""


# ---------------------------------------------------------------- bytes and characters

def _to_text(data: bytes) -> str:
    """Two bytes per character, as EncodedByteBuffer.toUtf16String."""
    out = []
    for index in range(0, len(data) - 1, 2):
        high, low = data[index], data[index + 1]
        out.append(chr(_AREA_B + low - 254) if high == 255 and low >= 254 else chr(_AREA_A + (high << 8 | low)))
    if len(data) % 2:  # an odd last byte gets its own Area-B character
        out.append(chr(_AREA_B + (data[-1] << 8) + 0xEE))
    return "".join(out)


def _to_bytes(text: str) -> bytes:
    """The bytes behind the characters, as EncodedByteBuffer.fromUtf16String."""
    out = bytearray()
    for char in text:
        point = ord(char)
        if point >= _AREA_B:
            if point & 0xFF == 0xEE:
                out.append((point - _AREA_B - 0xEE) >> 8)
            else:
                out += bytes([255, 254 + ((point - _AREA_B) & 0xFF)])
        else:
            value = point - _AREA_A
            out += bytes([value >> 8, value & 0xFF])
    return bytes(out)
