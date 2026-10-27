"""The game's text font as a web font, so the site's headings match the cards pixel for pixel.

    pip install fonttools
    python tools/build_font.py web/src/assets/minecraft.woff

Every glyph of `language/wynncraft` that is drawn 8 pixels tall becomes one square per inked pixel,
with the same advance the renderer uses. One pixel is 125 units, so the font is crisp at multiples of
8 CSS pixels.
"""
import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wynncard import mcfont  # noqa: E402

UNIT = 125  # font units per Minecraft pixel
ASCENT = 7  # pixels above the baseline, as in the font definition


def build(target: Path) -> None:
    glyphs = {"space": mcfont.glyph("language/wynncraft", " ")}
    cmap = {ord(" "): "space"}
    for char, found in mcfont.font("language/wynncraft").items():
        if found.image is not None and found.height == 8 and char.isprintable() and not char.isspace():
            name = f"uni{ord(char):04X}"
            glyphs[name] = found
            cmap[ord(char)] = name

    outlines, metrics = {".notdef": TTGlyphPen(None).glyph()}, {".notdef": (UNIT * 6, 0)}
    for name, found in glyphs.items():
        pen = TTGlyphPen(None)
        if found.image is not None:
            image = found.sized(1)
            for y in range(image.height):
                for x in range(image.width):
                    if image.getpixel((x, y))[3]:
                        top, left = (ASCENT - y) * UNIT, x * UNIT
                        pen.moveTo((left, top))
                        pen.lineTo((left + UNIT, top))
                        pen.lineTo((left + UNIT, top - UNIT))
                        pen.lineTo((left, top - UNIT))
                        pen.closePath()
        outlines[name] = pen.glyph()
        metrics[name] = (found.advance * UNIT, 0)

    builder = FontBuilder(UNIT * 8, isTTF=True)
    builder.setupGlyphOrder(list(outlines))
    builder.setupCharacterMap(cmap)
    builder.setupGlyf(outlines)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=ASCENT * UNIT, descent=-UNIT * 2)
    builder.setupNameTable({"familyName": "Wynncard Minecraft", "styleName": "Regular"})
    builder.setupOS2(sTypoAscender=ASCENT * UNIT, sTypoDescender=-UNIT * 2, usWinAscent=ASCENT * UNIT,
                     usWinDescent=UNIT * 2)
    builder.setupPost()
    builder.font.flavor = "woff"
    target.parent.mkdir(parents=True, exist_ok=True)
    builder.save(target)
    print(f"{len(cmap)} characters, {target.stat().st_size} bytes")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
