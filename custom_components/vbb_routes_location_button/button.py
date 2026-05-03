from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VBBRoutesLocationCoordinator


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: VBBRoutesLocationCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VBBLocationRefreshButton(coordinator, entry)])


class VBBLocationRefreshButton(CoordinatorEntity[VBBRoutesLocationCoordinator], ButtonEntity):
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(self, coordinator: VBBRoutesLocationCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = f"{entry.title} Refresh"
        self._attr_unique_id = f"{entry.entry_id}_refresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="VBB",
            model="Location route query",
        )

    @property
    def available(self) -> bool:
        # The button must stay available even before the first successful route query.
        # Otherwise the first manual refresh cannot be triggered.
        return True

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
