from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, CoreState, EVENT_HOMEASSISTANT_STARTED, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.components import websocket_api
import voluptuous as vol

from .const import (
    ATTR_TRACKING_NUMBER,
    CONF_COURIER,
    DATA_IGNORED,
    DOMAIN,
    INTEGRATION_VERSION,
    PLATFORMS,
    SERVICE_IGNORE_SHIPMENT,
    SERVICE_UNIGNORE_SHIPMENT,
)
from .frontend import JSModuleRegistration
from .coordinator import ShipmentCoordinator
from .helpers import get_parcel_id
from .ignored import IgnoredShipments, normalize_tracking_number

_LOGGER = logging.getLogger(__name__)


async def _async_migrate_unique_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Account-scope per-parcel entity unique_ids.

    Old scheme `{courier}_{number}` (and `_refresh`/`_manage` variants) was not
    scoped per account, so two accounts of the same courier collided. Rewrite to
    `{courier}_{entry_id}_{number}`. Idempotent and per-entry; the refresh-all
    button already carries the entry_id so it is left untouched.
    """
    courier = entry.data.get(CONF_COURIER)
    if not courier:
        return
    prefix = f"{courier}_"
    scoped_prefix = f"{courier}_{entry.entry_id}"

    @callback
    def _migrator(entity_entry: er.RegistryEntry) -> dict | None:
        uid = entity_entry.unique_id or ""
        if not uid.startswith(prefix) or uid.startswith(scoped_prefix):
            return None
        rest = uid[len(prefix):]
        return {"new_unique_id": f"{courier}_{entry.entry_id}_{rest}"}

    await er.async_migrate_entries(hass, entry.entry_id, _migrator)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Shipment Tracking integration."""
    hass.data.setdefault(DOMAIN, {})

    ignored = IgnoredShipments(hass)
    await ignored.async_load()
    hass.data[DOMAIN][DATA_IGNORED] = ignored

    def _coordinators() -> list[ShipmentCoordinator]:
        return [c for c in hass.data[DOMAIN].values() if isinstance(c, ShipmentCoordinator)]

    def _tracking_number(call: ServiceCall) -> str:
        tracking_number = call.data[ATTR_TRACKING_NUMBER].strip()
        if not normalize_tracking_number(tracking_number):
            raise ServiceValidationError("tracking_number is empty")
        return tracking_number

    async def async_ignore_shipment(call: ServiceCall) -> None:
        """Hide a shipment on every account until it is un-ignored."""
        tracking_number = _tracking_number(call)
        key = normalize_tracking_number(tracking_number)
        courier = next(
            (
                c.courier
                for c in _coordinators()
                for parcel in (c.data or [])
                if normalize_tracking_number(get_parcel_id(parcel, c.courier)) == key
            ),
            None,
        )
        if not ignored.async_ignore(tracking_number, courier):
            return
        for coordinator in _coordinators():
            coordinator.async_apply_ignore_list()

    async def async_unignore_shipment(call: ServiceCall) -> None:
        """Track an ignored shipment again."""
        tracking_number = _tracking_number(call)
        if not ignored.async_unignore(tracking_number):
            return
        # The parcel was dropped from coordinator data, so it has to be refetched.
        for coordinator in _coordinators():
            await coordinator.async_request_refresh()

    service_schema = vol.Schema({vol.Required(ATTR_TRACKING_NUMBER): cv.string})
    hass.services.async_register(
        DOMAIN, SERVICE_IGNORE_SHIPMENT, async_ignore_shipment, schema=service_schema
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNIGNORE_SHIPMENT, async_unignore_shipment, schema=service_schema
    )

    async def async_register_frontend(_event=None) -> None:
        """Register the JavaScript modules after Home Assistant startup."""
        module_register = JSModuleRegistration(hass)
        await module_register.async_register()

    # Websocket handler to expose the integration version to the frontend.
    @websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/version"})
    @websocket_api.async_response
    async def websocket_get_version(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Handle version requests from the frontend."""
        connection.send_result(msg["id"], {"version": INTEGRATION_VERSION})

    websocket_api.async_register_command(hass, websocket_get_version)

    # Schedule frontend registration based on HA state.
    if hass.state == CoreState.running:
        await async_register_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, async_register_frontend)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up from a config entry."""
    await _async_migrate_unique_ids(hass, entry)

    coordinator = ShipmentCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        # Don't leak the DHL-owned aiohttp session if first refresh fails.
        await coordinator.async_close()
        raise

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Reactive Allegro dedup: when a NON-allegro courier's coordinator updates,
    # re-run every Allegro coordinator's cross-courier dedup so an Allegro copy
    # of a parcel now covered by its real courier is dropped promptly (instead
    # of waiting for Allegro's own ~15-min cycle). Allegro coordinators are
    # resolved dynamically, so this works regardless of entry load order and
    # covers multiple Allegro accounts.
    if coordinator.courier != "allegro":
        @callback
        def _rededup_allegro() -> None:
            for other in list(hass.data.get(DOMAIN, {}).values()):
                if isinstance(other, ShipmentCoordinator) and other.courier == "allegro":
                    other.rededup_from_cache()

        entry.async_on_unload(coordinator.async_add_listener(_rededup_allegro))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            await coordinator.async_close()

    # If no more entries, unregister frontend? 
    # Actually, keep it for now as there might be other entries.
    # The original code did some logic here for global sensor.
    
    return unload_ok

