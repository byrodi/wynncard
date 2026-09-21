# wynncard-server

HTTP front for [wynncard](https://github.com/byrodi/wynncard): post an item as JSON, get its
tooltip back as a PNG, or post a list and get the cards of all of them.

wynncard renders the real in-game tooltip with the Minecraft bitmap fonts and the sprites from the
Wynncraft resource pack, which is why it stays Python. This is the smallest thing that lets a
process in another language use it: one endpoint on the standard library HTTP server, no framework.
The service holds no state.

## API

The full contract is in [openapi.yaml](openapi.yaml) (OpenAPI 3.1).

`POST /card` with a JSON body, answers `image/png`.

| Field | Type | Meaning |
|---|---|---|
| `listing` | object | A Wynnventory lot, exactly as `/trademarket/listings` returns it |
| `info` | object | The Wynnpool or Wynncraft v3 item, for base damage, requirements and major ids |
| `scales` | array | Wynnpool weight profiles as `[{"profile": "Main", "score": 94.6}]` |
| `scale` | int | Pixel zoom, 1 to 10, default 4 |

A listing alone renders fine, it simply has no base stats or requirements to draw. An `info`
without a `listing` renders the unrolled base item. A body that is a listing itself, with no
wrapper key, works too, so the raw API object can be piped straight through.

```sh
curl -X POST --data-binary @wynncard-server/tests/listing.json http://127.0.0.1:8765/card -o card.png
curl -X POST -d '{"listing": {...}, "scale": 2}' http://127.0.0.1:8765/card -o card.png
```

A JSON array of such objects renders a batch of up to 100 in one request. The answer is then
`application/json`, an array in the same order where each entry is `{"png": "<base64>"}` or
`{"error": "..."}`, so one broken item does not cost the others their cards.

```sh
curl -X POST -d '[{"listing": {...}}, {"info": {...}, "scale": 2}]' http://127.0.0.1:8765/card
```

`GET /health` answers `{"ok": true, "wynncard": "0.2.0"}`.

Errors come back as `{"error": "..."}`: 400 for a body that is not a renderable item, 413 over
4 MB, 404 for any other path, 500 when the render itself fails.

## Run

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/pip install -e . -e ./wynncard-server
.venv/bin/wynncard-server
```

Or in Docker, also from the root:

```sh
docker build -f wynncard-server/Dockerfile -t wynncard-server .
docker run --rm -p 127.0.0.1:8765:8765 wynncard-server
```

| Variable | Default | Meaning |
|---|---|---|
| `RENDER_HOST` | `127.0.0.1` | Bind address. Keep it on loopback, or on a private container network |
| `RENDER_PORT` | `8765` | Port |
| `RENDER_LOG_LEVEL` | `INFO` | Standard logging level |

There is no authentication, so the port must never be published to the internet. On one host that
means loopback; in compose it means a service without a `ports:` mapping.

A card costs about 25 ms and the font atlases load once at startup, so the first request is not the
one that pays for them.

## Tests

```sh
.venv/bin/python -m unittest discover -s wynncard-server/tests
```

The tests start the real server on a loopback port and talk to it over HTTP with a real Wynnventory
listing in `tests/listing.json`.
