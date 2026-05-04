from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DESTINATION_ADDRESS,
    CONF_DESTINATION_ID,
    CONF_DESTINATION_LAT,
    CONF_DESTINATION_LON,
    CONF_DESTINATION_NAME,
    CONF_LOCATION_UPDATE_WAIT_SECONDS,
    CONF_MAX_TRANSFERS,
    CONF_MIN_DEPART_OFFSET_MIN,
    CONF_NOTIFY_SERVICE,
    CONF_ORIGIN_ENTITY,
    CONF_RESULTS,
    CONF_TOP_N,
    DEFAULT_DESTINATION_ADDRESS,
    DEFAULT_DESTINATION_ID,
    DEFAULT_DESTINATION_LAT,
    DEFAULT_DESTINATION_LON,
    DEFAULT_DESTINATION_NAME,
    DEFAULT_LOCATION_UPDATE_WAIT_SECONDS,
    DEFAULT_MAX_TRANSFERS,
    DEFAULT_MIN_DEPART_OFFSET_MIN,
    DEFAULT_NAME,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_ORIGIN_ENTITY,
    DEFAULT_RESULTS,
    DEFAULT_TOP_N,
    DOMAIN,
)

EDITABLE_KEYS = [
    CONF_ORIGIN_ENTITY,
    CONF_NOTIFY_SERVICE,
    CONF_LOCATION_UPDATE_WAIT_SECONDS,
    CONF_DESTINATION_ID,
    CONF_DESTINATION_NAME,
    CONF_DESTINATION_ADDRESS,
    CONF_DESTINATION_LAT,
    CONF_DESTINATION_LON,
    CONF_MIN_DEPART_OFFSET_MIN,
    CONF_MAX_TRANSFERS,
    CONF_RESULTS,
    CONF_TOP_N,
]


def build_schema(values: dict[str, Any] | None = None, *, include_name: bool = False) -> vol.Schema:
    values = values or {}
    schema: dict[Any, Any] = {}

    if include_name:
        schema[vol.Required(CONF_NAME, default=values.get(CONF_NAME, DEFAULT_NAME))] = str

    schema.update(
        {
            vol.Required(CONF_ORIGIN_ENTITY, default=values.get(CONF_ORIGIN_ENTITY, DEFAULT_ORIGIN_ENTITY)): str,
            vol.Optional(CONF_NOTIFY_SERVICE, default=values.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)): str,
            vol.Required(
                CONF_LOCATION_UPDATE_WAIT_SECONDS,
                default=values.get(CONF_LOCATION_UPDATE_WAIT_SECONDS, DEFAULT_LOCATION_UPDATE_WAIT_SECONDS),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=30)),
            vol.Optional(CONF_DESTINATION_ID, default=values.get(CONF_DESTINATION_ID, DEFAULT_DESTINATION_ID)): str,
            vol.Required(CONF_DESTINATION_NAME, default=values.get(CONF_DESTINATION_NAME, DEFAULT_DESTINATION_NAME)): str,
            vol.Optional(
                CONF_DESTINATION_ADDRESS,
                default=values.get(CONF_DESTINATION_ADDRESS, DEFAULT_DESTINATION_ADDRESS),
            ): str,
            vol.Optional(CONF_DESTINATION_LAT, default=values.get(CONF_DESTINATION_LAT, DEFAULT_DESTINATION_LAT)): vol.Coerce(float),
            vol.Optional(CONF_DESTINATION_LON, default=values.get(CONF_DESTINATION_LON, DEFAULT_DESTINATION_LON)): vol.Coerce(float),
            vol.Required(
                CONF_MIN_DEPART_OFFSET_MIN,
                default=values.get(CONF_MIN_DEPART_OFFSET_MIN, DEFAULT_MIN_DEPART_OFFSET_MIN),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
            vol.Required(CONF_MAX_TRANSFERS, default=values.get(CONF_MAX_TRANSFERS, DEFAULT_MAX_TRANSFERS)): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=5)
            ),
            vol.Required(CONF_RESULTS, default=values.get(CONF_RESULTS, DEFAULT_RESULTS)): vol.All(
                vol.Coerce(int), vol.Range(min=3, max=40)
            ),
            vol.Required(CONF_TOP_N, default=values.get(CONF_TOP_N, DEFAULT_TOP_N)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=6)
            ),
        }
    )
    return vol.Schema(schema)


class VBBRoutesLocationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return VBBRoutesLocationOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            data = dict(user_input)
            name = data.pop(CONF_NAME)
            dest_key = data.get(CONF_DESTINATION_ID) or data.get(CONF_DESTINATION_ADDRESS) or f"{data.get(CONF_DESTINATION_LAT)}_{data.get(CONF_DESTINATION_LON)}"
            unique_id = f"loc_{data[CONF_ORIGIN_ENTITY]}_{dest_key}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=name, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema(include_name=True),
            errors={},
        )


class VBBRoutesLocationOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            new_data = dict(self._config_entry.data)
            for key in EDITABLE_KEYS:
                if key in user_input:
                    new_data[key] = user_input[key]

            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=new_data,
                options={},
            )
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        values = dict(self._config_entry.data)
        values.update(self._config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(values),
            errors={},
        )
