"""HTTP front for wynncard: post an item as JSON, get its tooltip back as a PNG, or post a list and
get a list of PNGs.

wynncard stays a plain library. This is the smallest thing that lets a process in another language
use it: one endpoint, the standard library HTTP server, no framework. It holds no state, so any
number of copies can run behind anything.
"""
import base64
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from wynncard import Item, __version__, from_market, from_wynnpool, render

MAX_BODY = 4 << 20  # a listing is a few kilobytes, a full batch a couple of megabytes
MAX_BATCH = 100
DEFAULT_SCALE = 4
MAX_SCALE = 10

log = logging.getLogger("wynncard-server")


def card(payload: dict) -> bytes:
    """PNG for one item.

    `listing` is a Wynnventory lot, `info` a Wynnpool item, `scales` its weight profiles. A lot
    alone renders fine, it just has no base stats or requirements to draw. A body that carries a
    listing at the top level instead of under a key works too, so the raw API object can be piped
    straight through.
    """
    listing = payload.get("listing")
    info = payload.get("info")
    if listing is None and info is None and ("stat_rolls" in payload or "hash_code" in payload):
        listing = payload
    if listing is None and info is None:
        raise ValueError("body needs a listing, an info object, or a listing at the top level")
    scale = payload.get("scale", DEFAULT_SCALE)
    if not isinstance(scale, int) or not 1 <= scale <= MAX_SCALE:
        raise ValueError(f"scale must be a whole number 1..{MAX_SCALE}")
    item = from_market(listing, info, payload.get("scales")) if listing is not None else from_wynnpool(info)
    return render(item, scale=scale)


def batch(payloads: list) -> list[dict]:
    """Cards for a list of items, in order. One broken item gets an error entry, not the whole batch."""
    out = []
    for payload in payloads:
        try:
            if not isinstance(payload, dict):
                raise ValueError("each item must be a json object")
            out.append({"png": base64.b64encode(card(payload)).decode()})
        except (ValueError, KeyError, TypeError) as e:
            out.append({"error": f"{type(e).__name__}: {e}"})
        except Exception as e:
            log.exception("render failed for %s", _name(payload))
            out.append({"error": f"{type(e).__name__}: {e}"})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = f"wynncard-server/{__version__}"
    protocol_version = "HTTP/1.1"  # keep alive: a scan sends its cards in one burst
    timeout = 30

    def do_GET(self) -> None:
        if self.path.split("?")[0] == "/health":
            self._send(200, json.dumps({"ok": True, "wynncard": __version__}).encode(), "application/json")
        else:
            self._fail(404, "GET /health or POST /card")

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/card":
            self._fail(404, "GET /health or POST /card")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._fail(400, "empty body")
            return
        if length > MAX_BODY:
            self._fail(413, f"body over {MAX_BODY} bytes")
            return
        started = time.monotonic()
        try:
            payload = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError) as e:
            self._fail(400, f"bad json: {e}")
            return
        if isinstance(payload, list):
            if not 1 <= len(payload) <= MAX_BATCH:
                self._fail(400, f"a batch holds 1..{MAX_BATCH} items")
                return
            cards = batch(payload)
            failed = sum("error" in c for c in cards)
            log.info("batch of %d, %d failed, in %d ms", len(cards), failed, (time.monotonic() - started) * 1000)
            self._send(200, json.dumps(cards).encode(), "application/json")
            return
        if not isinstance(payload, dict):
            self._fail(400, "body must be a json object or an array of them")
            return
        try:
            png = card(payload)
        except (ValueError, KeyError, TypeError) as e:
            self._fail(400, f"{type(e).__name__}: {e}")
            return
        except Exception as e:  # a broken sprite or an unknown item shape must not kill the server
            log.exception("render failed")
            self._fail(500, f"{type(e).__name__}: {e}")
            return
        log.info("card %s: %d bytes in %d ms", _name(payload), len(png), (time.monotonic() - started) * 1000)
        self._send(200, png, "image/png")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, status: int, message: str) -> None:
        self._send(status, json.dumps({"error": message}).encode(), "application/json")

    def log_message(self, fmt: str, *args) -> None:
        log.debug(fmt, *args)


def _name(payload: dict) -> str:
    source = payload.get("listing") or payload.get("info") or payload
    return str(source.get("name", "?"))[:40] if isinstance(source, dict) else "?"


def warm() -> None:
    """First render pays for the font atlases and the tooltip sprites; pay it before serving."""
    started = time.monotonic()
    render(Item("Warmup"), scale=1)
    log.info("assets loaded in %d ms", (time.monotonic() - started) * 1000)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("RENDER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    host = os.environ.get("RENDER_HOST", "127.0.0.1")
    port = int(os.environ.get("RENDER_PORT", "8765"))
    warm()
    server = ThreadingHTTPServer((host, port), Handler)
    log.info("wynncard-server %s on http://%s:%d", __version__, host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
