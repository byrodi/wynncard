"""The item tooltip as the game draws it, line for line after Wynntils' IdentifiableTooltipBuilder.

A line is a list of runs, each `(text, font id, colour)`; a run with colour `None` only moves the pen.
Lines come in three shapes: fixed (drawn at the left edge), centered, and aligned (left part at the
edge, right part flush right). Spacing is done with the game's own space font, so glyphs sit exactly
where Wynntils puts them, and everything is laid out in Minecraft pixels and scaled up at the end.

Requirement marks are drawn neutral: the card describes an item, not whether some character can wear it.
"""
import functools
import json
import math
import re

from . import mcfont

TEXT_FONT = "language/wynncraft"
SPRITE = "tooltip/attribute/sprite"
EMBLEM_FRAME, EMBLEM_SPRITE = "tooltip/emblem/frame", "tooltip/emblem/sprite"
REQ_FRAME, REQ_SPRITE = "tooltip/requirement/frame", "tooltip/requirement/sprite"
DIVIDER_FONT, MAJOR_FONT, BANNER_FONT = "tooltip/divider", "tooltip/identification/major", "tooltip/banner"
BOX_FONT, ICON_FONT, COMMON_FONT = "banner/box", "wynntils/icons", "common"

WHITE, GRAY, DARK_GRAY, BLACK = "#ffffff", "#aaaaaa", "#555555", "#000000"
GREEN, RED, ORANGE = "#acfac6", "#faacac", "#fac6ac"
RAINBOW = ("#ff5b74", "#ffd760", "#32ff70", "#3ff2ff", "#efb0ff")
SCALE_COLORS = ((20.0, (0xFF, 0x55, 0x55)), (50.0, (0xFF, 0xAA, 0x00)), (80.0, (0xFF, 0xFF, 0x55)),
                (95.0, (0x55, 0xFF, 0x55)), (100.0, (0x55, 0xFF, 0xFF)))  # the percentage scale, lerped between stops
SKILL_CELL = 27  # the width Wynntils centres each requirement column in

TIERS = {  # name colour, secondary colour (dividers, DPS, tags)
    "normal": ("#ffffff", "#e0e0e0"), "unique": ("#ffff55", "#fff2b3"), "rare": ("#ff55ff", "#f2c2f2"),
    "legendary": ("#55ffff", "#cff9f9"), "fabled": ("#ff5555", "#f2c2c2"), "mythic": ("#aa00aa", "#e0b3e6"),
}
TIER_ORDER = ("normal", "unique", "rare", "legendary", "fabled", "mythic")
ELEMENTS = {  # attribute sprite, banner glyph, banner overlay, colour
    "earth": ("", "", "", "#00aa00"), "thunder": ("", "", "", "#ffff55"),
    "water": ("", "", "", "#55ffff"), "fire": ("", "", "", "#ff5555"),
    "air": ("", "", "", "#ffffff"), "neutral": ("", "", "", "#ffaa00"),
}
SKILLS = ("strength", "dexterity", "intelligence", "defence", "agility")
STAT_SKILL_NUDGE = {"strength": -1, "intelligence": -1, "defence": 1}  # per-sprite kerning
TYPE_SPRITES = {"helmet": "", "chestplate": "", "leggings": "", "boots": "", "bow": "",
                "dagger": "", "wand": "", "relik": "", "spear": "", "ring": "",
                "bracelet": "", "necklace": ""}
EMBLEM_SHAPES = ("diamond", "square", "hexagon", "shield", "sticker", "circle")
HITS = {"superSlow": 0.51, "verySlow": 0.83, "slow": 1.21, "normal": 2.05, "fast": 2.5, "veryFast": 3.1,
        "superFast": 4.3}
