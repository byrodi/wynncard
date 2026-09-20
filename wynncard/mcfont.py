"""Minecraft bitmap fonts, the subset Wynncraft's tooltips use.

A font file (`assets/mc/font/<id>.json`) lists providers: `bitmap` ones cut glyphs out of a texture
atlas, `space` ones only advance the pen, `reference` ones pull in another font. The first provider that
carries a character wins, the same way the game resolves them. Glyph advance is `round(inked width * scale) + 1`, with
`scale = height / cell height`, which is what makes text line up pixel for pixel with the game.
"""
import functools
import json
import os
from pathlib import Path

from PIL import Image, ImageChops

# The extracted resource pack; WYNNCARD_ASSETS points at a copy outside the package.
ASSETS = Path(os.environ.get("WYNNCARD_ASSETS") or Path(__file__).parent / "assets" / "mc")


class Glyph:
    """One character of a bitmap font: its cell image (None for pure spacing glyphs) and metrics.

    `advance` is how far the pen moves, `ascent` how far above the baseline the cell top sits and
    `height` how tall the cell is drawn, all in Minecraft pixels.
    """
    __slots__ = ("image", "advance", "ascent", "height", "colored", "overhang", "_sized")

    def __init__(self, image: Image.Image | None, advance: int, ascent: int, height: int):
        if image is not None:  # the text shader discards fragments under 10 % alpha
            image.putalpha(image.getchannel("A").point(lambda a: a if a >= 26 else 0))
        self.image, self.advance, self.ascent, self.height = image, advance, ascent, height
        self.colored = image is not None and _is_colored(image)
        drawn = round(image.width * height / image.height) if image is not None else 0
        self.overhang = max(0, drawn - advance)  # sprites wider than their advance, so lines leave room for them
        self._sized: dict[int, Image.Image] = {}

    def sized(self, zoom: int) -> Image.Image:
        """The glyph at output size: exactly `height` Minecraft pixels tall, nearest sampled like the game.

        A 12 px cell drawn 7 px tall gets uneven pixels, and so does the game's.
        """
        if zoom not in self._sized:
            factor = self.height / self.image.height * zoom
            size = (round(self.image.width * factor), self.height * zoom)
            self._sized[zoom] = self.image.resize(size, Image.NEAREST)
        return self._sized[zoom]


def _is_colored(cell: Image.Image) -> bool:
    """Sprites that carry their own colours are drawn as they are; grey ones take the text colour.

    A cell is grey when its red, green and blue channels are identical everywhere.
    """
    red, green, blue, alpha = cell.split()
    return ImageChops.difference(red, green).getbbox() is not None or \
        ImageChops.difference(green, blue).getbbox() is not None


@functools.cache
def _atlas(path: str) -> Image.Image:
    return Image.open(ASSETS / "textures" / path).convert("RGBA")


def _inked_width(cell: Image.Image) -> int:
    """Rightmost inked column of a cell: the game measures glyph width from the atlas, not the cell."""
    box = cell.getbbox()
    return box[2] if box else 0


@functools.cache
def font(font_id: str) -> dict[str, Glyph]:
    """Every glyph of a font, keyed by character; later providers override earlier ones."""
    glyphs: dict[str, Glyph] = {}
    for provider in json.loads((ASSETS / "font" / f"{font_id}.json").read_text())["providers"]:
        kind = provider.get("type")
        if kind == "reference":
            for char, found in font(provider["id"].split(":")[-1]).items():
                glyphs.setdefault(char, found)
        elif kind == "space":
            for char, advance in provider["advances"].items():
                glyphs.setdefault(char, Glyph(None, advance, 0, 0))
        elif kind == "bitmap":
            atlas = _atlas(provider["file"].split(":")[-1])
            rows = provider["chars"]
            cell_w, cell_h = atlas.width // len(rows[0]), atlas.height // len(rows)
            height = provider.get("height", 8)
            scale = height / cell_h
            for row, line in enumerate(rows):
                for col, char in enumerate(line):
                    if char == "\x00":
                        continue
                    cell = atlas.crop((col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h))
                    glyphs.setdefault(char, Glyph(cell, round(_inked_width(cell) * scale) + 1, provider["ascent"], height))
    return glyphs


def glyph(font_id: str, char: str) -> Glyph | None:
    """The glyph for `char`, or None when the font does not carry it."""
    return font(font_id).get(char)


def width(font_id: str, text: str) -> int:
    """Pen advance of `text` in Minecraft pixels; characters the font lacks take no space."""
    chars = font(font_id)
    return sum(g.advance for g in (chars.get(c) for c in text) if g is not None)


def overhang(font_id: str, text: str) -> int:
    """How far the last glyph sticks out past the pen position."""
    chars = font(font_id)
    found = next((chars.get(c) for c in reversed(text) if chars.get(c) is not None), None)
    return found.overhang if found else 0


def draw(canvas: Image.Image, x: int, baseline: int, text: str, font_id: str,
         color: str | tuple = "#ffffff", zoom: int = 1) -> int:
    """Draw text onto canvas at the pen position, `zoom` pixels per Minecraft pixel; returns the new pen x."""
    chars = font(font_id)
    tint = Image.new("RGBA", (1, 1), color).getpixel((0, 0))
    for char in text:
        found = chars.get(char)
        if found is None:
            continue
        if found.image is not None:
            sprite = found.sized(zoom)
            if tint[:3] != (255, 255, 255) and not found.colored:
                sprite = _tinted(sprite, tint)
            canvas.alpha_composite(sprite, (x * zoom, (baseline - found.ascent) * zoom))
        x += found.advance
    return x


def _tinted(sprite: Image.Image, tint: tuple) -> Image.Image:
    """Multiply a grey glyph by the text colour, the way the game colours its font."""
    red, green, blue, alpha = sprite.split()
    scale = lambda band, value: band.point(lambda pixel: pixel * value // 255)  # noqa: E731
    return Image.merge("RGBA", (scale(red, tint[0]), scale(green, tint[1]), scale(blue, tint[2]), alpha))
