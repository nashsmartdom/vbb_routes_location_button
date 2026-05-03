from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DESTINATION_ID,
    CONF_DESTINATION_NAME,
    CONF_MAX_TRANSFERS,
    CONF_MIN_DEPART_OFFSET_MIN,
    CONF_ORIGIN_ENTITY,
    CONF_RESULTS,
    CONF_TOP_N,
    DEFAULT_MAX_TRANSFERS,
    DEFAULT_MIN_DEPART_OFFSET_MIN,
    DEFAULT_RESULTS,
    DEFAULT_TOP_N,
    DOMAIN,
    VBB_JOURNEYS_URL,
)

_LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Berlin")

LINE_COLOURS = {
    "U1": ("#7DAD4B", "#FFFFFF"), "U2": ("#DA421E", "#FFFFFF"),
    "U3": ("#16683D", "#FFFFFF"), "U4": ("#F0D722", "#000000"),
    "U5": ("#7E5330", "#FFFFFF"), "U6": ("#8C6DAB", "#FFFFFF"),
    "U7": ("#009BD8", "#FFFFFF"), "U8": ("#224F86", "#FFFFFF"),
    "U9": ("#F3791D", "#FFFFFF"), "S1": ("#DB6394", "#FFFFFF"),
    "S2": ("#007734", "#FFFFFF"), "S3": ("#00983A", "#FFFFFF"),
    "S5": ("#EB7405", "#FFFFFF"), "S7": ("#6F4E9B", "#FFFFFF"),
    "S8": ("#55A822", "#FFFFFF"), "S9": ("#8A1002", "#FFFFFF"),
}
DEFAULT_COLOURS = {"subway": ("#333333", "#FFFFFF"), "suburban": ("#007A3D", "#FFFFFF"), "tram": ("#BE1414", "#FFFFFF"), "bus": ("#6A6A6A", "#FFFFFF"), "walking": ("#444444", "#FFFFFF")}


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TZ)


def fmt_time(value):
    return value.strftime("%H:%M") if value else None


def is_walking_leg(leg: dict[str, Any]) -> bool:
    return bool(leg.get("walking")) or not leg.get("line")


def get_line_colour(line_name: str | None, product: str | None):
    if line_name and line_name in LINE_COLOURS:
        return LINE_COLOURS[line_name]
    return DEFAULT_COLOURS.get(product or "", ("#555555", "#FFFFFF"))


def normalize_leg(leg: dict[str, Any]) -> dict[str, Any]:
    walking = is_walking_leg(leg)
    line = leg.get("line") or {}
    line_name = line.get("name")
    product = line.get("product") or line.get("mode")
    if walking:
        line_name = "Fußweg"
        product = "walking"
    bg, fg = get_line_colour(line_name, product)
    dep = parse_dt(leg.get("departure") or leg.get("plannedDeparture"))
    arr = parse_dt(leg.get("arrival") or leg.get("plannedArrival"))
    raw_delay = leg.get("departureDelay") if leg.get("departureDelay") is not None else leg.get("arrivalDelay")
    if raw_delay is None:
        raw_delay = leg.get("delay", 0)
    try:
        delay_min = int(raw_delay / 60)
    except (TypeError, ValueError):
        delay_min = 0
    duration_min = int((arr - dep).total_seconds() / 60) if dep and arr else None
    return {"line": line_name, "product": product, "walking": walking, "origin": (leg.get("origin") or {}).get("name"), "destination": (leg.get("destination") or {}).get("name"), "departure": fmt_time(dep), "arrival": fmt_time(arr), "duration_min": duration_min, "delay_min": delay_min, "bg": bg, "fg": fg}


