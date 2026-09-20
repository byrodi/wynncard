"""Pull the fonts, sprites and tooltip frames wynncard needs out of a Wynncraft resource pack.

The pack ships with obfuscated local file headers, so entries are read straight from the offsets
in the central directory instead of through ZipFile.open.
"""
import json
import pathlib
import struct
import sys
import zipfile
import zlib

PACK = pathlib.Path.home() / "Library/Application Support/minecraft/downloads"
OUT = pathlib.Path(__file__).resolve().parent.parent / "wynncard/assets/mc"
FONTS = [
    "language/wynncraft", "tooltip/attribute/sprite", "tooltip/emblem/frame", "tooltip/emblem/sprite",
    "tooltip/requirement/frame", "tooltip/requirement/sprite", "tooltip/banner", "tooltip/divider",
    "tooltip/identification/major", "tooltip/page", "banner/box", "banner/symbol", "space", "common",
]
GUI = "assets/minecraft/textures/gui/sprites/tooltip/"


def newest_pack() -> pathlib.Path:
    packs = [p for p in PACK.glob("*/*") if p.is_file() and p.stat().st_size > 1_000_000]
    return max(packs, key=lambda p: p.stat().st_mtime)


class Pack:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.zip = zipfile.ZipFile(path)
        self.names = set(self.zip.namelist())

    def read(self, name: str) -> bytes:
        info = self.zip.getinfo(name)
        with open(self.path, "rb") as f:
            f.seek(info.header_offset)
            name_len, extra_len = struct.unpack("<HH", f.read(30)[26:30])
            f.seek(info.header_offset + 30 + name_len + extra_len)
            data = f.read(info.compress_size + 1_000_000)  # sizes in this pack are not trustworthy
        if info.compress_type == zipfile.ZIP_DEFLATED:
            data = zlib.decompressobj(-15).decompress(data)
        return _clean(data, name)


def _repair_png(data: bytes) -> bytes:
    """Rebuild a PNG whose chunk CRCs and zlib checksum Wynncraft broke on purpose.

    The game decodes with stb_image, which never verifies them; Pillow does, so the pixel data is
    recompressed into a clean stream and every checksum recomputed.
    """
    out, pixels, pos = bytearray(data[:8]), b"", 8
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b"IDAT":
            pixels += body
            continue
        if kind == b"IEND":
            packed = zlib.compress(zlib.decompressobj(-15).decompress(pixels[2:]), 9)
            for chunk in (b"IDAT" + packed, b"IEND"):
                out += (len(chunk) - 4).to_bytes(4, "big") + chunk + zlib.crc32(chunk).to_bytes(4, "big")
            return bytes(out)
        chunk = kind + body
        out += length.to_bytes(4, "big") + chunk + zlib.crc32(chunk).to_bytes(4, "big")
    return bytes(out)


def _clean(data: bytes, name: str) -> bytes:
    """Cut the payload out of the read-ahead buffer and repair it.

    Stored entries carry a bogus size, so a PNG is walked chunk by chunk until IEND, and the
    checksums Wynncraft breaks on purpose (the game never verifies them) are recomputed.
    """
    if name.endswith(".png"):
        return _repair_png(data)
    if name.endswith((".json", ".mcmeta")):
        text = data.decode("utf-8", "ignore")
        value, _ = json.JSONDecoder().raw_decode(text[text.index("{"):])
        return json.dumps(value).encode()
    return data


def save(pack: Pack, name: str) -> bool:
    if name not in pack.names:
        print("missing", name)
        return False
    target = OUT / name.replace("assets/minecraft/", "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pack.read(name))
    return True


def pull_font(pack: Pack, font_id: str, seen: set) -> None:
    if font_id in seen:
        return
    seen.add(font_id)
    name = f"assets/minecraft/font/{font_id}.json"
    if not save(pack, name):
        return
    for provider in json.loads(pack.read(name)).get("providers", []):
        if provider.get("type") == "reference":
            pull_font(pack, provider["id"].split(":")[-1], seen)
        elif provider.get("type") == "bitmap":
            save(pack, "assets/minecraft/textures/" + provider["file"].split(":")[-1])


def main() -> None:
    pack = Pack(newest_pack())
    print("pack:", pack.path.name, len(pack.names), "entries")
    seen = set()
    for font_id in FONTS:
        pull_font(pack, font_id, seen)
    for name in sorted(n for n in pack.names if n.startswith(GUI) and n.endswith((".png", ".mcmeta"))):
        save(pack, name)
    files = sorted(OUT.rglob("*"))
    total = sum(f.stat().st_size for f in files if f.is_file())
    print(f"{sum(f.is_file() for f in files)} files, {total / 1024:.0f} KB")


if __name__ == "__main__":
    sys.exit(main())
