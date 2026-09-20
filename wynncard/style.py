"""Sizes, colours and the game's icon glyphs. Everything the card looks like is decided here."""

W, PAD, LINE, GAP, COL_GAP = 620, 26, 30, 14, 20
SIZE, BIG, SMALL = 24, 40, 16

BG, PANEL, TEXT, MUTED, ACCENT = "#150b14", "#241322", "#f8efff", "#AAAAAA", "#d966ff"
GREEN, RED, AQUA, YELLOW, WHITE = "#55FF55", "#FF5555", "#55FFFF", "#FFFF55", "#FFFFFF"
CHIP, DIVIDER, DIM = "#3a2038", "#5a315e", "#6b566a"
RAINBOW = ("#ff5b74", "#ffd760", "#32ff70", "#3ff2ff", "#efb0ff")  # a perfect roll cycles through these, as in the game
EMBLEM = "#d8a72c"

RARITY = {  # border, name colour
    "normal": ("#8f949a", "#f0f0f0"), "unique": ("#d8c83c", "#fff178"), "rare": ("#d983ff", "#f4c4ff"),
    "set": ("#40d65a", "#7dff91"), "legendary": ("#55d8ff", "#90edff"), "fabled": ("#ff5d61", "#ff9a9d"),
    "mythic": ("#d966ff", "#e878ff"),
}
ELEMENT = {  # glyph in the common font, colour
    "neutral": ("", "#FFFFAA"), "earth": ("", "#00AA00"), "thunder": ("", YELLOW),
    "water": ("", AQUA), "fire": ("", RED), "air": ("", WHITE),
}
SWORD, HEART, MARK, POWDER, REROLL = "", "", "", "", ""

SKILLS = (("strength", "earth"), ("dexterity", "thunder"), ("intelligence", "water"),
          ("defence", "fire"), ("agility", "air"))
SKILL_ELEMENT = {f"SKILL_{skill.upper()}": element for skill, element in SKILLS}
HITS = {"superSlow": 0.51, "verySlow": 0.83, "slow": 1.21, "normal": 2.05,
        "fast": 2.5, "veryFast": 3.1, "superFast": 4.3}
UNITS = {"PERCENT": "%", "RAW": "", "PER_3_S": "/3s", "PER_5_S": "/5s", "TIER": " tier"}
CLASSES = {  # tooltip class name and the spell names the cost stats are shown under
    "warrior": ("Warrior/Knight", ("Bash", "Charge", "Uppercut", "War Scream")),
    "mage": ("Mage/Dark Wizard", ("Heal", "Teleport", "Meteor", "Ice Snake")),
    "archer": ("Archer/Hunter", ("Arrow Storm", "Escape", "Bomb Arrow", "Arrow Shield")),
    "assassin": ("Assassin/Ninja", ("Spin Attack", "Vanish", "Multihit", "Smoke Bomb")),
    "shaman": ("Shaman/Skyseer", ("Totem", "Haul", "Aura", "Uproot")),
}
ORDINALS = ("FIRST", "SECOND", "THIRD", "FOURTH")
GROUPS = (  # identification order of the game tooltip; anything unlisted lands just before the spell costs
    ("SKILL_", "DAMAGE_"),
    ("MISC_HEALTH", "MISC_LIFE_STEAL", "MISC_MANA"),
    ("DEFENCE_",),
    ("MISC_WALK_SPEED", "MISC_SPRINT", "MISC_JUMP"),
    ("SPELL_",),
)


def roll_color(pct: float) -> str:
    return "rainbow" if pct >= 100 else AQUA if pct >= 95 else GREEN if pct >= 80 else YELLOW if pct >= 30 else RED
