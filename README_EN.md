# Polish Shipment Tracking

Polska wersja: [README.md](README.md)

![Shipment Tracking card](images/screenshot.png)


[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Home Assistant integration for tracking shipments from popular carriers in Poland. It creates sensor entities for active shipments and includes a Lovelace card with a list of shipments.

## Features

- Multiple carriers supported in a single integration (Config Flow)
- Sensor entities for active shipments
- Status normalization into a common set of states
- Automatic discovery of new shipments and cleanup of old entities
- Built-in Lovelace card:
  - served by the integration
  - automatic resource registration for storage dashboards

> [!TIP]
> You can add multiple entries for the same carrier (e.g., your number and your spouse's account) – this works for every carrier, see [Multiple accounts per carrier](#multiple-accounts-per-carrier).

## Supported carriers

| Carrier | Login | Multiple accounts | Account identified by |
|---|---|:---:|---|
| InPost | phone number + SMS code | ✅ | phone number |
| DPD | phone number + SMS code | ✅ | phone number |
| DHL | phone number + SMS code | ✅ | phone number |
| Pocztex (Poczta Polska) | e-mail + password | ✅ | e-mail address |
| GLS | phone number + myGLS account password | ✅ | phone number |
| Allegro | `QXLSESSID` session cookie + account context (private / business) | ✅ | cookie and context (optional custom label) |
| UPS | pasted "Copy as cURL" of the `GetIncomingShipments` request from the ups.com dashboard | ✅ | pasted session |

### Multiple accounts per carrier

Every carrier supports multiple accounts – add the integration again and pick the same carrier with different credentials (e.g. two people's phone numbers). Each account is a separate entry with its own entities; the sensor's `account_contact` attribute tells you which account a shipment belongs to.

| Carrier | How multiple accounts behave |
|---|---|
| InPost | A parcel shared between your own accounts shows up only once (under the owner). Parcels shared by people outside the integration are still shown. |
| DPD, Pocztex | Accounts are independent – each has its own token. |
| DHL, GLS | Each account gets its own isolated session, so the accounts' cookies never mix. |
| Allegro | One entry per cookie and context. The same login can be added twice: as a private account and as Allegro Business. |
| UPS | One entry per pasted browser session. |

Notes:

- **Allegro** returns active packages only. A package already tracked through the real carrier's account (e.g. InPost or DHL) is not duplicated. When the cookie expires, the entry has to be added again.
- **UPS** has no login inside the integration – the session is taken over from the browser and kept alive by periodic polling.

> [!WARNING]
> The integration relies on unofficial APIs used by carrier apps/services. These APIs may change without notice.

> [!CAUTION]
> I am not responsible if a carrier blocks or limits a user account in any way.


## Requirements

- Home Assistant 2024.6 or newer
- (Optional) HACS 1.30 or newer

## Installation

### HACS (recommended)

1. Open HACS -> Integrations.
2. Add this repository as a Custom repository:
   - Repository: https://github.com/radzio/polish_shipment_tracking
   - Category: Integration
3. Install the integration.
4. Restart Home Assistant.

### Manual install

1. Copy `custom_components/polish_shipment_tracking` into:
   `<config>/custom_components/polish_shipment_tracking`
2. Restart Home Assistant.

## Configuration

1. Settings -> Devices and Services -> Add Integration
2. Search for "Polish Shipment Tracking"
3. Pick a carrier and provide the required credentials
4. Save

Sensor entities should appear after the first refresh.

## Entities

The integration creates one `sensor` per active (not delivered) shipment.

- unique_id: `<courier>_<shipment_id>`
- sensor state: normalized status (for example: in_transport)
- attributes: carrier-specific, commonly:
  - shipment number
  - raw status
  - event history
  - event timestamps
  - pickup point details

## Events (custom)

The integration fires events on the `hass.bus`:

- `polish_shipment_tracking_new_shipment` - new shipment detected
- `polish_shipment_tracking_shipment_status_changed` - shipment status changed

Example payload:

```json
{
  "courier": "inpost",
  "shipment_id": "1234567890",
  "entity_id": "sensor.inpost_paczka_1234567890",
  "status_raw": "in_transit",
  "status_key": "in_transport"
}
```

For `polish_shipment_tracking_shipment_status_changed`, additional fields are present:

- `old_status_raw`
- `old_status_key`
- `new_status_raw`
- `new_status_key`

## Status normalization

Carrier-specific status names are mapped to a common set, for example:
- created
- in_transport
- waiting_for_pickup
- delivered
- exception
- cancelled
- returned
- unknown

> [!NOTE]
> Status mapping is not complete yet; PRs with new mappings are welcome.

See the implementation in the integration code (sensor.py).

## Lovelace card


The integration bundles a Lovelace card (JavaScript module) and will automatically add it to Lovelace Resources.

## Debugging

Enable debug logs:

```yaml
logger:
  default: info
  logs:
    custom_components.polish_shipment_tracking: debug
```

## Known issues

* Carrier API/auth changes can break login or tracking.

## Issues and support

* Issues: [https://github.com/radzio/polish_shipment_tracking/issues](https://github.com/radzio/polish_shipment_tracking/issues)
* Pull requests are welcome.

When reporting a bug, include:

* Home Assistant version
* logs (with debug enabled)
* selected carrier
* reproduction steps

## License

GNU General Public License v3.0. See LICENSE.
