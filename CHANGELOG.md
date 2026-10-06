# Changelog

Changes in this fork of [stirante/polish_shipment_tracking](https://github.com/stirante/polish_shipment_tracking). Versions from 1.5.4 onwards are this fork's own and do not match upstream version numbers.

The same notes are published with each [GitHub release](https://github.com/radzio/polish_shipment_tracking/releases), which is where HACS reads them from.

## 1.8.2 – 2026-10-06

- Allegro: a package waiting to be handed to the carrier (status `PENDING`, "Przesyłka oczekuje na nadanie") is shown as "created" instead of "unknown".

## 1.8.1 – 2026-10-05

- **Ignore list cleans itself up.** An ignored shipment is removed from the list 24 hours after the account that used to return it stops returning it. If another account still returns it, it stays ignored. Entries no account can vouch for are still dropped after 30 days.

## 1.8.0 – 2026-10-05

- **Ignore shipments.** A shipment that will never arrive (for example a label the sender replaced) can be hidden, for every carrier:
  - from the card: the crossed-out eye icon in the shipment details, clicked twice;
  - with the `polish_shipment_tracking.ignore_shipment` action.
- `polish_shipment_tracking.unignore_shipment` brings a shipment back.
- The ignored shipments are listed in the `ignored_shipments` attribute of the "Active shipments" sensor.
- README: all supported carriers with their login method, and how multiple accounts per carrier behave.
- Manifest and README links point at this fork.

## 1.7.1 – 2026-09-14

- DPD: the `HANDED_OVER_FOR_DELIVERY_PUDO` status is recognised as "handed out for delivery" instead of "unknown".
- Pocztex: shipments the app has archived are treated as finished, so their sensors are removed.

## 1.7.0 – 2026-07-27

- **New carrier: UPS.** Set up by pasting a "Copy as cURL" of the `GetIncomingShipments` request from the ups.com dashboard; the session is kept alive by polling.

## 1.6.4 – 2026-07-25

- Allegro: a package that its real carrier starts tracking is dropped from Allegro within seconds, instead of showing twice until Allegro's next refresh.

## 1.6.3 – 2026-07-24

- Allegro: the seller (shop name) is shown as the sender.

## 1.6.2 – 2026-07-24

- Allegro: accounts are labelled "Private" / "Business" instead of "(None)".

## 1.6.1 – 2026-07-24

- Allegro: pickup code and QR code for packages waiting for pickup, and the real carrier's icon on each row.
- DHL: the Altcha captcha solver needed for logging in is back.

## 1.6.0 – 2026-07-24

- **New carrier: Allegro.** Uses the `QXLSESSID` session cookie, for private and business accounts. A package already tracked through its real carrier's account is not shown twice.

## 1.5.4 – 2026-07-08

First release of this fork, based on upstream 1.5.0.

- Multiple accounts of the same carrier no longer collide: entities are scoped per account, and DHL and GLS accounts each get their own isolated session.
- InPost: a parcel shared between your own accounts is shown once, under its owner.
- DHL: sender and timeline details, and all active shipments are fetched (the list is paginated).
- DPD: the sender falls back to the company name when the sender's name is empty.
