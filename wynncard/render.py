"""Draws the tooltip lines onto the game's tooltip background and scales the result up."""
import functools
import io
import json

from PIL import Image

from . import game, mcfont

LINE_HEIGHT, PAD_X, PAD_Y, MIN_WIDTH = 10, 10, 12, 140
RAINBOW = game.RAINBOW


@functools.cache
def _sprite(name: str) -> tuple[Image.Image, dict]:
    base = mcfont.ASSETS / "textures" / "gui" / "sprites" / "tooltip" / f"{name}.png"
    meta = json.loads(base.with_suffix(".png.mcmeta").read_text())
    return Image.open(base).convert("RGBA"), meta["gui"]["scaling"]["border"]


def _nine_slice(name: str, width: int, height: int) -> Image.Image:
    """Stretch a bordered sprite to the tooltip size, the way the game scales its frames."""
    source, border = _sprite(name)
    left, right, top, bottom = border["left"], border["right"], border["top"], border["bottom"]
    out = Image.new("RGBA", (width, height))
    parts = (
        ((0, 0, left, top), (0, 0, left, top)),
        ((source.width - right, 0, source.width, top), (width - right, 0, width, top)),
        ((0, source.height - bottom, left, source.height), (0, height - bottom, left, height)),
        ((source.width - right, source.height - bottom, source.width, source.height),
         (width - right, height - bottom, width, height)),
        ((left, 0, source.width - right, top), (left, 0, width - right, top)),
        ((left, source.height - bottom, source.width - right, source.height),
         (left, height - bottom, width - right, height)),
        ((0, top, left, source.height - bottom), (0, top, left, height - bottom)),
        ((source.width - right, top, source.width, source.height - bottom),
         (width - right, top, width, height - bottom)),
        ((left, top, source.width - right, source.height - bottom), (left, top, width - right, height - bottom)),
    )
    for crop, box in parts:
        piece = source.crop(crop)
        target = (box[2] - box[0], box[3] - box[1])
        if target[0] <= 0 or target[1] <= 0:
            continue
        out.alpha_composite(piece.resize(target, Image.NEAREST), (box[0], box[1]))
    return out


def _run_width(runs) -> int:
    return sum(mcfont.width(font_id, value) for value, font_id, _ in runs)


def _draw_runs(canvas: Image.Image, x: int, baseline: int, runs, zoom: int) -> None:
    for value, font_id, color in runs:
        if color is None:  # a pure offset run
            x += mcfont.width(font_id, value)
            continue
        if color == "rainbow":
            for index, char in enumerate(value):
                x = mcfont.draw(canvas, x, baseline, char, font_id, RAINBOW[index % len(RAINBOW)], zoom)
            continue
        x = mcfont.draw(canvas, x, baseline, value, font_id, color, zoom)


def _wrapped(runs, width: int) -> list:
    """Split a paragraph run list into lines that fit the tooltip width."""
    lines, current, used = [], [], 0
    for value, font_id, color in runs:
        for word in value.replace("\n", " ").split(" "):
            piece = word + " "
            piece_width = mcfont.width(font_id, piece)
            if used + piece_width > width and current:
                lines.append(current)
                current, used = [], 0
            current.append((piece, font_id, color))
            used += piece_width
    return lines + ([current] if current else [])


def render(item: dict, info: dict | None = None, scales: list[dict] | None = None, scale: int = 4) -> bytes:
    """PNG of the item tooltip; `scale` is the Minecraft GUI scale to render at."""
    info = info or {}
    lines = game.build(item, info, scales or [])

    width = max([MIN_WIDTH] + [game.line_width(line) for line in lines if line[0] != "wrap"])
    flat = []
    for line in lines:
        if line[0] == "wrap":
            flat += [("fixed", part) for part in _wrapped(line[1], width)]
        else:
            flat.append(line)

    size = (width + 2 * PAD_X, LINE_HEIGHT * len(flat) + 2 * PAD_Y)
    canvas = Image.new("RGBA", (size[0] * scale, size[1] * scale), (0, 0, 0, 0))
    tier = (item.get("rarity") or info.get("tier") or "normal").lower()
    prefix = f"{tier}_" if tier in game.TIERS and tier != "normal" else ""
    for part in (f"{prefix}background", f"{prefix}frame"):
        frame = _nine_slice(part, size[0], size[1])
        canvas.alpha_composite(frame.resize(canvas.size, Image.NEAREST))

    for index, line in enumerate(flat):
        baseline = PAD_Y + index * LINE_HEIGHT + 8
        if line[0] == "aligned":
            _draw_runs(canvas, PAD_X, baseline, line[1], scale)
            _draw_runs(canvas, PAD_X + width - _run_width(line[2]), baseline, line[2], scale)
        elif line[0] == "centered":
            _draw_runs(canvas, PAD_X + (width - _run_width(line[1])) // 2, baseline, line[1], scale)
        else:
            _draw_runs(canvas, PAD_X, baseline, line[1], scale)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
