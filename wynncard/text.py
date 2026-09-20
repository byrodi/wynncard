"""Text in the game's two fonts: ascii for letters, common for the icons in the private use area.

A line is a list of parts, each `(text, colour)`. Everything is drawn on a baseline, so an icon
and the text next to it sit on the same line whatever the two fonts' metrics say.
"""
import re
from pathlib import Path

from PIL import ImageFont

from .style import RAINBOW

ASSETS = Path(__file__).parent / "assets"
Part = tuple[str, str]
_FONTS: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, icons: bool = False) -> ImageFont.FreeTypeFont:
    return _FONTS.setdefault((size, icons), ImageFont.truetype(str(ASSETS / ("common.ttf" if icons else "ascii.ttf")), size))


def ascent(size: int) -> int:
    """Baseline offset from the top of a line of this size."""
    return font(size).getmetrics()[0]


def _runs(text: str):
    """Runs of (text, is_icon): private use area codepoints come from the common font."""
    out: list[list] = []
    for ch in text:
        icon = 0xE000 <= ord(ch) <= 0xF8FF
        if out and out[-1][1] == icon:
            out[-1][0] += ch
        else:
            out.append([ch, icon])
    return out


def measure(parts: list[Part], size: int) -> int:
    return sum(int(font(size, icon).getlength(run)) for text, _ in parts for run, icon in _runs(text))


def draw(d, x: int, baseline: int, parts: list[Part], size: int) -> int:
    """Draw parts left to right on `baseline`; returns the x the next part would start at."""
    for text, color in parts:
        for run, icon in _runs(text):
            f = font(size, icon)
            if color == "rainbow":
                for i, ch in enumerate(run):
                    d.text((x, baseline), ch, font=f, fill=RAINBOW[i % len(RAINBOW)], anchor="ls")
                    x += int(f.getlength(ch))
                continue
            d.text((x, baseline), run, font=f, fill=color, anchor="ls")
            x += int(f.getlength(run))
    return x


def draw_right(d, right: int, baseline: int, parts: list[Part], size: int) -> None:
    draw(d, right - measure(parts, size), baseline, parts, size)


def wrap(parts: list[Part], width: int, size: int) -> list[list[Part]]:
    lines: list[list[Part]] = []
    cur: list[Part] = []
    used = 0
    for text, color in parts:
        for word in re.findall(r"\S+\s*", text):
            w = measure([(word, color)], size)
            if used + w > width and cur:
                lines.append(cur)
                cur, used = [], 0
                word = word.lstrip()
                w = measure([(word, color)], size)
            cur.append((word, color))
            used += w
    return lines + ([cur] if cur else [])
