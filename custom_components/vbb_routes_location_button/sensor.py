from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TOP_N, DEFAULT_TOP_N, DOMAIN
from .coordinator import VBBRoutesLocationCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: VBBRoutesLocationCoordinator = hass.data[DOMAIN][entry.entry_id]
    top_n = int(entry.data.get(CONF_TOP_N, DEFAULT_TOP_N))
    async_add_entities([VBBLocationRouteSensor(coordinator, entry, i) for i in range(top_n)])


class VBBLocationRouteSensor(CoordinatorEntity[VBBRoutesLocationCoordinator], SensorEntity):
    _attr_icon = "mdi:map-marker-path"

    def __init__(self, coordinator: VBBRoutesLocationCoordinator, entry: ConfigEntry, index: int) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.index = index
        number = index + 1
        self._attr_name = f"{entry.title} Route {number}"
        self._attr_unique_id = f"{entry.entry_id}_location_route_{number}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, manufacturer="VBB", model="Location route query")

    @property
    def route(self) -> dict[str, Any] | None:
        data = self.coordinator.data or {}
        routes = data.get("routes") or []
        if self.index >= len(routes):
            return None
        return routes[self.index]

    @property
    def native_value(self) -> str | None:
        route = self.route
        return route.get("leave_home") if route else "—"

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        route = self.route
        attrs = {
            "route_available": route is not None,
            "api_ok": data.get("api_ok"),
            "updated_at": data.get("updated_at"),
            "origin": data.get("origin"),
            "origin_entity": data.get("origin_entity"),
            "origin_latitude": data.get("origin_latitude"),
            "origin_longitude": data.get("origin_longitude"),
            "destination": data.get("destination"),
        }
        if not route:
            return attrs
        attrs.update({
            "leave_home": route.get("leave_home"),
            "departure": route.get("departure"),
            "arrival": route.get("arrival"),
            "duration_min": route.get("duration_min"),
            "minutes_until_leave": route.get("minutes_until_leave"),
            "transfers": route.get("transfers"),
            "change_at": route.get("change_at"),
            "max_delay_min": route.get("max_delay_min"),
            "legs": route.get("legs"),
        })
        return attrs
