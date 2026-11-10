# CellarTracker for Home Assistant

Brings your [CellarTracker](https://www.cellartracker.com) wine cellar into Home Assistant: what's in the cellar (per bottle location and bin), what you drank, and label images for your dashboards.

It reads CellarTracker's own export interface (the same one Excel web queries use), once an hour.

## What you get

| Entity | State | Attributes |
|---|---|---|
| `sensor.cellartracker_bottles` | bottles in the cellar | |
| `sensor.cellartracker_cellar_value` | total value | |
| `sensor.cellartracker_average_bottle_value` | average value per bottle | |
| `sensor.cellartracker_wines` | number of different wines | `wines`: one entry per wine with producer, vintage, type, drinking window, value, scores, `places` (location / bin / quantity) and `image` |
| `sensor.cellartracker_consumed_this_year` | bottles consumed this year | `consumed`: latest 250 consumed bottles with date and note, `per_year`, `total` |
| `sensor.cellartracker_last_update` | time of the last update | `tables`: rows and columns received (diagnostic) |
| `button.cellartracker_refresh` | fetch now | also picks up new photos |

The big list attributes are kept out of the recorder database.

## Bottle images

Images live in `/config/www/wine/` and are served as `/local/wine/...`:

* **Your own photos** win: name them after the CellarTracker wine number (`iWine`), for example `5534061.jpg` (`.jpg`, `.jpeg`, `.png`, `.webp`, any case).
* **Label images** (optional, off by default): the integration can try to download labels from CellarTracker's wine pages as `ct_<iWine>.jpg`, at most 5 per update. CellarTracker currently answers automated requests with a bot challenge (HTTP 202/405), so this usually finds nothing; `sensor.cellartracker_last_update` shows the last attempt. Turn it on in the integration options if that changes.

The `image` field of each wine already points at the right file, so dashboards don't have to guess.

## Installation

### Marketplace (Home Assistant 2026.11 and later) or HACS

Add this repository as a custom repository (category *Integration*), install **CellarTracker** and restart Home Assistant.

### Manual

Copy `custom_components/cellartracker` into your `/config/custom_components/` folder and restart.

## Setup

**Settings → Devices & services → Add integration → CellarTracker**, then log in with your CellarTracker user name and password.

Or, once, from `configuration.yaml` (the entry is imported; you can remove the lines afterwards):

```yaml
cellartracker:
  username: !secret cellartracker_username
  password: !secret cellartracker_password
```

Options: update interval (15–1440 minutes) and label downloads.

## Notes

* Your password is only sent to cellartracker.com and is stored in Home Assistant's config entry like any other integration.
* Not affiliated with CellarTracker.