def normalize_journey(journey: dict[str, Any], now: datetime):
    raw_legs = journey.get("legs") or []
    if not raw_legs:
        return None
    legs = [normalize_leg(leg) for leg in raw_legs]
    non_walking = [leg for leg in legs if not leg["walking"]]
    transfers = max(0, len(non_walking) - 1)
    leave_dt = parse_dt(raw_legs[0].get("departure") or raw_legs[0].get("plannedDeparture"))
    arrival_dt = parse_dt(raw_legs[-1].get("arrival") or raw_legs[-1].get("plannedArrival"))
    if not leave_dt or not arrival_dt:
        return None
    first_transport = next((leg for leg in raw_legs if not is_walking_leg(leg)), None)
    dep_dt = parse_dt(first_transport.get("departure") or first_transport.get("plannedDeparture")) if first_transport else leave_dt
    max_delay_min = max([int(leg.get("delay_min") or 0) for leg in legs] or [0])
    return {"leave_home": fmt_time(leave_dt), "departure": fmt_time(dep_dt), "arrival": fmt_time(arrival_dt), "duration_min": int((arrival_dt - leave_dt).total_seconds() / 60), "transfers": transfers, "minutes_until_leave": int((leave_dt - now).total_seconds() / 60), "change_at": non_walking[0]["destination"] if len(non_walking) >= 2 else None, "max_delay_min": max_delay_min, "legs": legs}


class VBBRoutesLocationCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.session = async_get_clientsession(hass)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)

    async def _async_update_data(self) -> dict[str, Any]:
        return await self._fetch_routes()

    def _origin_coordinates(self) -> tuple[float, float, str]:
        entity_id = self.entry.data[CONF_ORIGIN_ENTITY]
        state = self.hass.states.get(entity_id)
        if state is None:
            raise UpdateFailed(f"Origin entity not found: {entity_id}")
        lat = state.attributes.get("latitude")
        lon = state.attributes.get("longitude")
        if lat is None or lon is None:
            raise UpdateFailed(f"Origin entity has no latitude/longitude: {entity_id}")
        name = state.attributes.get("friendly_name") or entity_id
        return float(lat), float(lon), str(name)

    async def _fetch_routes(self) -> dict[str, Any]:
        d = self.entry.data
        now = datetime.now(TZ)
        lat, lon, origin_name = self._origin_coordinates()
        min_offset = int(d.get(CONF_MIN_DEPART_OFFSET_MIN, DEFAULT_MIN_DEPART_OFFSET_MIN))
        max_transfers = int(d.get(CONF_MAX_TRANSFERS, DEFAULT_MAX_TRANSFERS))
        results = int(d.get(CONF_RESULTS, DEFAULT_RESULTS))
        top_n = int(d.get(CONF_TOP_N, DEFAULT_TOP_N))
        params = {"from.latitude": lat, "from.longitude": lon, "from.address": origin_name, "to": d[CONF_DESTINATION_ID], "departure": (now + timedelta(minutes=min_offset)).isoformat(), "transfers": max_transfers, "results": results, "stopovers": "false", "remarks": "false", "language": "de"}
        try:
            async with self.session.get(VBB_JOURNEYS_URL, params=params, timeout=15) as response:
                if response.status != 200:
                    text = await response.text()
                    raise UpdateFailed(f"VBB HTTP {response.status}: {text[:300]}")
                payload = await response.json()
        except ClientError as err:
            raise UpdateFailed(f"VBB connection error: {err}") from err

        routes = []
        for journey in payload.get("journeys", []):
            route = normalize_journey(journey, now)
            if not route:
                continue
            if route["minutes_until_leave"] < min_offset:
                continue
            if route["transfers"] > max_transfers:
                continue
            routes.append(route)

        best_by_leave = {}
        for route in routes:
            key = route["leave_home"]
            if key not in best_by_leave or route["duration_min"] < best_by_leave[key]["duration_min"]:
                best_by_leave[key] = route
        routes = sorted(best_by_leave.values(), key=lambda r: (r["minutes_until_leave"], r["duration_min"], r["transfers"]))[:top_n]
        while len(routes) < top_n:
            routes.append(None)
        return {"api_ok": True, "updated_at": now.isoformat(), "origin": origin_name, "origin_entity": d[CONF_ORIGIN_ENTITY], "origin_latitude": lat, "origin_longitude": lon, "destination": d[CONF_DESTINATION_NAME], "routes": routes}
