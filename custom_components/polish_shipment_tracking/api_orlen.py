"""ORLEN Paczka public tracking client.

ORLEN Paczka has no account feed to list "my parcels": its public tracker is
keyed on the tracking number alone and answers JSONP (``callback({...});``).
Parcels are therefore added by number (``polish_shipment_tracking.track_shipment``).

Endpoint and status codes follow the MIT-licensed
https://github.com/ha-parcel-integrations/ha-orlen-paczka.
"""
from __future__ import annotations

import json

import aiohttp

TRACKING_URL = "https://nadaj.orlenpaczka.pl/parcel/api-status"

# Code 690 is used both for "waiting at the pickup point" and for a hand-over
# to a carrier abroad; only the label tells them apart.
_PICKUP_LABEL = "czeka na odbiór w punkcie"


class OrlenUnknownParcel(Exception):
    """The tracker does not know this number (err 1003 / 1004)."""


class OrlenApi:
    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    async def get_parcel(self, number: str) -> dict:
        """Return the normalized parcel for a tracking number.

        A number the tracker accepts but has no events for yet comes back with
        an empty status. Raises OrlenUnknownParcel when the tracker rejects it.
        """
        async with self._session.get(
            TRACKING_URL,
            params={"id": number, "jsonp": "callback"},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            if resp.status != 200:
                raise Exception(f"ORLEN Paczka API Error: {resp.status}")
            body = (await resp.text()).strip()

        if not body.startswith("callback(") or not body.endswith(");"):
            raise Exception("ORLEN Paczka API Error: unexpected JSONP wrapper")
        payload = json.loads(body[len("callback(") : -2])
        if not isinstance(payload, dict):
            raise Exception("ORLEN Paczka API Error: unexpected body")
        if payload.get("err") in (1003, 1004):
            raise OrlenUnknownParcel(f"ORLEN Paczka does not know {number} (err {payload['err']})")
        return self._normalize(number, payload)

    @staticmethod
    def _normalize(number: str, payload: dict) -> dict:
        history = [h for h in payload.get("history") or [] if isinstance(h, dict)]
        latest = history[-1] if history else {}
        code = str(latest.get("code") or "")
        label = latest.get("label") or ""
        if code == "690" and _PICKUP_LABEL in label.lower():
            code = "690_PICKUP"
        return {
            "number": number,
            "status": code,
            "label": label or None,
            "date": latest.get("date"),
            "history": [
                {"code": h.get("code"), "label": h.get("label"), "date": h.get("date")}
                for h in history
            ],
            # historyHtml is display markup; keep the structured fields only.
            "_raw_response": {k: v for k, v in payload.items() if k != "historyHtml"},
        }
