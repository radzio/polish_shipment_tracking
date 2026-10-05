"""Persistent list of shipments the user chose to ignore."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.ignored"
SAVE_DELAY = 10

# An ignored shipment is forgotten once no courier has returned it for this
# long. The window is deliberately generous: an account that silently returns
# an empty list for a while (e.g. a disabled DPD user) must not wipe the list
# and resurrect every ignored shipment when it comes back.
PRUNE_AFTER_SECONDS = 30 * 24 * 3600
# Persisting "still seen" on every 15-min poll would be pointless disk churn.
SEEN_WRITE_INTERVAL_SECONDS = 6 * 3600


def normalize_tracking_number(value: Any) -> str:
    """Return the courier-agnostic key for a tracking number."""
    return "".join(ch for ch in str(value or "") if ch.isalnum()).upper()


class IgnoredShipments:
    """Ignore list shared by all accounts and couriers.

    Keyed by the normalized tracking number only, so ignoring a shipment hides
    it on every account that sees it, including its Allegro copy.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._items: dict[str, dict[str, Any]] = {}
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Load the list from storage and drop long-gone shipments."""
        data = await self._store.async_load()
        items = (data or {}).get("ignored")
        self._items = dict(items) if isinstance(items, dict) else {}
        if self._prune():
            self._schedule_save()

    def is_ignored(self, tracking_number: Any) -> bool:
        return normalize_tracking_number(tracking_number) in self._items

    @callback
    def mark_seen(self, tracking_number: Any) -> None:
        """Record that a courier still returns this ignored shipment."""
        item = self._items.get(normalize_tracking_number(tracking_number))
        if item is None:
            return
        now = time.time()
        if now - item.get("last_seen", 0) < SEEN_WRITE_INTERVAL_SECONDS:
            return
        item["last_seen"] = now
        self._schedule_save()

    @callback
    def async_ignore(self, tracking_number: Any, courier: str | None = None) -> bool:
        """Add a shipment to the list. Return False if it was already there."""
        key = normalize_tracking_number(tracking_number)
        if not key or key in self._items:
            return False
        now = time.time()
        self._items[key] = {
            "tracking_number": str(tracking_number).strip(),
            "courier": courier,
            "ignored_at": now,
            "last_seen": now,
        }
        self._prune()
        self._changed()
        return True

    @callback
    def async_unignore(self, tracking_number: Any) -> bool:
        """Remove a shipment from the list. Return False if it was not there."""
        if self._items.pop(normalize_tracking_number(tracking_number), None) is None:
            return False
        self._changed()
        return True

    def as_list(self) -> list[dict[str, Any]]:
        """Return the list for display, oldest first."""
        return [
            {
                "tracking_number": item.get("tracking_number"),
                "courier": item.get("courier"),
                "ignored_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%S%z", time.localtime(item.get("ignored_at", 0))
                ),
            }
            for item in sorted(self._items.values(), key=lambda i: i.get("ignored_at", 0))
        ]

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Call `listener` whenever a shipment is ignored or un-ignored."""
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    def _prune(self) -> bool:
        cutoff = time.time() - PRUNE_AFTER_SECONDS
        stale = [
            key
            for key, item in self._items.items()
            if item.get("last_seen", item.get("ignored_at", 0)) < cutoff
        ]
        for key in stale:
            del self._items[key]
        return bool(stale)

    def _changed(self) -> None:
        self._schedule_save()
        for listener in list(self._listeners):
            listener()

    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: {"ignored": self._items}, SAVE_DELAY)
