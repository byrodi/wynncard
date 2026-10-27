"""Draws the tooltip lines onto the game's tooltip background and scales the result up.

Layout happens in Minecraft pixels: every line is `LINE_HEIGHT` tall, the text block is padded by
`PAD_X`/`PAD_Y` and never narrower than the game's minimum. The nine-slice frame is stretched to that
size and the glyphs are stamped on top, each one already scaled by `scale` whole pixels, so the output
is a pixel-exact enlargement of what the game shows.
"""
import functools
import io
import json

from PIL import Image

from . import mcfont, tooltip
from .model import Item
from .tooltip import Line

LINE_HEIGHT, PAD_X, PAD_Y, MIN_WIDTH = 10, 10, 12, 140
BASELINE = 8  # glyph ascent inside a line


@functools.cache
def _sprite(name: str) -> tuple[Image.Image, dict]:
    """A tooltip frame or background sprite with the border widths from its `.mcmeta`.

    Shiny sprites are animations with their frames stacked in one strip; the card shows the first frame.
    """
    base = mcfont.ASSETS / "textures" / "gui" / "sprites" / "tooltip" / f"{name}.png"
    scaling = json.loads(base.with_suffix(".png.mcmeta").read_text())["gui"]["scaling"]
    image = Image.open(base).convert("RGBA")
    return image.crop((0, 0, image.width, scaling["height"])), scaling["border"]


def _nine_slice(name: str, width: int, height: int) -> Image.Image:
    """Stretch a bordered sprite to the tooltip size: corners stay, edges and centre are resized."""
    source, border = _sprite(name)
    left, right, top, bottom = border["left"], border["right"], border["top"], border["bottom"]
    out = Image.new("RGBA", (width, height))
    x_cuts = ((0, left, 0, left), (left, source.width - right, left, width - right),
              (source.width - right, source.width, width - right, width))
    y_cuts = ((0, top, 0, top), (top, source.height - bottom, top, height - bottom),
              (source.height - bottom, source.height, height - bottom, height))
    for sx0, sx1, dx0, dx1 in x_cuts:
        for sy0, sy1, dy0, dy1 in y_cuts:
            target = (dx1 - dx0, dy1 - dy0)
            if target[0] <= 0 or target[1] <= 0:
                continue
            out.alpha_composite(source.crop((sx0, sy0, sx1, sy1)).resize(target, Image.NEAREST), (dx0, dy0))
    return out


def _run_width(runs: list) -> int:
    """Pen advance of the runs plus the overhang of the last sprite, so wide sprites get room."""
    width = sum(mcfont.width(font_id, value) for value, font_id, _ in runs)
    tail = next((mcfont.overhang(font_id, value) for value, font_id, _ in reversed(runs) if value), 0)
    return width + tail


def _line_width(line: Line) -> int:
    return _run_width(line.runs + line.right)


def _draw_runs(canvas: Image.Image, x: int, baseline: int, runs: list, zoom: int) -> None:
    for value, font_id, color in runs:
        if color is None:  # a pure offset run
            x += mcfont.width(font_id, value)
        elif color == "rainbow":  # a 100 % roll cycles through the rainbow, one colour per glyph
            for index, char in enumerate(value):
                x = mcfont.draw(canvas, x, baseline, char, font_id, tooltip.RAINBOW[index % len(tooltip.RAINBOW)], zoom)
        else:
            x = mcfont.draw(canvas, x, baseline, value, font_id, color, zoom)


def _wrapped(runs: list, width: int) -> list[list]:
    """Break a paragraph into lines that fit `width`, keeping each word's font and colour."""
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


def render_image(item: Item, *, scale: int = 4, color_lerp: bool = False, rolls: bool = True,
                 frame: bool = True, min_width: int = MIN_WIDTH) -> Image.Image:
    """The item tooltip as an RGBA image.

    - `scale`: output pixels per Minecraft pixel; 1 gives the raw game size.
    - `color_lerp`: slide roll colours between the stops instead of snapping to the flat five.
    - `rolls`: draw the roll percentages; off gives the plain game tooltip without the mod's brackets.
    - `frame`: draw the tier's background and frame; off leaves the text on a transparent canvas.
    - `min_width`: the narrowest text block, in Minecraft pixels; the game uses 140.
    """
    if scale < 1:
        raise ValueError("scale must be at least 1")
    lines = tooltip.build(item, rolls, color_lerp)

    # Fixed lines set the width; paragraphs are wrapped to it afterwards.
    width = max([min_width] + [_line_width(line) for line in lines if line.align != "wrap"])
    flat: list[Line] = []
    for line in lines:
        if line.align == "wrap":
            flat += [Line("left", part) for part in _wrapped(line.runs, width)]
        else:
            flat.append(line)

    size = (width + 2 * PAD_X, LINE_HEIGHT * len(flat) + 2 * PAD_Y)
    canvas = Image.new("RGBA", (size[0] * scale, size[1] * scale), (0, 0, 0, 0))
    if frame:
        tier = tooltip.tier_of(item)
        prefix = f"{tier}_" if tier in tooltip.FRAMED_TIERS else ""  # "set" has no sprite of its own
        shiny = "shiny_" if item.shiny is not None and prefix else ""
        for part in (f"{prefix}{shiny}background", f"{prefix}{shiny}frame"):
            canvas.alpha_composite(_nine_slice(part, *size).resize(canvas.size, Image.NEAREST))

    for index, line in enumerate(flat):
        baseline = PAD_Y + index * LINE_HEIGHT + BASELINE
        if line.align == "aligned":
            _draw_runs(canvas, PAD_X, baseline, line.runs, scale)
            _draw_runs(canvas, PAD_X + width - _run_width(line.right), baseline, line.right, scale)
        elif line.align == "center":
            _draw_runs(canvas, PAD_X + (width - _run_width(line.runs)) // 2, baseline, line.runs, scale)
        else:
            _draw_runs(canvas, PAD_X, baseline, line.runs, scale)
    return canvas


def render(item: Item, **options) -> bytes:
    """The item tooltip as PNG bytes; `options` are those of `render_image`."""
    buffer = io.BytesIO()
    render_image(item, **options).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
