"""The identification table, built the same way Wynntils' StatModel builds its registry.

Every identification has a Wynntils key (`MISC_MANA_REGEN`), the display name the game prints, a unit
suffix and the name the Wynncraft item API uses (`manaRegen`). The key drives the tooltip: its group
decides where the line sits and where the blank separators go, `SKILL_` keys get a skill icon and
`SPELL_` keys are named after the class's spells and count a negative value as good.

Only the stats that appear on gear are listed; charm-only leveled stats are left out.
"""
from dataclasses import dataclass

UNITS = {"RAW": "", "PERCENT": "%", "PER_3_S": "/3s", "PER_5_S": "/5s", "TIER": " tier"}
ELEMENTS = ("earth", "thunder", "water", "fire", "air")  # the game's order
SKILLS = ("strength", "dexterity", "intelligence", "defence", "agility")  # one per element, same order
ORDINALS = (("FIRST", "1st"), ("SECOND", "2nd"), ("THIRD", "3rd"), ("FOURTH", "4th"))


@dataclass(frozen=True, slots=True)
class StatType:
    key: str        # Wynntils key, e.g. MISC_MANA_REGEN
    name: str       # printed name, e.g. "Mana Regen"
    unit: str       # printed suffix: "", "%", "/3s", "/5s", " tier"
    api: str        # Wynncraft item API name, e.g. manaRegen
    inverted: bool = False  # lower is better (spell costs)


# MiscStatKind in Wynntils enum order: (enum name, display name, unit, api name).
_MISC = (
    ("HEALTH", "Health", "RAW", "rawHealth"),
    ("HEALTH_REGEN_PERCENT", "Health Regen", "PERCENT", "healthRegen"),
    ("HEALTH_REGEN_RAW", "Health Regen", "RAW", "healthRegenRaw"),
    ("HEALING_EFFICIENCY", "Healing Efficiency", "PERCENT", "healingEfficiency"),
    ("LIFE_STEAL", "Life Steal", "PER_3_S", "lifeSteal"),
    ("MANA_REGEN", "Mana Regen", "PER_5_S", "manaRegen"),
    ("MANA_STEAL", "Mana Steal", "PER_3_S", "manaSteal"),
    ("MAX_MANA_RAW", "Max Mana", "RAW", "rawMaxMana"),
    ("WALK_SPEED", "Walk Speed", "PERCENT", "walkSpeed"),
    ("SPRINT", "Sprint", "PERCENT", "sprint"),
    ("SPRINT_REGEN", "Sprint Regen", "PERCENT", "sprintRegen"),
    ("JUMP_HEIGHT", "Jump Height", "RAW", "jumpHeight"),
    ("ATTACK_SPEED", "Attack Speed", "TIER", "rawAttackSpeed"),
    ("MAIN_ATTACK_RANGE", "Main Attack Range", "PERCENT", "mainAttackRange"),
    ("REFLECTION", "Reflection", "PERCENT", "reflection"),
    ("THORNS", "Thorns", "PERCENT", "thorns"),
    ("EXPLODING", "Exploding", "PERCENT", "exploding"),
    ("POISON", "Poison", "PER_3_S", "poison"),
    ("KNOCKBACK", "Knockback", "PERCENT", "knockback"),
    ("SLOW_ENEMY", "Slow Enemy", "PERCENT", "slowEnemy"),
    ("WEAKEN_ENEMY", "Weaken Enemy", "PERCENT", "weakenEnemy"),
    ("STEALING", "Stealing", "PERCENT", "stealing"),
    ("COMBAT_EXPERIENCE", "Combat Experience", "PERCENT", "combatExperience"),
    ("LOOT", "Loot", "PERCENT", "lootBonus"),
    ("LOOT_QUALITY", "Loot Quality", "PERCENT", "lootQuality"),
    ("GATHERING_EXPERIENCE", "Gathering Experience", "PERCENT", "gatherXpBonus"),
    ("GATHERING_SPEED", "Gathering Speed", "PERCENT", "gatherSpeed"),
    ("SLAYING_XP", "Slaying XP", "PERCENT", "slayingXP"),
    ("GATHERING_XP", "Gathering Experience", "PERCENT", "gatheringExperience"),
    ("DUNGEON_XP", "Dungeon XP", "PERCENT", "dungeonXP"),
)
_ATTACKS = (("ANY", ""), ("SPELL", "Spell"), ("MAIN_ATTACK", "Main Attack"))
_DAMAGE_TYPES = (("ALL", ""), ("NEUTRAL", "Neutral"), ("FIRE", "Fire"), ("WATER", "Water"), ("AIR", "Air"),
                 ("THUNDER", "Thunder"), ("EARTH", "Earth"), ("RAINBOW", "Elemental"))


def _build() -> tuple[tuple[StatType, ...], ...]:
    """The five groups in Wynntils' default tooltip order: skills, misc, defence, damage, spell costs."""
    skills = tuple(StatType(f"SKILL_{s.upper()}", s.title(), "", f"raw{s.title()}") for s in SKILLS)
    misc = tuple(StatType(f"MISC_{enum}", name, UNITS[unit], api) for enum, name, unit, api in _MISC)
    defence = tuple(StatType(f"DEFENCE_{e.upper()}", f"{e.title()} Defence", "%", f"{e}Defence") for e in ELEMENTS)
    defence += (StatType("DEFENCE_ELEMENTAL", "Elemental Defence", "%", "elementalDefence"),
                StatType("DEFENCE_TO_MOBS", "Mob Damage Resistance", "%", "defenceToMobs"))
    damage = []
    for attack, attack_name in _ATTACKS:
        for kind, kind_name in _DAMAGE_TYPES:
            words = " ".join(word for word in (kind_name, attack_name, "Damage") if word)
            camel = words.replace(" ", "")
            damage.append(StatType(f"DAMAGE_{attack}_{kind}_PERCENT", words, "%", camel[0].lower() + camel[1:]))
            damage.append(StatType(f"DAMAGE_{attack}_{kind}_RAW", words, "", "raw" + camel))
    damage += [StatType("CRITICAL_DAMAGE_BONUS", "Critical Damage", "%", "criticalDamageBonus"),
               StatType("DAMAGE_TO_MOBS", "Damage to Mobs", "%", "damageToMobs")]
    spells = []
    for word, ordinal in ORDINALS:
        spells.append(StatType(f"SPELL_{word}_SPELL_COST_PERCENT", f"{ordinal} Spell Cost", "%",
                               f"{ordinal}SpellCost", inverted=True))
        spells.append(StatType(f"SPELL_{word}_SPELL_COST_RAW", f"{ordinal} Spell Cost", "",
                               f"raw{ordinal}SpellCost", inverted=True))
    return skills, misc, defence, tuple(damage), tuple(spells)


GROUPS = _build()
TYPES: tuple[StatType, ...] = sum(GROUPS, ())
# key -> (group, position): the sort key that puts identifications in tooltip order.
ORDER: dict[str, tuple[int, int]] = {t.key: (g, i) for g, group in enumerate(GROUPS) for i, t in enumerate(group)}
UNKNOWN_ORDER = (len(GROUPS), 0)  # keys the table does not know go last, in the order given
_BY_NAME: dict[str, StatType] = {t.api: t for t in TYPES} | {t.key: t for t in TYPES}


def lookup(name: str) -> StatType | None:
    """Find a stat by API name (`manaRegen`) or Wynntils key (`MISC_MANA_REGEN`)."""
    return _BY_NAME.get(name)


def order(key: str) -> tuple[int, int]:
    return ORDER.get(key, UNKNOWN_ORDER)
