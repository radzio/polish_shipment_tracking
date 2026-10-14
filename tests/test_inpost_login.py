"""Checks for the InPost browser sign-in helpers."""

import base64
import importlib.util
import json
import sys
import types
import unittest
import urllib.parse
from pathlib import Path


API_FILE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "polish_shipment_tracking"
    / "api_inpost.py"
)


def _load_api_inpost():
    # Load the module alone: Home Assistant and async_timeout are not
    # installed in this repository's lightweight test environment.
    package = types.ModuleType("inpost_pkg")
    package.__path__ = []
    helpers = types.ModuleType("inpost_pkg.api_helpers")
    helpers.request_json = None
    stubs = {
        "inpost_pkg": package,
        "inpost_pkg.api_helpers": helpers,
        "async_timeout": types.ModuleType("async_timeout"),
    }
    if importlib.util.find_spec("aiohttp") is None:
        aiohttp = types.ModuleType("aiohttp")
        aiohttp.ClientSession = object
        aiohttp.ClientError = Exception
        stubs["aiohttp"] = aiohttp
    for name, module in stubs.items():
        sys.modules.setdefault(name, module)
    spec = importlib.util.spec_from_file_location("inpost_pkg.api_inpost", API_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


API = _load_api_inpost()


def _jwt(payload):
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.signature"


class InPostLoginTests(unittest.TestCase):
    def setUp(self):
        self.login = API.InPostLogin()
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.login.url).query)
        self.state = query["state"][0]

    def test_url_asks_for_pkce_code_on_inpost_callback(self):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.login.url).query)
        self.assertEqual(query["client_id"], ["inpost-mobile"])
        self.assertEqual(query["redirect_uri"], ["https://account.inpost-group.com/callback"])
        self.assertEqual(query["code_challenge_method"], ["S256"])

    def test_extracts_code_from_callback_url(self):
        pasted = f" https://account.inpost-group.com/callback?code=abc-123&state={self.state} "
        self.assertEqual(self.login.extract_code(pasted), "abc-123")

    def test_rejects_url_from_another_attempt(self):
        pasted = "https://account.inpost-group.com/callback?code=abc&state=other"
        with self.assertRaisesRegex(ValueError, "state"):
            self.login.extract_code(pasted)

    def test_recognizes_pasted_sms_code(self):
        with self.assertRaisesRegex(ValueError, "sms"):
            self.login.extract_code("123 456")

    def test_rejects_page_without_code(self):
        pasted = "https://account.inpost-group.com/email-verify?lang=pl-PL&authCode=v2_x"
        with self.assertRaisesRegex(ValueError, "no_code"):
            self.login.extract_code(pasted)

    def test_reads_phone_from_access_token(self):
        token = _jwt({"phone": "600000000", "phone_prefix": "+48"})
        self.assertEqual(API.token_phone(token), "600000000")
        self.assertIsNone(API.token_phone("not-a-jwt"))


if __name__ == "__main__":
    unittest.main()
