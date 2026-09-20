"""The item tooltip as the game draws it, line for line after Wynntils' IdentifiableTooltipBuilder.

The output is a list of `Line`s. A line is a list of runs, each `(text, font id, colour)`; a run with
colour `None` only moves the pen. Lines come in four shapes: `left` (drawn at the left edge), `center`,
`aligned` (left part at the edge, right part flush right) and `wrap` (a paragraph the renderer breaks
to the tooltip width). Spacing uses the game's own space font, so glyphs sit exactly where Wynntils puts
them, and everything is laid out in Minecraft pixels; `render` scales it up at the end.

Requirement marks are drawn neutral: the card describes an item, not whether some character can wear it.
"""
import functools
import json
import math
import re
from typing import NamedTuple

from . import mcfont, stats
from .model import Item

# Font ids, as `assets/mc/font/<id>.json`.
TEXT_FONT = "language/wynncraft"
SPRITE = "tooltip/attribute/sprite"                                   # element, skill and attack speed icons
EMBLEM_FRAME, EMBLEM_SPRITE = "tooltip/emblem/frame", "tooltip/emblem/sprite"
REQ_FRAME, REQ_SPRITE = "tooltip/requirement/frame", "tooltip/requirement/sprite"
DIVIDER_FONT, MAJOR_FONT, BANNER_FONT = "tooltip/divider", "tooltip/identification/major", "tooltip/banner"
BOX_FONT, ICON_FONT, COMMON_FONT = "banner/box", "wynntils/icons", "common"

# Colours. GREEN/RED tint identification values; RAINBOW cycles over a 100 % roll.
WHITE, GRAY, DARK_GRAY, BLACK = "#ffffff", "#aaaaaa", "#555555", "#000000"
GREEN, RED, ORANGE, RESTRICTION_RED = "#acfac6", "#faacac", "#fac6ac", "#ff4242"
RAINBOW = ("#ff5b74", "#ffd760", "#32ff70", "#3ff2ff", "#efb0ff")
_RED, _GOLD, _YELLOW, _GREEN, _AQUA = (0xFF, 0x55, 0x55), (0xFF, 0xAA, 0x00), (0xFF, 0xFF, 0x55), (0x55, 0xFF, 0x55), (0x55, 0xFF, 0xFF)
FLAT_STOPS = ((20.0, _RED), (50.0, _GOLD), (80.0, _YELLOW), (95.0, _GREEN), (math.inf, _AQUA))  # the stop above wins
LERP_STOPS = ((0.0, _RED), (40.0, _GOLD), (70.0, _YELLOW), (90.0, _GREEN), (100.0, _AQUA))  # ItemStatInfoFeature

# Tier -> (name colour, secondary colour for dividers, DPS and the type banner), from Wynntils' GearTier.
TIERS = {
    "normal": ("#ffffff", "#e0e0e0"), "unique": ("#ffff55", "#fff2b3"), "rare": ("#ff55ff", "#f2c2f2"),
    "set": ("#aaaaaa", "#ffffff"), "legendary": ("#55ffff", "#cff9f9"), "fabled": ("#ff5555", "#f2c2c2"),
    "mythic": ("#aa00aa", "#e0b3e6"),
}
FRAMED_TIERS = ("normal", "unique", "rare", "legendary", "fabled", "mythic")  # tiers with their own requirement frame
# Element -> (attribute sprite, banner glyph, banner overlay, colour).
ELEMENTS = {
    "earth": ("", "", "", "#00aa00"), "thunder": ("", "", "", "#ffff55"),
    "water": ("", "", "", "#55ffff"), "fire": ("", "", "", "#ff5555"),
    "air": ("", "", "", "#ffffff"), "neutral": ("", "", "", "#ffaa00"),
}
ATTACK_SPEED_SPRITE = ""
# Skill icon in front of a `SKILL_` identification: (offset before the sprite, gap after it), Wynntils' prefixes.
SKILL_PREFIX = {"strength": (-1, 2), "dexterity": (0, 2), "intelligence": (-1, 2), "defence": (-1, 3), "agility": (0, 2)}
SKILL_CELL = 27  # the width Wynntils centres each requirement column in
TYPE_SPRITES = {"helmet": "", "chestplate": "", "leggings": "", "boots": "", "bow": "",
                "dagger": "", "wand": "", "relik": "", "spear": "", "ring": "",
                "bracelet": "", "necklace": ""}
