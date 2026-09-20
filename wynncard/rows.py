"""Item data to card rows. A row is a tuple whose first element names its kind; `card` draws them.

Kinds: ("stat", left, value, pct) three-column identification, ("row", left, right),
("big", value, label), ("badge", powder, rerolls), ("skills", requirements),
("wrap", parts), ("small", text), ("div",), ("gap", pixels).
"""
import math
import re

from .style import (ACCENT, CLASSES, ELEMENT, GAP, GREEN, GROUPS, HEART, HITS, MARK, MUTED, ORDINALS, RED, SKILL_ELEMENT,
                    SKILLS, SWORD, TEXT, UNITS, WHITE, YELLOW, roll_color)


def _group(key: str):
    """(group, position in the group) for the tooltip order."""
    for i, prefixes in enumerate(GROUPS):
        hit = next((p for p in prefixes if key.startswith(p)), None)
        if hit:
            return i, prefixes.index(hit)
    return len(GROUPS) - 1.5, 0


def stats(item: dict, spells: tuple[str, ...] = ()) -> list[tuple]:
    """Identifications in tooltip order, a blank line between groups."""
    found = []
    for s in item.get("stat_rolls") or []:
        actual = s.get("statActualValue") or {}
        stat_type = actual.get("statType") or {}
        value, key = actual.get("value"), stat_type.get("key") or ""
        if value is None:
            continue
        try:
            pct = float(s.get("rollPercentage"))
        except (TypeError, ValueError):
            pct = math.nan
        name = stat_type.get("displayName") or key
        if key.startswith("SPELL_"):
            value = -value  # the API counts a cost reduction up, the tooltip shows it as a negative cost
            spell = next((spells[i] for i, word in enumerate(ORDINALS) if word in key and i < len(spells)), None)
            name = f"{spell} Cost" if spell else name
        found.append((_group(key), key, name, value, UNITS.get(stat_type.get("unit"), ""), pct))

    rows, last = [], None
    for group, key, name, value, unit, pct in sorted(found, key=lambda f: f[0]):
        if last is not None and group[0] != last[0]:
            rows.append(("gap", GAP // 2))
        last = group
        good = value < 0 if key.startswith("SPELL_") else value > 0
        left = [(name, TEXT)]
        if key in SKILL_ELEMENT:
            glyph, color = ELEMENT[SKILL_ELEMENT[key]]
            left = [(glyph + " ", color), (name, TEXT)]
        pct_parts = [] if math.isnan(pct) else [(f"[{pct:.1f}%]", roll_color(pct))]
        rows.append(("stat", left, [(f"{value:+g}{unit}", GREEN if good else RED)], pct_parts))
    return rows


def _damage(info: dict) -> list[tuple]:
    """Base damage ranges, one part per element, the way the tooltip prints them."""
    parts = []
    for key, dmg in (info.get("base") or {}).items():
        element = key.replace("base", "").replace("Damage", "").lower() or "neutral"
        if not key.endswith("Damage") or element not in ELEMENT:
            continue
        glyph, color = ELEMENT[element]
        parts += [(glyph + " ", color), (f"{dmg['min']:,}-{dmg['max']:,}   ", TEXT)]
    return parts


def weapon(info: dict) -> list[tuple]:
    speed = info.get("attackSpeed") or ""
    label = re.sub(r"(?<!^)([A-Z])", r" \1", speed).title()
    rows = [("big", str(info.get("averageDps") or "?"), "DPS"),
            ("row", [(SWORD + " ", WHITE), (label, TEXT), (f" ({HITS.get(speed, 0):.2f} hits/s)", MUTED)], [])]
    damage = _damage(info)
    return rows + [("row", damage, [])] if damage else rows


def armour(info: dict) -> list[tuple]:
    rows = []
    for key, value in (info.get("base") or {}).items():
        raw = value.get("raw", value.get("max")) if isinstance(value, dict) else value
        if raw is None:
            continue
        if key == "baseHealth":
            rows.append(("row", [(HEART + " ", RED), (f"{raw:,}", TEXT)], []))
        elif key.endswith("Defence"):
            glyph, color = ELEMENT.get(key.replace("base", "").replace("Defence", "").lower(), (MARK, MUTED))
            rows.append(("row", [(glyph + " ", color), (f"{raw:+g}", GREEN if raw > 0 else RED)], []))
    return rows


def scales(items: list[dict]) -> list[tuple]:
    rows = [("row", [(MARK + " ", YELLOW), ("Wynnpool", TEXT)], [])]
    for s in items:
        rows.append(("stat", [(f"{s['profile']} Scale", TEXT)], [], [(f"[{s['score']:.1f}%]", roll_color(s["score"]))]))
    return rows


def build(item: dict, info: dict | None, scale_list: list[dict]) -> list[tuple]:
    """Every row under the header, in order."""
    rows = []
    if info:
        rows += weapon(info) if info.get("type") == "weapon" else armour(info)
    if scale_list:
        rows += [("div",)] + scales(scale_list)

    req = (info or {}).get("requirements") or {}
    if req:
        rows.append(("div",))
        if any(req.get(skill) for skill, _ in SKILLS):
            rows.append(("skills", req))
        if req.get("classRequirement"):
            label = CLASSES.get(req["classRequirement"], (req["classRequirement"].title(), ()))[0]
            rows.append(("row", [("Class Type", TEXT)], [(label, MUTED)]))
        if req.get("level"):
            rows.append(("row", [("Combat Level", TEXT)], [(str(req["level"]), MUTED)]))

    powder, rerolls = (info or {}).get("powderSlots") or 0, item.get("reroll_count") or 0
    if powder or rerolls > 1:  # a single reroll is not shown, the same as in the game
        rows.append(("badge", powder, rerolls))

    identifications = stats(item, CLASSES.get(req.get("classRequirement") or "", ("", ()))[1])
    if identifications:
        rows += [("div",)] + identifications
    for name, text in ((info or {}).get("majorIds") or {}).items():
        body = re.sub(r"<[^>]+>", "", text).strip()
        rows += [("gap", GAP), ("wrap", [(MARK + " ", ACCENT), (f"{name}: ", ACCENT), (body, MUTED)])]
    if item.get("shiny"):
        rows += [("gap", GAP), ("small", f"shiny: {item['shiny']}")]
    return rows
