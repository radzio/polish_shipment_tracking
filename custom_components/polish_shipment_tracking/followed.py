"""Shipments fetched one by one because the courier's list no longer has them."""
from __future__ import annotations

import time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.followed"
SAVE_DELAY = 10

# Stop following a shipment that has still not been delivered after this long.
FOLLOW_MAX_SECONDS = 30 * 24 * 3600


class FollowedShipments:
    """Per-account tracking numbers to fetch individually.

    InPost drops a courier parcel from its list once it is redirected to
    another address, although the parcel is still on its way and can be
    fetched by number. Such numbers are remembered here, per config entry, so
    they keep being tracked across restarts until delivery.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # entry_id -> {tracking_number: followed_since}
        self._items: dict[str, dict[str, float]] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load()
        items = (data or {}).get("followed")
        self._items = (
            {entry_id: dict(numbers) for entry_id, numbers in items.items()}
            if isinstance(items, dict)
            else {}
        )

    def numbers(self, entry_id: str) -> list[str]:
        """Return the followed numbers of an account, dropping expired ones."""
        numbers = self._items.get(entry_id, {})
        cutoff = time.time() - FOLLOW_MAX_SECONDS
        expired = [number for number, since in numbers.items() if since < cutoff]
        for number in expired:
            del numbers[number]
        if expired:
            self._schedule_save()
        return list(numbers)

    @callback
    def follow(self, entry_id: str, tracking_number: str) -> bool:
        """Start following a number. Return False if it already was."""
        numbers = self._items.setdefault(entry_id, {})
        if tracking_number in numbers:
            return False
        numbers[tracking_number] = time.time()
        self._schedule_save()
        return True

    @callback
    def unfollow(self, entry_id: str, tracking_number: str) -> None:
        if self._items.get(entry_id, {}).pop(tracking_number, None) is not None:
            self._schedule_save()

    def _schedule_save(self) -> None:
        self._store.async_delay_save(
            lambda: {"followed": {k: v for k, v in self._items.items() if v}}, SAVE_DELAY
        )