UNITS = {"PERCENT": "%", "RAW": "", "PER_3_S": "/3s", "PER_5_S": "/5s", "TIER": " tier"}
CLASSES = {
    "warrior": ("Warrior/Knight", ("Bash", "Charge", "Uppercut", "War Scream")),
    "mage": ("Mage/Dark Wizard", ("Heal", "Teleport", "Meteor", "Ice Snake")),
    "archer": ("Archer/Hunter", ("Arrow Storm", "Escape", "Bomb Arrow", "Arrow Shield")),
    "assassin": ("Assassin/Ninja", ("Spin Attack", "Vanish", "Multihit", "Smoke Bomb")),
    "shaman": ("Shaman/Skyseer", ("Totem", "Haul", "Aura", "Uproot")),
}
ORDINALS = ("FIRST", "SECOND", "THIRD", "FOURTH")
GROUPS = (("SKILL_", "DAMAGE_"), ("MISC_HEALTH", "MISC_LIFE_STEAL", "MISC_MANA"), ("DEFENCE_",),
          ("MISC_WALK_SPEED", "MISC_SPRINT", "MISC_JUMP"), ("SPELL_",))


def offset(pixels: int) -> str:
    """A space-font glyph that moves the pen by this many pixels."""
    return chr(0xD0000 + pixels)


def space(pixels: int) -> tuple:
    return (offset(pixels), "space", None)


def scale_color(percentage: float, lerp: bool = True) -> str:
    """The percentage colour on the mod's default scale.

    With `lerp` the colour slides between the stops; without it the stop above the value wins, which is
    the flat five-colour look Wynntils shows when colour lerping is off.
    """
    if percentage >= 100:
        return "rainbow"
    if not lerp:
        stop = next((rgb for edge, rgb in SCALE_COLORS if percentage < edge), SCALE_COLORS[-1][1])
        return "#%02x%02x%02x" % stop
    if percentage <= SCALE_COLORS[0][0]:
        return "#%02x%02x%02x" % SCALE_COLORS[0][1]
    for (low, low_rgb), (high, high_rgb) in zip(SCALE_COLORS, SCALE_COLORS[1:]):
        if percentage <= high:
            t = (percentage - low) / (high - low)
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * t) for a, b in zip(low_rgb, high_rgb))
    return "#%02x%02x%02x" % SCALE_COLORS[-1][1]


def fixed(runs):
    return ("fixed", runs)


def centered(runs):
    return ("centered", runs)


def aligned(left, right):
    return ("aligned", left, right)


def text(value, color=WHITE):
    return (value, TEXT_FONT, color)


@functools.cache
def _box_glyphs() -> dict:
    return json.loads((mcfont.ASSETS / "font" / "banner" / "box_map.json").read_text())["glyphs"]


def banner(label: str, background: str, foreground: str = BLACK, suffix: tuple | None = None) -> list:
    """A boxed tag: the banner background first, then the letters printed back over it."""
    glyphs = _box_glyphs()
    label = label.lower()
    back = glyphs["left_edge"] + offset(-1)
    for char in label:
        back += (glyphs["space"] if char == " " else glyphs.get(char + "_background", glyphs["space"]))
        back += offset(-1)
    back += glyphs["right_edge"]
    letters = "".join(" " if char == " " else glyphs.get(char + "_foreground", " ") for char in label)
    runs = [(back, BOX_FONT, background), space(2 - mcfont.width(BOX_FONT, back)), (letters, BOX_FONT, foreground)]
    return runs + [suffix] if suffix else runs


# ---------------------------------------------------------------- sections

def _name(item: dict, info: dict, tier: str, lerp: bool) -> list:
    shape, _, variant = (info.get("emblem") or "diamond_1").partition("_")
    frame = chr(0xE000 + (int(variant or 1) - 1) * 0x10 + EMBLEM_SHAPES.index(shape))
    sprite = TYPE_SPRITES.get((info.get("subType") or "").lower(), "")
    runs = [space(-16), (frame, EMBLEM_FRAME, TIERS[tier][1]), space(-49), (sprite, EMBLEM_SPRITE, WHITE),
            space(5), text(item.get("name") or "?", TIERS[tier][0])]
    overall = item.get("overall_roll")
    if overall is not None:
        runs.append(text(f" [{overall:.1f}%]", scale_color(overall, lerp)))
    return runs


