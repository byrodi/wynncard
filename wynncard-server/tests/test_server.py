"""The server is started for real on a loopback port and answered over HTTP, like its caller does."""
import base64
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from wynncard_server import Handler

LISTING = json.loads((Path(__file__).parent / "listing.json").read_text(encoding="utf-8"))
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def post(url: str, payload: dict | list) -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(), response.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_renders_a_market_listing(self):
        status, body, content_type = post(f"{self.url}/card", {"listing": LISTING})
        self.assertEqual(200, status)
        self.assertEqual("image/png", content_type)
        self.assertTrue(body.startswith(PNG_MAGIC))
        self.assertGreater(len(body), 2000)

    def test_takes_a_bare_listing_object(self):
        status, body, _ = post(f"{self.url}/card", LISTING)
        self.assertEqual(200, status)
        self.assertTrue(body.startswith(PNG_MAGIC))

    def test_scale_changes_the_size(self):
        small = post(f"{self.url}/card", {"listing": LISTING, "scale": 1})[1]
        big = post(f"{self.url}/card", {"listing": LISTING, "scale": 4})[1]
        self.assertTrue(small.startswith(PNG_MAGIC))
        self.assertGreater(len(big), len(small))

    def test_rejects_a_body_without_an_item(self):
        status, body, _ = post(f"{self.url}/card", {"scale": 2})
        self.assertEqual(400, status)
        self.assertIn("listing", json.loads(body)["error"])

    def test_rejects_an_impossible_scale(self):
        self.assertEqual(400, post(f"{self.url}/card", {"listing": LISTING, "scale": 99})[0])

    def test_rejects_bad_json(self):
        request = urllib.request.Request(f"{self.url}/card", data=b"{oops", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(400, caught.exception.code)

    def test_renders_a_batch_in_order(self):
        status, body, content_type = post(f"{self.url}/card", [{"listing": LISTING}, {"scale": 2}, LISTING])
        self.assertEqual(200, status)
        self.assertEqual("application/json", content_type)
        cards = json.loads(body)
        self.assertEqual(3, len(cards))
        self.assertTrue(base64.b64decode(cards[0]["png"]).startswith(PNG_MAGIC))
        self.assertIn("listing", cards[1]["error"])
        self.assertTrue(base64.b64decode(cards[2]["png"]).startswith(PNG_MAGIC))

    def test_rejects_an_empty_batch(self):
        self.assertEqual(400, post(f"{self.url}/card", [])[0])

    def test_rejects_an_oversized_batch(self):
        self.assertEqual(400, post(f"{self.url}/card", [{"scale": 1}] * 101)[0])

    def test_health(self):
        with urllib.request.urlopen(f"{self.url}/health", timeout=10) as response:
            self.assertEqual(200, response.status)
            self.assertTrue(json.loads(response.read())["ok"])

    def test_unknown_path(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"{self.url}/nope", timeout=10)
        self.assertEqual(404, caught.exception.code)


if __name__ == "__main__":
    unittest.main()
