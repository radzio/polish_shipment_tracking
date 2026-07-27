"""UPS 'My Choice' / Package Portal API client — cookie/session based.

The logged-in UPS website dashboard loads incoming shipments from
``https://webapis.ups.com/ppc/api/AccountDashboard/GetIncomingShipments``,
authenticated by the session cookies + an ``X-CSRF-Token`` header that must
match the ``PPC-XSRF-TOKEN`` cookie. That CSRF cookie **rotates on every
response**, so we capture ``Set-Cookie`` and carry the new value forward. The
server session uses sliding expiration, so regular polling keeps it alive.

Seed: the user pastes the browser "Copy as cURL" of that request once; we
extract the cookies + ``addressToken``. UPS auth is Auth0 + app-only with no
headless re-login, so when the session eventually hits an absolute cap the
config entry must be re-seeded with a fresh cURL.
"""

import json
import re
from datetime import datetime, timedelta, timezone

import aiohttp

from .api_helpers import request_json

INCOMING_URL = "https://webapis.ups.com/ppc/api/AccountDashboard/GetIncomingShipments"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)


def parse_curl(curl_text: str) -> dict:
    """Extract {cookies, address_token, locale} from a copied cURL command."""
    text = curl_text or ""

    # Cookies: from `-b '...'` (or `--cookie '...'`), else a `-H 'cookie: ...'`.
    cookie_str = ""
    m = re.search(r"(?:-b|--cookie)\s+'([^']*)'", text)
    if not m:
        m = re.search(r"-H\s+'cookie:\s*([^']*)'", text, re.IGNORECASE)
    if m:
        cookie_str = m.group(1)

    cookies: dict = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            key = key.strip()
            if key:
                cookies[key] = value.strip()

    # addressToken + locale from the JSON body (`--data-raw '{...}'`).
    address_token = ""
    locale = "en_US"
    body_match = re.search(r"--data(?:-raw|-binary)?\s+'([^']*)'", text)
    if body_match:
        raw_body = body_match.group(1)
        try:
            body = json.loads(raw_body)
            address_token = body.get("addressToken") or ""
            locale = body.get("locale") or locale
        except Exception:
            token_match = re.search(r'"addressToken"\s*:\s*"([^"]+)"', raw_body)
            if token_match:
                address_token = token_match.group(1)
            loc_match = re.search(r'"locale"\s*:\s*"([^"]+)"', raw_body)
            if loc_match:
                locale = loc_match.group(1)

    # Ensure a CSRF value exists (prefer the cookie; fall back to the header).
    if not cookies.get("PPC-XSRF-TOKEN"):
        header_match = re.search(r"-H\s+'x-csrf-token:\s*([^']*)'", text, re.IGNORECASE)
        if header_match:
            cookies["PPC-XSRF-TOKEN"] = header_match.group(1).strip()

    return {"cookies": cookies, "address_token": address_token, "locale": locale}


class UpsApi:
    """Read-only client for the UPS incoming-shipments dashboard API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        cookies: dict,
        address_token: str,
        locale: str = "en_US",
    ):
        self._session = session
        # Managed explicitly via the Cookie header (session uses DummyCookieJar).
        self._cookies = dict(cookies or {})
        self._address_token = address_token or ""
        self._locale = locale or "en_US"

    def _headers(self) -> dict:
        return {
            "accept": "text/plain",
            "content-type": "application/json",
            "locale": self._locale,
            "origin": "https://www.ups.com",
            "referer": f"https://www.ups.com/ppc/dashboard.html?loc={self._locale}",
            "user-agent": _USER_AGENT,
            "x-csrf-token": self._cookies.get("PPC-XSRF-TOKEN", ""),
            "Cookie": "; ".join(f"{k}={v}" for k, v in self._cookies.items()),
        }

    def _capture_cookies(self, resp) -> None:
        """Absorb rotated cookies (PPC-XSRF-TOKEN, Akamai) from the response."""
        for raw in resp.headers.getall("Set-Cookie", []):
            first = raw.split(";", 1)[0]
            if "=" in first:
                key, value = first.split("=", 1)
                key = key.strip()
                if key and value:
                    self._cookies[key] = value

    async def get_parcels(self) -> dict:
        """Fetch incoming shipments; returns {"shipments": [<normalized>, ...]}."""
        now = datetime.now(timezone.utc)
        body = {
            "startDate": (now - timedelta(days=60)).strftime("%Y%m%d"),
            "endDate": (now + timedelta(days=45)).strftime("%Y%m%d"),
            "locale": self._locale,
            "addressToken": self._address_token,
        }
        data = await request_json(
            self._session,
            "POST",
            INCOMING_URL,
            json_data=body,
            headers=self._headers(),
            label="UPS",
            on_response=self._capture_cookies,
        )
        shipments = []
        if isinstance(data, dict):
            response = data.get("response") or {}
            for shipment in response.get("shipments") or []:
                if isinstance(shipment, dict):
                    shipments.append(self._normalize(shipment))
        return {"shipments": shipments}

    async def validate(self) -> bool:
        """Return True if the seeded cookies are accepted (config-flow check)."""
        await self.get_parcels()
        return True

    @staticmethod
    def _normalize(shipment: dict) -> dict:
        service = shipment.get("service") or {}
        from_parts = [shipment.get("shipFromCity") or "", shipment.get("shipFromCountry") or ""]
        return {
            "trackingNumber": shipment.get("trackingNumber"),
            "status": shipment.get("status"),
            "status_code": shipment.get("dpStatusCode"),
            "sender": (shipment.get("shipFromName") or "").strip(),
            "from_location": ", ".join(p for p in from_parts if p),
            "service": service.get("description"),
            "scheduled_delivery": shipment.get("scheduledDeliveryDate"),
            "delivery_date": shipment.get("deliveryDate"),
            "package_quantity": shipment.get("packageQuantity"),
            "activity": shipment.get("btActivity"),
            "_raw_response": shipment,
        }