EMBLEM_SHAPES = ("diamond", "square", "hexagon", "shield", "sticker", "circle")
RESTRICTIONS = {"untradable": ("", ""), "quest_item": ("", "")}  # (banner glyph, overlay)
HITS = {"superSlow": 0.51, "verySlow": 0.83, "slow": 1.21, "normal": 2.05, "fast": 2.5, "veryFast": 3.1, "superFast": 4.3}
# Class -> (full name, spells 1..4), as Wynntils names them.
CLASSES = {
    "warrior": ("Warrior/Knight", ("Bash", "Charge", "Uppercut", "War Scream")),
    "mage": ("Mage/Dark Wizard", ("Heal", "Teleport", "Meteor", "Ice Snake")),
    "archer": ("Archer/Hunter", ("Arrow Storm", "Escape", "Arrow Bomb", "Arrow Shield")),
    "assassin": ("Assassin/Ninja", ("Spin Attack", "Dash", "Multihit", "Smoke Bomb")),
    "shaman": ("Shaman/Skyseer", ("Totem", "Haul", "Aura", "Uproot")),
}

Run = tuple[str, str, str | None]


class Line(NamedTuple):
    align: str                 # left, center, aligned or wrap
    runs: list                 # the line, or the left part of an aligned line
    right: list = []           # the right part of an aligned line


# ---------------------------------------------------------------- run helpers

def offset(pixels: int) -> str:
    """A space-font glyph that moves the pen by this many pixels (negative moves back)."""
    return chr(0xD0000 + pixels)


def space(pixels: int) -> Run:
    return (offset(pixels), "space", None)


def text(value: str, color: str = WHITE) -> Run:
    return (value, TEXT_FONT, color)


def left(runs: list) -> Line:
    return Line("left", runs)


def centered(runs: list) -> Line:
    return Line("center", runs)


def aligned(runs: list, right: list) -> Line:
    return Line("aligned", runs, right)


def wrap(runs: list) -> Line:
    return Line("wrap", runs)


def scale_color(percentage: float, lerp: bool = False) -> str:
    """The colour of a roll percentage on the mod's default scale; 100 % and above is the rainbow.

    Without `lerp` the stop above the value wins, the flat five-colour look; with it the colour slides
    between the mod's lerp stops.
    """
    if percentage >= 100:
        return "rainbow"
    if not lerp:
        return "#%02x%02x%02x" % next(rgb for edge, rgb in FLAT_STOPS if percentage < edge)
    for (low, low_rgb), (high, high_rgb) in zip(LERP_STOPS, LERP_STOPS[1:]):
        if percentage <= high:
            t = max(0.0, percentage - low) / (high - low)
            return "#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip(low_rgb, high_rgb))
    return "#%02x%02x%02x" % LERP_STOPS[-1][1]


def roll_text(percentage: float, lerp: bool) -> Run:
    """The ` [94.6%]` suffix; the mod truncates the decimals rather than rounding them."""
    return text(f" [{math.floor(percentage * 10) / 10:.1f}%]", scale_color(percentage, lerp))


@functools.cache
def _box_glyphs() -> dict:
    return json.loads((mcfont.ASSETS / "font" / "banner" / "box_map.json").read_text())["glyphs"]


def banner(label: str, background: str, foreground: str = BLACK, suffix: Run | None = None) -> list:
    """A boxed tag such as `MYTHIC`: the box background first, then the letters printed back over it."""
    glyphs = _box_glyphs()
    label = label.lower()
    back = glyphs["left_edge"] + offset(-1)
    for char in label:
        back += glyphs["space"] if char == " " else glyphs.get(char + "_background", glyphs["space"])
        back += offset(-1)
    back += glyphs["right_edge"]
    letters = "".join(" " if char == " " else glyphs.get(char + "_foreground", " ") for char in label)
    runs = [(back, BOX_FONT, background), space(2 - mcfont.width(BOX_FONT, back)), (letters, BOX_FONT, foreground)]
    return runs + [suffix] if suffix else runs


# ---------------------------------------------------------------- sections

