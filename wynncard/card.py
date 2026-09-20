"""Draws the rows onto the panel and returns the PNG."""
import io

from PIL import Image, ImageDraw

from . import rows as build_rows
from .style import (BG, BIG, CHIP, COL_GAP, DIM, DIVIDER, ELEMENT, EMBLEM, GAP, LINE, MUTED, PAD, PANEL, POWDER,
                    RARITY, REROLL, SIZE, SKILLS, SMALL, W, roll_color)
from .text import ascent, draw, draw_right, measure, wrap

ICON, EMBLEM_BOX = 48, 78


def _rarity(item: dict):
    return RARITY.get((item.get("rarity") or "normal").lower(), RARITY["normal"])


def _height(row: tuple) -> int:
    kind = row[0]
    if kind == "gap":
        return row[1]
    if kind == "div":
        return GAP * 2
    if kind == "big":
        return BIG + 8
    if kind == "skills":
        return 120
    if kind == "badge":
        return SMALL + 18
    if kind == "small":
        return SMALL + 6
    if kind == "wrap":
        return LINE * len(wrap(row[1], W - 2 * PAD, SIZE))
    return LINE


def _columns(rows: list[tuple]) -> tuple[int, int]:
    """Right edges of the value and the roll percentage columns, so both line up down the card."""
    pct = max((measure(r[3], SIZE) for r in rows if r[0] == "stat"), default=0)
    pct_right = W - PAD
    return pct_right - pct - (COL_GAP if pct else 0), pct_right


