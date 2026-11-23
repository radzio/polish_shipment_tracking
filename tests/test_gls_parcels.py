"""GLS parcel list endpoint and token persistence after a failed fetch.

These tests run without Home Assistant installed: ``api_gls`` is imported
directly, and ``_async_update_data`` is lifted out of ``coordinator.py`` by
parsing the file and executing just that one function in a controlled
namespace. Keep them dependency-free so they run in plain CI.
"""

import ast
import asyncio
import importlib.util
import logging
import sys
import types
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "polish_shipment_tracking"


def _load_api_gls():
    # ``api_gls`` only needs ``aiohttp`` importable (it builds requests at call
    # time, which the test overrides). Avoid ``importlib.util.find_spec`` here:
    # another test may have already put a spec-less stub module in
    # ``sys.modules``, and find_spec raises ValueError on a None __spec__.
    if "aiohttp" not in sys.modules:
        try:
            import aiohttp  # noqa: F401  (use the real one when installed)
        except ModuleNotFoundError:
            sys.modules["aiohttp"] = types.ModuleType("aiohttp")
    spec = importlib.util.spec_from_file_location("gls_api_gls", COMPONENT / "api_gls.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpdateFailed(Exception):
    pass


class ConfigEntryAuthFailed(Exception):
    pass


class InPostAuthError(Exception):
    pass


def _load_update_data():
    # Home Assistant is not installed here: load only the one method, with the
    # module-level names it references supplied by hand. ``_is_auth_rejection``
    # is stubbed to return False so the generic (transient) branch is taken —
    # that is the branch whose token-persistence behaviour we are testing.
    tree = ast.parse((COMPONENT / "coordinator.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_async_update_data":
            namespace = {
                "UpdateFailed": UpdateFailed,
                "ConfigEntryAuthFailed": ConfigEntryAuthFailed,
                "InPostAuthError": InPostAuthError,
                "_is_auth_rejection": lambda err: False,
                "_LOGGER": logging.getLogger("test_gls_parcels"),
            }
            module = ast.Module(body=[node], type_ignores=[])
            exec(compile(module, "coordinator.py", "exec"), namespace)
            return namespace["_async_update_data"]
    raise AssertionError("_async_update_data not found")


class FailingCoordinator:
    courier = "gls"

    def __init__(self, error):
        self.error = error
        self.persisted = 0

    async def _fetch_parcels_with_retry(self):
        raise self.error

    def _persist_auth_if_changed(self):
        self.persisted += 1


class GlsParcelListTests(unittest.TestCase):
    def test_parcel_list_uses_the_paged_endpoint(self):
        api_gls = _load_api_gls()
        api = api_gls.GlsApi(session=None, session_id="session")
        calls = []

        async def fake_request(method, url):
            calls.append((method, url))
            return {"content": []}

        api.request = fake_request
        self.assertEqual(asyncio.run(api.get_parcels()), {"content": []})

        method, url = calls[0]
        parsed = urlparse(url)
        self.assertEqual(method, "GET")
        self.assertTrue(parsed.path.endswith("/mygls-tracking/tracking/shipment/paged"))
        self.assertEqual(
            parse_qs(parsed.query),
            {"size": ["100"], "page": ["0"], "archive": ["false"]},
        )


class TokenPersistenceTests(unittest.TestCase):
    def test_failed_fetch_saves_a_refreshed_token(self):
        update_data = _load_update_data()
        coordinator = FailingCoordinator(Exception("GLS API Error: 500 - 404 page not found"))

        with self.assertLogs("test_gls_parcels", level="ERROR"):
            with self.assertRaises(UpdateFailed):
                asyncio.run(update_data(coordinator))

        self.assertEqual(coordinator.persisted, 1)

    def test_inpost_auth_failure_does_not_save_tokens(self):
        update_data = _load_update_data()
        coordinator = FailingCoordinator(InPostAuthError("rejected"))

        with self.assertRaises(ConfigEntryAuthFailed):
            asyncio.run(update_data(coordinator))

        self.assertEqual(coordinator.persisted, 0)


if __name__ == "__main__":
    unittest.main()