def _name(item: Item, tier: str, rolls: bool, lerp: bool) -> Line:
    """Emblem frame, item type sprite, the name in the tier colour and the overall roll."""
    shape, _, variant = item.emblem.partition("_")
    shape_index = EMBLEM_SHAPES.index(shape) if shape in EMBLEM_SHAPES else 0
    frame = chr(0xE000 + (int(variant or 1) - 1) * 0x10 + shape_index)
    sprite = TYPE_SPRITES.get(item.type, "")
    runs = [space(-16), (frame, EMBLEM_FRAME, TIERS[tier][1]), space(-49), (sprite, EMBLEM_SPRITE, WHITE),
            space(5), text(item.name, TIERS[tier][0])]
    if rolls and item.overall_roll is not None:
        runs.append(roll_text(item.overall_roll, lerp))
    return left(runs)


def _tags(item: Item, tier: str) -> list[Line]:
    """The rarity and type banners with the restriction icon, and the element strip under them."""
    kind = banner((item.type or item.kind).upper(), TIERS[tier][1])
    restriction = RESTRICTIONS.get(item.restriction)
    if restriction:
        glyph, overlay = restriction
        kind += [space(2), (glyph, BANNER_FONT, RESTRICTION_RED), space(-10), (overlay, BANNER_FONT, WHITE)]
    lines = [left([space(38)] + banner(tier, TIERS[tier][0]) + [space(1)] + kind)]
    elements = [element for element in item.elements if element in ELEMENTS]
    if not elements:
        return lines
    runs = [space(38)]
    for index, element in enumerate(elements):
        _, glyph, overlay, _ = ELEMENTS[element]
        runs += [(glyph, BANNER_FONT, TIERS[tier][1]), space(-10), (overlay, BANNER_FONT, WHITE)]
        if index < len(elements) - 1:
            runs.append(space(-1))
    if len(elements) == 1:  # a single element also gets its name as a banner
        runs += [space(-1)] + banner(elements[0], TIERS[tier][1])
    return lines + [left(runs)]


def _overview(item: Item, tier: str) -> list[Line]:
    """DPS or health, attack speed, then the base damage and base defence rows."""
    lines = []
    if item.average_dps is not None:
        lines.append(left([text(f"{item.average_dps:,}", TIERS[tier][1]), text(" DPS")]))
    elif item.health is not None:
        lines.append(left([text(f"{item.health:+,}", TIERS[tier][1]), text(" Health")]))
    if item.attack_speed:
        label = re.sub(r"(?<!^)([A-Z])", r" \1", item.attack_speed).title()  # superSlow -> Super Slow
        lines.append(left([(ATTACK_SPEED_SPRITE, SPRITE, WHITE), text(f" {label} ", GRAY),
                           text(f"({HITS.get(item.attack_speed, 0)} hits/s)", DARK_GRAY)]))
    damage = [run for element, (low, high) in item.damage.items() if element in ELEMENTS
              for run in ((ELEMENTS[element][0], SPRITE, ELEMENTS[element][3]), text(f" {low:,}-{high:,} ", GRAY))]
    defence = [run for element, value in item.defence.items() if element in ELEMENTS
               for run in ((ELEMENTS[element][0], SPRITE, ELEMENTS[element][3]), text(f" {value:+,} ", GRAY))]
    return lines + ([left(damage)] if damage else []) + ([left(defence)] if defence else [])


def _divider(tier: str) -> Line:
    return centered([("", DIVIDER_FONT, TIERS[tier][1])])


def _weights(item: Item, lerp: bool) -> list[Line]:
    """The Wynnpool weight scales, each scored like a roll."""
    if not item.scales:
        return []
    lines = [left([("", ICON_FONT, ORANGE), text(" Wynnpool")])]
    lines += [aligned([text(f"{scale.profile} Scale")], [roll_text(scale.score, lerp)]) for scale in item.scales]
    return lines


def _requirement(label: str, value: str) -> Line:
    return aligned([("", REQ_SPRITE, WHITE), space(-1), text(f" {label}")], [text(value, GRAY)])


