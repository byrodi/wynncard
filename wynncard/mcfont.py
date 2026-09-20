"""Minecraft bitmap fonts, the subset Wynncraft's tooltips use.

A font file (`assets/mc/font/<id>.json`) lists providers: `bitmap` ones cut glyphs out of a texture
atlas, `space` ones only advance the pen, `reference` ones pull in another font. The first provider that
carries a character wins, the same way the game resolves them. Glyph advance is `round(inked width * scale) + 1`, with
`scale = height / cell height`, which is what makes text line up pixel for pixel with the game.
"""
import functools
import json
from pathlib import Path

from PIL import Image, ImageChops

ASSETS = Path(__file__).parent / "assets" / "mc"


class Glyph:
    __slots__ = ("image", "advance", "ascent", "height", "colored", "_sized")

    def __init__(self, image: Image.Image | None, advance: int, ascent: int, height: int):
        self.image, self.advance, self.ascent, self.height = image, advance, ascent, height
        self.colored = image is not None and _is_colored(image)
        self._sized: dict[int, Image.Image] = {}

    def sized(self, zoom: int) -> Image.Image:
        """The glyph at output size.

        The game squeezes some sprites to a fractional height (a 12 px cell drawn 7 px tall); doing that
        with resampling turns them to mush, so the whole sprite is scaled by whole pixels instead and
        stays crisp, at the cost of a pixel or two of height.
        """
        if zoom not in self._sized:
            pixels = max(1, round(self.height / self.image.height * zoom))
            size = (self.image.width * pixels, self.image.height * pixels)
            self._sized[zoom] = self.image if pixels == 1 else self.image.resize(size, Image.NEAREST)
        return self._sized[zoom]


def _is_colored(cell: Image.Image) -> bool:
    """Sprites that carry their own colours are drawn as they are; grey ones take the text colour."""
    red, green, blue, alpha = cell.split()
    return ImageChops.difference(red, green).getbbox() is not None or \
        ImageChops.difference(green, blue).getbbox() is not None


@functools.cache
def _atlas(path: str) -> Image.Image:
    return Image.open(ASSETS / "textures" / path).convert("RGBA")


def _inked_width(cell: Image.Image) -> int:
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
    return font(font_id).get(char)


def width(font_id: str, text: str) -> int:
    chars = font(font_id)
    return sum(g.advance for g in (chars.get(c) for c in text) if g is not None)


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
    red, green, blue, alpha = sprite.split()
    scale = lambda band, value: band.point(lambda pixel: pixel * value // 255)  # noqa: E731
    return Image.merge("RGBA", (scale(red, tint[0]), scale(green, tint[1]), scale(blue, tint[2]), alpha))