def _tags(item: dict, info: dict, tier: str) -> list:
    """The rarity and type banners, and the element strip under them."""
    kind = (info.get("subType") or item.get("type") or "").upper()
    lines = [fixed([space(38)] + banner(tier, TIERS[tier][0]) + [space(1)] + banner(kind, TIERS[tier][1]))]
    elements = info.get("elements") or []
    if not elements:
        return lines
    runs = [space(38)]
    for index, element in enumerate(elements):
        _, glyph, overlay, color = ELEMENTS[element]
        runs += [(glyph, BANNER_FONT, TIERS[tier][1]), space(-10), (overlay, BANNER_FONT, WHITE)]
        if index < len(elements) - 1:
            runs.append(space(-1))
    if len(elements) == 1:
        runs += [space(-1)] + banner(elements[0], TIERS[tier][1])
    return lines + [fixed(runs)]


def _overview(info: dict, tier: str) -> list:
    lines = []
    base = info.get("base") or {}
    if info.get("type") == "weapon" and info.get("averageDps") is not None:
        lines.append(fixed([text(f"{info['averageDps']:,}", TIERS[tier][1]), text(" DPS")]))
    elif base.get("baseHealth") is not None:
        health = base["baseHealth"]
        raw = health.get("raw", health.get("max")) if isinstance(health, dict) else health
        lines.append(fixed([text(f"{raw:+,}", TIERS[tier][1]), text(" Health")]))
    speed = info.get("attackSpeed")
    if speed:
        label = re.sub(r"(?<!^)([A-Z])", r" \1", speed).title()
        lines.append(fixed([("", SPRITE, WHITE), text(f" {label} ", GRAY),
                            text(f"({HITS.get(speed, 0)} hits/s)", DARK_GRAY)]))
    damage, defence = [], []
    for key, value in base.items():
        element = key.replace("base", "").replace("Damage", "").replace("Defence", "").lower() or "neutral"
        if element not in ELEMENTS:
            continue
        glyph, _, _, color = ELEMENTS[element]
        if key.endswith("Damage"):
            damage += [(glyph, SPRITE, color), text(f" {value['min']:,}-{value['max']:,} ", GRAY)]
        elif key.endswith("Defence"):
            raw = value.get("raw", value.get("max")) if isinstance(value, dict) else value
            defence += [(glyph, SPRITE, color), text(f" {raw:+,} ", GRAY)]
    return lines + ([fixed(damage)] if damage else []) + ([fixed(defence)] if defence else [])


def _divider(tier: str) -> tuple:
    return centered([("", DIVIDER_FONT, TIERS[tier][1])])


def _weights(scales: list[dict], lerp: bool) -> list:
    if not scales:
        return []
    lines = [fixed([("", ICON_FONT, ORANGE), text(" Wynnpool")])]
    for scale in scales:
        lines.append(aligned([text(f"{scale['profile']} Scale")],
                             [text(f" [{scale['score']:.1f}%]", scale_color(scale["score"], lerp))]))
    return lines


def _requirement(label: str, value: str) -> tuple:
    return aligned([("", REQ_SPRITE, WHITE), space(-1), text(f" {label}")], [text(value, GRAY)])


