# Brand assets

Icon and logo for this integration, concept "box-as-pin" (a map pin whose
head is a taped parcel). Courier-neutral on purpose — the integration
aggregates many couriers, so it wears none of their brand colours.

Palette: PL red `#E11D2E` / `#B3101F`, white box, graphite text `#23272E`.
Vector sources in `src/` (edit those, then re-render).

## Files (`custom_integrations/polish_shipment_tracking/`)

| File | Size | Use |
|---|---|---|
| `icon.png` | 256×256 | square app icon, transparent |
| `icon@2x.png` | 512×512 | hi-dpi icon |
| `logo.png` / `logo@2x.png` | 560×160 / 1120×320 | wordmark, light backgrounds |
| `dark_logo.png` / `dark_logo@2x.png` | same | wordmark, dark backgrounds |

## Re-render

```sh
rsvg-convert -w 256  src/icon.svg      -o custom_integrations/polish_shipment_tracking/icon.png
rsvg-convert -w 512  src/icon.svg      -o custom_integrations/polish_shipment_tracking/icon@2x.png
rsvg-convert -w 560  src/logo.svg      -o custom_integrations/polish_shipment_tracking/logo.png
rsvg-convert -w 1120 src/logo.svg      -o custom_integrations/polish_shipment_tracking/logo@2x.png
rsvg-convert -w 560  src/dark_logo.svg -o custom_integrations/polish_shipment_tracking/dark_logo.png
rsvg-convert -w 1120 src/dark_logo.svg -o custom_integrations/polish_shipment_tracking/dark_logo@2x.png
```

## Publishing to home-assistant/brands

Home Assistant shows integration icons from the central
[home-assistant/brands](https://github.com/home-assistant/brands) repo, not
from this repo. To make the icon appear in HA/HACS, copy
`custom_integrations/polish_shipment_tracking/` into a PR against that repo
(the `custom_integrations/` folder there). Their CI trims and optimises the
PNGs and enforces the size rules.