def _emblem(img, d, icon: bytes | None, x: int, y: int) -> None:
    """The golden diamond the game frames an item icon with."""
    cx, cy, half = x + EMBLEM_BOX // 2, y + EMBLEM_BOX // 2, EMBLEM_BOX // 2
    d.polygon([(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)], fill="#3a2e12", outline=EMBLEM, width=3)
    if not icon:
        return
    try:
        sprite = Image.open(io.BytesIO(icon)).convert("RGBA").resize((ICON, ICON), Image.LANCZOS)
        img.paste(sprite, (cx - ICON // 2, cy - ICON // 2), sprite)
    except OSError:  # a broken texture must not cost us the card
        pass


def _chips(d, x: int, y: int, chips: list[tuple[str, str]]) -> None:
    for text, color in chips:
        width = measure([(text, color)], SMALL)
        d.rounded_rectangle((x, y, x + width + 16, y + SMALL + 12), radius=4, fill=CHIP)
        draw(d, x + 8, y + 6 + ascent(SMALL), [(text, color)], SMALL)
        x += width + 24


def _header(img, d, item: dict, info: dict | None, icon: bytes | None, y: int) -> int:
    """Emblem, name with the overall roll and the rarity, type and element chips."""
    name_color = _rarity(item)[1]
    _emblem(img, d, icon, PAD, y)
    x = PAD + EMBLEM_BOX + 18
    parts = [(item.get("name") or "?", name_color)]
    overall = item.get("overall_roll")
    if overall is not None:
        parts.append((f" [{overall:.1f}%]", roll_color(overall)))
    draw(d, x, y + ascent(SIZE + 4), parts, SIZE + 4)
    kind = (info or {}).get("subType") or item.get("type") or ""
    _chips(d, x, y + 36, [(t.upper(), c) for t, c in ((item.get("rarity") or "", name_color), (kind, MUTED)) if t])
    elements = [(ELEMENT[e][0] + " " + e.upper(), ELEMENT[e][1]) for e in (info or {}).get("elements") or []]
    if elements:
        _chips(d, x, y + 36 + SMALL + 18, elements)
    return EMBLEM_BOX + (SMALL + 18 if elements else 0)


def _skills(d, y: int, req: dict) -> None:
    """The five requirement diamonds under their STR/DEX/INT/DEF/AGI labels, greyed out where nothing is asked."""
    step = (W - 2 * PAD) // 5
    for i, (skill, element) in enumerate(SKILLS):
        value = req.get(skill) or 0
        glyph, color = ELEMENT[element]
        cx, cy = PAD + step * i + step // 2, y + 56
        label = [(skill[:3].upper(), color if value else MUTED)]
        width = measure(label, SMALL)
        d.rounded_rectangle((cx - width // 2 - 8, y, cx + width // 2 + 8, y + SMALL + 10), radius=4, fill=CHIP)
        draw(d, cx - width // 2, y + 5 + ascent(SMALL), label, SMALL)
        d.polygon([(cx, cy - 30), (cx + 26, cy), (cx, cy + 30), (cx - 26, cy)],
                  fill="#2f1a2d", outline=color if value else "#4d3a4b", width=2)
        glyph_parts = [(glyph, color if value else DIM)]
        draw(d, cx - measure(glyph_parts, SIZE) // 2, cy + ascent(SIZE) // 2 - 2, glyph_parts, SIZE)
        value_parts = [(str(value), color if value else MUTED)]
        draw(d, cx - measure(value_parts, SMALL) // 2, y + 94 + ascent(SMALL), value_parts, SMALL)


def _badge(d, y: int, powder: int, rerolls: int) -> None:
    """Powder slots and reroll count, right aligned, where the game puts them."""
    chips = [(f"{POWDER} {powder}", "#c9b6ff")] if powder else []
    if rerolls > 1:
        chips.append((f"{REROLL} {rerolls}", EMBLEM))
    x = W - PAD - sum(measure([c], SMALL) + 16 for c in chips) - 8 * (len(chips) - 1)
    for text, color in chips:
        width = measure([(text, color)], SMALL)
        d.rounded_rectangle((x, y, x + width + 16, y + SMALL + 12), radius=4, fill=CHIP)
        draw(d, x + 8, y + 6 + ascent(SMALL), [(text, color)], SMALL)
        x += width + 24


def _divider(d, y: int) -> None:
    mid, cx = y + GAP, W // 2
    d.line((PAD + 40, mid, cx - 16, mid), fill=DIVIDER, width=2)
    d.line((cx + 16, mid, W - PAD - 40, mid), fill=DIVIDER, width=2)
    d.polygon([(cx, mid - 8), (cx + 8, mid), (cx, mid + 8), (cx - 8, mid)], fill=DIVIDER)


def _corners(d, height: int, color: str) -> None:
    """Short brackets in the corners, like the frame around the tooltip in game."""
    for x, dx in ((10, 1), (W - 11, -1)):
        for y, dy in ((10, 1), (height - 11, -1)):
            d.line((x, y, x + dx * 26, y), fill=color, width=4)
            d.line((x, y, x, y + dy * 26), fill=color, width=4)


def render(item: dict, info: dict | None = None, scales: list[dict] | None = None, icon: bytes | None = None) -> bytes:
    rows = build_rows.build(item, info, scales or [])
    header_h = EMBLEM_BOX + (SMALL + 18 if (info or {}).get("elements") else 0)
    height = PAD + header_h + sum(_height(r) for r in rows) + PAD
    border = _rarity(item)[0]

    img = Image.new("RGB", (W, height), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((3, 3, W - 4, height - 4), radius=10, fill=PANEL, outline=border, width=3)
    _corners(d, height, border)
    y = PAD + _header(img, d, item, info, icon, PAD)
    value_right, pct_right = _columns(rows)

    for row in rows:
        kind, base = row[0], y + ascent(SIZE)
        if kind == "stat":
            draw(d, PAD, base, row[1], SIZE)
            if row[2]:
                draw_right(d, value_right, base, row[2], SIZE)
            if row[3]:
                draw_right(d, pct_right, base, row[3], SIZE)
        elif kind == "row":
            draw(d, PAD, base, row[1], SIZE)
            if row[2]:
                draw_right(d, W - PAD, base, row[2], SIZE)
        elif kind == "big":
            x = draw(d, PAD, y + ascent(BIG), [(row[1], "#c89ae0")], BIG)
            draw(d, x + 8, y + ascent(BIG), [(row[2], MUTED)], SIZE)
        elif kind == "div":
            _divider(d, y)
        elif kind == "skills":
            _skills(d, y, row[1])
        elif kind == "badge":
            _badge(d, y, row[1], row[2])
        elif kind == "small":
            draw(d, PAD, y + ascent(SMALL), [(row[1], "#b79abf")], SMALL)
        elif kind == "wrap":
            for line in wrap(row[1], W - 2 * PAD, SIZE):
                draw(d, PAD, y + ascent(SIZE), line, SIZE)
                y += LINE
            continue
        y += _height(row)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