def _requirements(info: dict, tier: str) -> list:
    req = info.get("requirements") or {}
    if not req:
        return []
    lines = []
    skills = [(skill, req.get(skill) or 0) for skill in SKILLS]
    if any(value for _, value in skills):
        frame = chr(0xE000 + TIER_ORDER.index(tier))
        icons, values = [], []
        for index, (_, value) in enumerate(skills):
            icons += [(frame if value else "", REQ_FRAME, WHITE), space(-25),
                      (chr((0xE000 if value else 0xE010) + index), REQ_SPRITE, WHITE), space(2)]
            cell = [("", REQ_SPRITE, WHITE), space(-1), space(3), text(str(value), DARK_GRAY if not value else GRAY)]
            width = sum(mcfont.width(font_id, value_text) for value_text, font_id, _ in cell)
            left = max(0, (SKILL_CELL - width) // 2)
            values += [space(left)] + cell + [space(max(0, SKILL_CELL - width - left))]
        lines += [fixed([]), centered(icons), fixed([]), centered(values), fixed([])]
    if req.get("classRequirement"):
        lines.append(_requirement("Class Type", CLASSES.get(req["classRequirement"],
                                                            (req["classRequirement"].title(), ()))[0]))
    if req.get("level"):
        lines.append(_requirement("Combat Level", str(req["level"])))
    return lines


def _shiny(item: dict, tier: str) -> list:
    shiny = item.get("shiny_stat")
    if not isinstance(shiny, dict):
        return []
    name = (shiny.get("statType") or {}).get("displayName") or "Shiny"
    return [_divider(tier),
            aligned([("", COMMON_FONT, TIERS[tier][1]), text(f" {name}", TIERS[tier][1])],
                    [text(f"{shiny.get('value', 0):,}")])]


def _reroll(item: dict, tier: str) -> list:
    rerolls = item.get("reroll_count") or 0
    if rerolls <= 0:
        return []
    color = TIERS[tier][1]
    runs = banner(str(rerolls), color, BLACK, space(2)) + [
        space(-1), ("", BANNER_FONT, color), space(-10), ("", BANNER_FONT, WHITE)]
    return [aligned([], runs)]


def _stats(item: dict, spells: tuple, lerp: bool) -> list:
    found = []
    for roll in item.get("stat_rolls") or []:
        actual = roll.get("statActualValue") or {}
        stat_type = actual.get("statType") or {}
        value, key = actual.get("value"), stat_type.get("key") or ""
        if value is None:
            continue
        try:
            percentage = float(roll.get("rollPercentage"))
        except (TypeError, ValueError):
            percentage = math.nan
        name = stat_type.get("displayName") or key
        if key.startswith("SPELL_"):
            value = -value  # the API counts a cost reduction up, the tooltip shows it as a negative cost
            spell = next((spells[i] for i, word in enumerate(ORDINALS) if word in key and i < len(spells)), None)
            name = f"{spell} Cost" if spell else name
        group = next(((i, p.index(next(x for x in p if key.startswith(x))))
                      for i, p in enumerate(GROUPS) if key.startswith(p)), (len(GROUPS) - 1.5, 0))
        found.append((group, key, name, value, UNITS.get(stat_type.get("unit"), ""), percentage))

    lines, last = [], None
    for group, key, name, value, unit, percentage in sorted(found, key=lambda f: f[0]):
        if last is not None and group[0] != last[0]:
            lines.append(fixed([]))
        last = group
        left = []
        if key.startswith("SKILL_"):
            skill = key.split("SKILL_")[1].lower()
            index = SKILLS.index(skill)
            left = [space(STAT_SKILL_NUDGE.get(skill, 0)), (chr(0xE010 + index), SPRITE, WHITE), space(2), text(" ")]
        left.append(text(f"{name} "))
        positive = value < 0 if key.startswith("SPELL_") else value > 0
        right = [text(f"{value:+g}{unit}", GREEN if positive else RED)]
        if not math.isnan(percentage):
            right.append(text(f" [{percentage:.1f}%]", scale_color(percentage, lerp)))
        lines.append(aligned(left, right))
    return lines


def _major_ids(info: dict, tier: str) -> list:
    lines = []
    for name, lore in (info.get("majorIds") or {}).items():
        body = re.sub(r"<[^>]+>", "", lore).strip()
        lines += [fixed([]), ("wrap", [("", MAJOR_FONT, TIERS[tier][1]), space(2),
                                       text(f"{name}: ", TIERS[tier][1]), text(body, GRAY)])]
    return lines


def build(item: dict, info: dict, scales: list[dict], color_lerp: bool = True) -> list:
    """Every tooltip line, in the order Wynntils assembles the sections."""
    tier = (item.get("rarity") or info.get("tier") or "normal").lower()
    if tier not in TIERS:
        tier = "normal"
    lines = [fixed([]), fixed(_name(item, info, tier, color_lerp))] + _tags(item, info, tier) + [fixed([])]
    lines += _overview(info, tier)
    weights = _weights(scales, color_lerp)
    if weights:
        lines += [_divider(tier)] + weights
    lines.append(_divider(tier))
    lines += _requirements(info, tier)
    lines += _shiny(item, tier)
    lines.append(_divider(tier))
    lines += _reroll(item, tier)
    req = info.get("requirements") or {}
    lines += _stats(item, CLASSES.get(req.get("classRequirement") or "", ("", ()))[1], color_lerp)
    lines += _major_ids(info, tier)
    return lines


def line_width(line: tuple) -> int:
    runs = line[1] if line[0] != "aligned" else line[1] + line[2]
    return sum(mcfont.width(font_id, value) for value, font_id, _ in runs)