def _requirements(item: Item, tier: str) -> list[Line]:
    """Skill point diamonds with their values, then quest, class and level rows."""
    req = item.requirements
    if not req:
        return []
    lines = []
    skills = req.skills()
    if any(skills):
        frame = chr(0xE000 + (FRAMED_TIERS.index(tier) if tier in FRAMED_TIERS else 0))
        icons, values = [], []
        for index, value in enumerate(skills):
            # A framed, coloured diamond for a required skill; a plain grey one otherwise.
            icons += [(frame if value else "", REQ_FRAME, WHITE), space(-25),
                      (chr((0xE000 if value else 0xE010) + index), REQ_SPRITE, WHITE), space(2)]
            cell = [("", REQ_SPRITE, WHITE), space(-1), space(3), text(str(value), GRAY if value else DARK_GRAY)]
            width = sum(mcfont.width(font_id, glyphs) for glyphs, font_id, _ in cell)
            pad = max(0, (SKILL_CELL - width) // 2)
            values += [space(pad)] + cell + [space(max(0, SKILL_CELL - width - pad))]
        lines += [left([]), centered(icons), left([]), centered(values), left([])]
    if req.quest:
        lines.append(_requirement("Quest", req.quest if len(req.quest) <= 10 else req.quest[:10] + "..."))
    if req.class_name:
        lines.append(_requirement("Class Type", CLASSES.get(req.class_name, (req.class_name.title(),))[0]))
    if req.level:
        lines.append(_requirement("Combat Level", str(req.level)))
    return lines


def _shiny(item: Item, tier: str) -> list[Line]:
    if item.shiny is None:
        return []
    color = TIERS[tier][1]
    return [_divider(tier), aligned([("", COMMON_FONT, color), text(f" {item.shiny.name}", color)],
                                    [text(f"{item.shiny.value:,}")])]


def _reroll(item: Item, tier: str) -> list[Line]:
    """The reroll counter, flush right: a boxed number and the reroll icon."""
    if item.rerolls <= 0:
        return []
    color = TIERS[tier][1]
    runs = banner(str(item.rerolls), color, BLACK, space(2)) + [
        space(-1), ("", BANNER_FONT, color), space(-10), ("", BANNER_FONT, WHITE)]
    return [aligned([], runs)]


def _stats(item: Item, rolls: bool, lerp: bool) -> list[Line]:
    """Identifications in Wynntils' default order, a blank line between groups, value and roll right-aligned."""
    spells = CLASSES.get(item.requirements.class_name, ("", ()))[1]
    lines, last_group = [], None
    for stat in sorted(item.identifications, key=lambda s: stats.order(s.key)):
        group = stats.order(stat.key)[0]
        if last_group is not None and group != last_group:
            lines.append(left([]))
        last_group = group
        name = stat.name
        if stat.key.startswith("SPELL_") and spells:  # "4th Spell Cost" -> "Ice Snake Cost" for the item's class
            name = next((f"{spells[i]} Cost" for i, (word, _) in enumerate(stats.ORDINALS) if word in stat.key), name)
        runs = []
        if stat.key.startswith("SKILL_"):
            skill = stat.key.removeprefix("SKILL_").lower()
            if skill in stats.SKILLS:
                before, after = SKILL_PREFIX[skill]
                runs = [space(before), (chr(0xE010 + stats.SKILLS.index(skill)), SPRITE, WHITE), space(after), text(" ")]
        runs.append(text(f"{name} "))
        right = [text(f"{stat.value:+g}{stat.unit}", GREEN if stat.positive else RED)]
        if rolls and stat.roll is not None:
            right.append(roll_text(stat.roll, lerp))
        lines.append(aligned(runs, right))
    return lines


def _major_ids(item: Item, tier: str) -> list[Line]:
    """Each major id as a wrapped paragraph: star, bold name, description with HTML stripped."""
    lines = []
    for name, lore in item.major_ids.items():
        body = re.sub(r"<[^>]+>", "", lore).strip()
        lines += [left([]), wrap([("", MAJOR_FONT, TIERS[tier][1]), space(2),
                                  text(f"{name}: ", TIERS[tier][1]), text(body, GRAY)])]
    return lines


def tier_of(item: Item) -> str:
    return item.tier.lower() if item.tier.lower() in TIERS else "normal"


def build(item: Item, rolls: bool = True, lerp: bool = False) -> list[Line]:
    """Every tooltip line, in the order Wynntils assembles the sections.

    `rolls` toggles the roll percentages after the name and the identifications; `lerp` picks the
    colour scale for them.
    """
    tier = tier_of(item)
    header = [left([]), _name(item, tier, rolls, lerp)] + _tags(item, tier) + [left([])]
    sections = [_overview(item, tier),
                _weights(item, lerp),
                _requirements(item, tier) + _shiny(item, tier),
                _reroll(item, tier) + _stats(item, rolls, lerp) + _major_ids(item, tier)]
    lines = list(header)
    for section in filter(None, sections):
        if len(lines) > len(header):
            lines.append(_divider(tier))  # a divider separates two sections, so an empty one draws none
        lines += section
    return lines
