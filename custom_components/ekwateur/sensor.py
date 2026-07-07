"""Sensor platform for the Ekwateur Billing integration.

Cost sensors are derived locally from existing HA energy sensors using the
flat per-kWh rates ported from the reference EkwateurBillingAPI Java project.
There is no polling and no call to any Ekwateur web service: sensors just
react to state changes of the consumption sensor(s) you point them at.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_CLIENT_CATEGORY,
    CONF_ELECTRICITY_SENSOR,
    CONF_GAS_SENSOR,
    CONF_PRO_CLIENT_TYPE,
    DOMAIN,
    get_rates,
)

# Consumption sensors are expected in kWh; these factors normalize the
# common alternative units so a Wh or MWh source still produces a correct cost.
_UNIT_TO_KWH: dict[str, Decimal] = {
    "wh": Decimal("0.001"),
    "kwh": Decimal("1"),
    "mwh": Decimal("1000"),
}


def _normalize_decimal_string(raw: str) -> str:
    """Normalize a number that may use a European comma decimal separator.

    HA sensor states are normally period-decimal, but sensors sourced from
    French utility data (scraped/template sensors) sometimes report values
    like "12,345" meaning 12.345, not 12345. A comma is only ever treated as
    a decimal point here, never dropped as if it were an English thousands
    separator, since that would silently inflate the value by ~1000x.
    """
    raw = raw.strip()
    if "," in raw and "." not in raw:
        return raw.replace(",", ".")
    if "," in raw and "." in raw:
        if raw.rindex(",") > raw.rindex("."):
            return raw.replace(".", "").replace(",", ".")
        return raw.replace(",", "")
    return raw


def _as_kwh(state: State | None) -> Decimal | None:
    """Convert a source sensor's state to a kWh Decimal, or None if unusable."""
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    try:
        value = Decimal(_normalize_decimal_string(state.state))
    except (InvalidOperation, TypeError):
        return None
    unit = (state.attributes.get("unit_of_measurement") or "kwh").lower()
    factor = _UNIT_TO_KWH.get(unit, Decimal("1"))
    return value * factor


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Ekwateur Billing cost sensors from a config entry."""
    data = entry.data
    electricity_rate, gas_rate = get_rates(
        data[CONF_CLIENT_CATEGORY], data.get(CONF_PRO_CLIENT_TYPE)
    )
    electricity_source = data.get(CONF_ELECTRICITY_SENSOR)
    gas_source = data.get(CONF_GAS_SENSOR)

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Ekwateur",
        model="Billing estimate",
    )

    entities: list[SensorEntity] = []
    if electricity_source:
        entities.append(
            EkwateurCostSensor(entry, device_info, "electricity", electricity_source, electricity_rate)
        )
        entities.append(EkwateurRateSensor(entry, device_info, "electricity", electricity_rate))
    if gas_source:
        entities.append(EkwateurCostSensor(entry, device_info, "gas", gas_source, gas_rate))
        entities.append(EkwateurRateSensor(entry, device_info, "gas", gas_rate))
    if electricity_source or gas_source:
        entities.append(
            EkwateurTotalCostSensor(
                entry, device_info, electricity_source, electricity_rate, gas_source, gas_rate
            )
        )

    async_add_entities(entities)


class EkwateurRateSensor(SensorEntity):
    """Flat €/kWh tariff sensor.

    This is what the Energy Dashboard's "use an entity with current price"
    (tariff) option expects: a numeric sensor whose unit ends in "/kWh".
    The EkwateurCostSensor below reports an accumulated EUR amount instead,
    which HA only accepts as a "track total cost" source, not as a tariff.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        energy_type: str,
        rate: Decimal,
    ) -> None:
        self._attr_translation_key = f"{energy_type}_rate"
        self._attr_unique_id = f"{entry.entry_id}_{energy_type}_rate"
        self._attr_device_info = device_info
        self._attr_native_unit_of_measurement = "EUR/kWh"
        self._attr_native_value = float(rate)


class EkwateurCostSensor(SensorEntity):
    """Cost sensor tracking a single energy source sensor at a flat rate."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        energy_type: str,
        source_entity_id: str,
        rate: Decimal,
    ) -> None:
        self._source_entity_id = source_entity_id
        self._rate = rate
        self._attr_translation_key = f"{energy_type}_cost"
        self._attr_unique_id = f"{entry.entry_id}_{energy_type}_cost"
        self._attr_device_info = device_info
        self._attr_extra_state_attributes = {
            "rate": float(rate),
            "source_entity_id": source_entity_id,
        }
        self._attr_native_value: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._recalculate(self.hass.states.get(self._source_entity_id))
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity_id], self._handle_source_event
            )
        )

    @callback
    def _handle_source_event(self, event: Event) -> None:
        self._recalculate(event.data.get("new_state"))
        self.async_write_ha_state()

    @callback
    def _recalculate(self, state: State | None) -> None:
        kwh = _as_kwh(state)
        self._attr_native_value = None if kwh is None else float(kwh * self._rate)


class EkwateurTotalCostSensor(SensorEntity):
    """Sum of the electricity and gas cost sensors for one client."""

    _attr_has_entity_name = True
    _attr_translation_key = "total_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        electricity_source: str | None,
        electricity_rate: Decimal,
        gas_source: str | None,
        gas_rate: Decimal,
    ) -> None:
        self._sources: dict[str, Decimal] = {}
        if electricity_source:
            self._sources[electricity_source] = electricity_rate
        if gas_source:
            self._sources[gas_source] = gas_rate
        self._attr_unique_id = f"{entry.entry_id}_total_cost"
        self._attr_device_info = device_info
        self._attr_native_value: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._recalculate()
        self.async_on_remove(
            async_track_state_change_event(self.hass, list(self._sources), self._handle_source_event)
        )

    @callback
    def _handle_source_event(self, event: Event) -> None:
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _recalculate(self) -> None:
        total = Decimal("0")
        has_value = False
        for entity_id, rate in self._sources.items():
            kwh = _as_kwh(self.hass.states.get(entity_id))
            if kwh is None:
                continue
            total += kwh * rate
            has_value = True
        self._attr_native_value = float(total) if has_value else None
