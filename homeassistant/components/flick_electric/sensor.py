"""Support for Flick Electric Pricing data."""
from datetime import timedelta
import logging

import async_timeout
from pyflick import FlickAPI, FlickPrice

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import ATTR_COMPONENTS, ATTR_END_AT, ATTR_START_AT, DOMAIN

_LOGGER = logging.getLogger(__name__)
_AUTH_URL = "https://api.flick.energy/identity/oauth/token"
_RESOURCE = "https://api.flick.energy/customer/mobile_provider/price"

SCAN_INTERVAL = timedelta(minutes=5)

ATTRIBUTION = "Data provided by Flick Electric"
FRIENDLY_NAME = "Flick Power Price"
UNIT_NAME = "cents"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Flick Sensor Setup."""
    api: FlickAPI = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([FlickPricingSensor(api)], True)


class FlickPricingSensor(SensorEntity):
    """Entity object for Flick Electric sensor."""

    _attr_native_unit_of_measurement = UNIT_NAME

    def __init__(self, api: FlickAPI) -> None:
        """Entity object for Flick Electric sensor."""
        self._api: FlickAPI = api
        self._price: FlickPrice = None
        self._attributes = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_FRIENDLY_NAME: FRIENDLY_NAME,
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return FRIENDLY_NAME

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._price.price

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_update(self):
        """Get the Flick Pricing data from the web service."""
        if self._price and self._price.end_at >= utcnow():
            return  # Power price data is still valid

        async with async_timeout.timeout(60):
            self._price = await self._api.getPricing()

        self._attributes[ATTR_START_AT] = self._price.start_at
        self._attributes[ATTR_END_AT] = self._price.end_at
        for component in self._price.components:
            if component.charge_setter not in ATTR_COMPONENTS:
                _LOGGER.warning("Found unknown component: %s", component.charge_setter)
                continue

            self._attributes[component.charge_setter] = float(component.value)
