"""What a card shows, independent of where the numbers came from.

Build an `Item` by hand for any item you can describe, or let `wynncard.sources` fill one from the
Wynnpool item API and a Wynnventory market listing. Every field is optional except the name: sections
whose data is missing are simply not drawn.
"""
from dataclasses import dataclass, field

from . import stats

TIERS = ("normal", "unique", "rare", "set", "legendary", "fabled", "mythic")
CLASSES = ("warrior", "mage", "archer", "assassin", "shaman")
RESTRICTIONS = ("", "untradable", "quest_item", "soulbound")


@dataclass(slots=True)
class Identification:
    """One identification line, e.g. `Mana Regen  +22/5s [100.0%]`.

    `value` is the number as printed, so a spell that costs 11 % less is `-11`. `roll` is the roll
    percentage the mod shows in brackets; `None` leaves the bracket out. `key` is the Wynntils stat key
    (`MISC_MANA_REGEN`): it sets the position in the list, adds the skill icon to `SKILL_` stats and
    renames `SPELL_` costs after the class's spells. `inverted` marks stats where lower is better.
    """
    name: str                   # printed name, e.g. "Mana Regen"
    value: float                # the number as printed: -11 for a spell that costs 11 % less
    unit: str = ""              # printed suffix: "", "%", "/3s", "/5s", " tier"
    roll: float | None = None   # roll percentage shown in brackets; None leaves the bracket out
    key: str = ""               # Wynntils stat key, e.g. MISC_MANA_REGEN: position, skill icon, spell name
    inverted: bool = False      # lower is better, so a negative value is drawn green

    @classmethod
    def from_api(cls, name: str, value: float, roll: float | None = None) -> "Identification":
        """From a Wynncraft API stat name (`manaRegen`) or a Wynntils key; unknown names print as given."""
        stat = stats.lookup(name)
        if stat is None:
            return cls(name, value, roll=roll, key=name)
        return cls(stat.name, value, stat.unit, roll, stat.key, stat.inverted)

    @property
    def positive(self) -> bool:
        """Whether the value is good for the wearer, which decides between green and red."""
        return self.value < 0 if self.inverted else self.value > 0


@dataclass(slots=True)
class Requirements:
    """The requirement block: skill points, quest, class and combat level. Zero or empty means none."""
    level: int = 0          # combat level
    class_name: str = ""    # one of CLASSES
    quest: str = ""         # quest name, shortened to ten characters on the card
    strength: int = 0       # skill points, one per element in the game's order
    dexterity: int = 0
    intelligence: int = 0
    defence: int = 0
    agility: int = 0

    def skills(self) -> tuple[int, int, int, int, int]:
        """Skill points in the game's order: strength, dexterity, intelligence, defence, agility."""
        return self.strength, self.dexterity, self.intelligence, self.defence, self.agility

    def __bool__(self) -> bool:
        return bool(self.level or self.class_name or self.quest or any(self.skills()))


@dataclass(frozen=True, slots=True)
class Scale:
    """A Wynnpool weight scale scored against the roll, e.g. `Main Scale  [94.6%]`."""
    profile: str    # scale name, printed as "<profile> Scale"
    score: float    # percentage, coloured like a roll


@dataclass(frozen=True, slots=True)
class Shiny:
    """The shiny tracker on the item, e.g. `Mobs Killed  1,234`."""
    name: str       # tracker name, e.g. "Mobs Killed"
    value: int      # tracked count


@dataclass(slots=True)
class Item:
    """Everything the card can draw.

    Base data (type, damage, requirements) describes the item; roll data (`overall_roll`, the
    identification rolls, `rerolls`, `shiny`, `scales`) describes one particular copy of it.
    """
    name: str                                # printed in the tier colour
    tier: str = "normal"                     # one of TIERS; sets the colours and the frame
    kind: str = ""                           # weapon, armour or accessory
    type: str = ""                           # wand, bow, helmet, ring... drives the emblem sprite and the type banner
    emblem: str = "diamond_1"                # emblem shape and variant, as the item API names them
    elements: list[str] = field(default_factory=list)   # element strip under the banners, in stats.ELEMENTS order
    restriction: str = ""                    # one of RESTRICTIONS, draws the icon after the type banner
    attack_speed: str = ""                   # superSlow ... superFast, weapons only
    average_dps: int | None = None           # weapons only
    health: int | None = None                # armour and accessories
    damage: dict[str, tuple[int, int]] = field(default_factory=dict)   # element -> (low, high); "neutral" for plain
    defence: dict[str, int] = field(default_factory=dict)              # element -> base defence
    requirements: Requirements = field(default_factory=Requirements)   # empty requirements draw nothing
    identifications: list[Identification] = field(default_factory=list)   # sorted into tooltip order by key
    major_ids: dict[str, str] = field(default_factory=dict)            # name -> description, HTML tags allowed
    overall_roll: float | None = None        # the percentage after the name
    rerolls: int = 0                         # reroll counter, flush right above the identifications
    shiny: Shiny | None = None               # shiny tracker; also switches to the shiny frame
    scales: list[Scale] = field(default_factory=list)   # Wynnpool weight scales, their own section
