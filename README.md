# VBB Routes Location Button

Separate Home Assistant custom integration for manual VBB/BVG route queries from a dynamic Home Assistant location entity.

Domain:

```text
vbb_routes_location_button
```

## Purpose

This integration does not poll periodically. It only queries VBB after pressing its refresh button.

The start point is read from a Home Assistant entity with `latitude` and `longitude` attributes, for example:

```text
device_tracker.alisa_phone
person.alisa
```

## Installation via HACS

1. HACS → Custom repositories
2. Add:

```text
https://github.com/nashsmartdom/vbb_routes_location_button
```

3. Category: Integration
4. Download
5. Restart Home Assistant
6. Settings → Devices & services → Add integration → VBB Routes Location Button

## Configuration example

```text
Name: VBB Alisa Pankow
origin_entity: device_tracker.alisa_phone
Destination stop ID: 900130002
Destination name: S+U Pankow
Minimum departure offset: 7
Maximum transfers: 1
Raw results: 20
Number of route sensors: 3
```

## Entities

Example:

```text
button.vbb_alisa_pankow_refresh
sensor.vbb_alisa_pankow_route_1
sensor.vbb_alisa_pankow_route_2
sensor.vbb_alisa_pankow_route_3
```

## Lovelace example with VBB Routes Card

```yaml
type: custom:vbb-routes-card
title: Alisa → Pankow
origin: Standort Alisa
destination: S+U Pankow
buttonEntity: button.vbb_alisa_pankow_refresh
entities:
  - sensor.vbb_alisa_pankow_route_1
  - sensor.vbb_alisa_pankow_route_2
  - sensor.vbb_alisa_pankow_route_3
collapsed: true
buttonText: Route für Alisa anzeigen
maxRoutes: 3
maxTransfers: 1
hideMultiTransfer: true
```

## Notes

The integration uses the last known coordinates from the configured Home Assistant entity. It does not force the phone to update GPS before querying VBB.

Data source: <https://v6.vbb.transport.rest>
