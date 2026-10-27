"""Everything the web editor loads besides its own code, written under one output directory.

    python tools/build_site_data.py web/public [--source items.json] [--weights weights.json]

- `py/wynncard.zip`: the library with its assets, unpacked into Pyodide's site-packages in the browser.
- `data/stats.json`: the identification table for the stat picker, in tooltip order.
- `og.png`: the link preview, a perfectly rolled Spring on the site's background.
- `data/index.json`: every gear item of the Wynncraft v3 item database as
  `[name, tier, type, level, file]`, sorted by name, for the preset search. Some items share a name,
  like Aftershock and the Masterwork Aftershock that also prints as Aftershock; such a row gets the
  internal name as a sixth field.
- `data/items/<file>.json`: one preset per item, `{"item": <spec dict of the base item>,
  "rolls": {stat key: [every value it can roll, worst first]}}`; fixed identifications have no rolls.
  An item Wynnpool weighs also gets `"weights": [{"name": "Main", "stats": {stat key: weight}}]`.

The item database comes from the API unless `--source` names a saved copy. Each item is checked on the
way: it has to render, and its roll range has to match the API's min and max, so a change on
Wynncraft's side fails the build instead of shipping wrong presets.

The Wynnpool weights come from Wynnpool's API unless `--weights` names a saved copy. They are a third
party's extra: when the request fails the build warns and goes on without them.
"""
import argparse
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from wynncard import from_wynnpool, render_image, rolls, stats, to_dict  # noqa: E402

API = "https://api.wynncraft.com/v3/item/database?fullResult"
WEIGHTS_API = "https://api.wynnpool.com/item/weight/all"
GEAR = ("weapon", "armour", "accessory")
PREVIEW_ITEM, PREVIEW_SIZE, PREVIEW_BACKGROUND = "Spring", (1200, 630), "#faf8f9"


def package(out: Path) -> None:
    target = out / "py" / "wynncard.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "wynncard").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(ROOT))


def stat_table(out: Path) -> None:
    rows = [{"key": t.key, "name": t.name, "unit": t.unit, "api": t.api, "inverted": t.inverted}
            for t in stats.TYPES]
    _write(out / "data" / "stats.json", rows)


def weights(source: str | None) -> dict[str, list[dict]]:
    """Wynnpool's weight profiles by internal item name, with stats renamed to Wynntils keys."""
    try:
        profiles = json.loads(Path(source).read_text()) if source else _get(WEIGHTS_API)
    except (OSError, ValueError) as e:
        print(f"warning: no Wynnpool weights, the presets go without them: {e}", file=sys.stderr)
        return {}
    out: dict[str, list[dict]] = {}
    for profile in profiles:
        weighted = {}
        for api, weight in (profile.get("identifications") or {}).items():
            stat = stats.lookup(api)
            if stat is not None:
                weighted[stat.key] = weight
        out.setdefault(profile.get("item_id"), []).append({"name": profile.get("weight_name") or "Scale",
                                                            "stats": weighted})
    return out


def items(out: Path, source: str | None, weighed: dict[str, list[dict]] | None = None) -> int:
    database = json.loads(Path(source).read_text()) if source else _get(API)
    gear = sorted((info for info in database if info.get("type") in GEAR), key=lambda info: _name(info).lower())
    index, files, problems = [], set(), []
    for info in gear:
        name = _name(info)
        try:
            item = from_wynnpool(info)
            render_image(item, scale=1)
            preset = {"item": to_dict(item), "rolls": _rolls(info)}
        except (ValueError, KeyError, TypeError) as e:  # a broken entry is reported, the rest still build
            problems.append(f"{name}: {type(e).__name__}: {e}")
            continue
        internal = info.get("internalName") or name
        if (weighed or {}).get(internal):
            preset["weights"] = weighed[internal]
        file = _slug(internal)
        while file in files:
            file += "_"
        files.add(file)
        _write(out / "data" / "items" / f"{file}.json", preset)
        row = [name, item.tier, item.type, item.requirements.level, file]
        index.append(row + [internal] if internal != name else row)
    _write(out / "data" / "index.json", index)
    preview(out, next((info for info in gear if info.get("internalName") == PREVIEW_ITEM), None))
    for problem in problems:
        print("problem:", problem, file=sys.stderr)
    print(f"{len(index)} presets, {len(problems)} problems")
    return len(problems)


def preview(out: Path, info: dict | None) -> None:
    """The link preview: the item with every roll at its best, centred on the site's background."""
    if info is None:
        print(f"warning: no {PREVIEW_ITEM} in the database, no link preview", file=sys.stderr)
        return
    item = from_wynnpool(info)
    best = _rolls(info)
    for stat in item.identifications:
        if stat.key in best:
            stat.value, stat.roll = best[stat.key][-1], 100.0
    item.overall_roll = 100.0
    card = render_image(item, scale=2)
    canvas = Image.new("RGBA", PREVIEW_SIZE, PREVIEW_BACKGROUND)
    canvas.alpha_composite(card, ((canvas.width - card.width) // 2, max(0, (canvas.height - card.height) // 2)))
    canvas.convert("RGB").save(out / "og.png", optimize=True)


def _rolls(info: dict) -> dict[str, list[int]]:
    """Possible values of each rolling identification, checked against the range the API states."""
    out = {}
    for api, value in (info.get("identifications") or {}).items():
        if not isinstance(value, dict):
            continue  # a plain number never rolls
        stat = stats.lookup(api)
        if stat is None:
            raise ValueError(f"unknown identification {api}")
        possible = rolls.values(value["raw"], stat.inverted)
        if {possible[0], possible[-1]} != {value["min"], value["max"]}:
            raise ValueError(f"{api} rolls {possible[0]}..{possible[-1]}, the API says {value['min']}..{value['max']}")
        if len(possible) > 1:
            out[stat.key] = possible
    return out


def _get(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "wynncard-site-data"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _name(info: dict) -> str:
    return info.get("displayName") or info.get("internalName") or "?"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "item"


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", type=Path, help="directory the site serves as its root, e.g. web/public")
    parser.add_argument("--source", help="a saved copy of the item database instead of the API")
    parser.add_argument("--weights", help="a saved copy of the Wynnpool weights instead of their API")
    args = parser.parse_args()
    package(args.out)
    stat_table(args.out)
    sys.exit(1 if items(args.out, args.source, weights(args.weights)) else 0)


if __name__ == "__main__":
    main()
