import json
from pathlib import Path
from typing import Final

DOMAIN = "polish_shipment_tracking"
PLATFORMS = ["sensor", "button"]

CONF_COURIER = "courier"
CONF_PHONE = "phone"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
CONF_REFRESH_EXPIRES_AT = "refresh_expires_at"
CONF_DEVICE_UID = "device_uid"
CONF_ID_TOKEN = "id_token"
CONF_SESSION_ID = "session_id"
CONF_SESSION_REGISTERED = "session_registered"
# Allegro (cookie-based). CONF_COOKIE holds the QXLSESSID value; CONF_ALLEGRO_HOST
# selects the edge host (allegro.pl for private, business.allegro.pl for business).
CONF_COOKIE = "cookie"
CONF_ALLEGRO_HOST = "allegro_host"
CONF_ALLEGRO_CONTEXT = "allegro_context"
# UPS (cookie/session based, seeded from a copied cURL). Cookies are stored as a
# JSON string under the shared "cookies" key (same as DHL).
CONF_ADDRESS_TOKEN = "address_token"
CONF_UPS_LOCALE = "ups_locale"

# --- Frontend registration constants ---
_MANIFEST_PATH: Final[Path] = Path(__file__).parent / "manifest.json"


def _load_integration_version(manifest_path: Path) -> str:
    """Read the integration version from manifest.json with safe fallbacks."""
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_data = json.loads(manifest_text)
    except (OSError, json.JSONDecodeError):
        return "0.0.0"
    return str(manifest_data.get("version", "0.0.0"))


INTEGRATION_VERSION: Final[str] = _load_integration_version(_MANIFEST_PATH)

URL_BASE: Final[str] = "/polish-shipment-tracking"

# List of JavaScript modules to register with Lovelace.
JSMODULES: Final[list[dict[str, str]]] = [
    {
        "name": "Shipment Tracking Card",
        "filename": "shipment-tracking-card.js",
        "version": INTEGRATION_VERSION,
    }
]
