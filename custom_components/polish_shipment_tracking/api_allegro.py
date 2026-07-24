"""Allegro packages API client.

Allegro exposes an internal "packages" feed that powers the "Moje przesyłki"
page. It is authenticated with the single ``QXLSESSID`` session cookie and is
served from a per-context edge host:

    * private consumer account -> https://edge.allegro.pl/packages
    * business (Allegro Biznes) -> https://edge.business.allegro.pl/packages

Both contexts share the SAME ``QXLSESSID`` for a linked company login; the host
is what selects which package stream you get. Only ``QXLSESSID`` is required —
the anti-bot ``datadome`` / ``wdctx`` cookies are not needed for this endpoint.

Endpoint discovery / cookie approach inspired by
https://github.com/Przemko92/home-assistant-allegro (which uses the older
``api.allegro.pl/myorder-api/myorders`` order feed); this client targets the
lighter, active-only ``/packages`` feed instead.
"""

import aiohttp

from .api_helpers import request_json

# Allowed edge hosts, keyed by the context selected in the config flow.
ALLEGRO_HOSTS = {
    "private": "allegro.pl",
    "business": "business.allegro.pl",
}

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)


class AllegroApi:
    """Read-only client for the Allegro packages feed."""

    def __init__(self, session: aiohttp.ClientSession, cookie: str, host: str = "allegro.pl"):
        self._session = session
        # QXLSESSID value only (no name).
        self._cookie = (cookie or "").strip()
        # Full host, e.g. "allegro.pl" or "business.allegro.pl".
        self._host = (host or "allegro.pl").strip()

    def _headers(self) -> dict:
        return {
            "Accept": "application/vnd.allegro.internal.v1+json",
            "Accept-Language": "pl-PL",
            "Referer": f"https://{self._host}/",
            "Origin": f"https://{self._host}",
            "User-Agent": _USER_AGENT,
            "Cookie": f"QXLSESSID={self._cookie}",
        }

    async def get_parcels(self) -> dict:
        """Fetch active packages and return {"packages": [<normalized>, ...]}."""
        url = f"https://edge.{self._host}/packages"
        data = await request_json(
            self._session,
            "GET",
            url,
            headers=self._headers(),
            label="Allegro",
        )
        packages = []
        if isinstance(data, dict) and isinstance(data.get("packages"), list):
            packages = data["packages"]
        return {"packages": [self._normalize(p) for p in packages if isinstance(p, dict)]}

    async def validate(self) -> bool:
        """Return True if the cookie is accepted (used by the config flow)."""
        # get_parcels raises on 401/403; a dict result means the session works.
        result = await self.get_parcels()
        return isinstance(result, dict)

    @staticmethod
    def _normalize(pkg: dict) -> dict:
        """Flatten a raw package into the flat parcel dict the integration uses."""
        content = pkg.get("content") or {}
        order = pkg.get("order") or {}
        delivery = pkg.get("delivery") or {}
        desc = delivery.get("description") or {}
        pickup = delivery.get("pickup") or {}

        waybill = delivery.get("waybill")
        order_id = order.get("id")

        parcel = {
            # Identity: prefer the carrier waybill, fall back to the order id so
            # not-yet-shipped packages still get a stable unique id.
            "waybill": waybill,
            "order_id": order_id,
            "status": delivery.get("status"),
            "title": content.get("description"),
            "image_url": content.get("imageUrl"),
            "carrier": delivery.get("carrierId"),
            "carrier_icon": delivery.get("iconUrl"),
            "pickup_valid_to": pickup.get("validTo"),
            "delivery_title": desc.get("title"),
            "delivery_subtitle": desc.get("subtitle"),
            "order_url": order.get("url"),
            "_raw_response": pkg,
        }
        return parcel
