"""Switch platform for condition_gate.

This platform is selected when the target entity is a `switch.*`.
The shared logic lives in `base.py`; this file is a thin subclass
that picks the correct HA entity base class.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .base import CriteriaBase


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the criteria switch entity from a config entry."""
    async_add_entities([CriteriaSwitchEntity(hass, entry)])


class CriteriaSwitchEntity(CriteriaBase, SwitchEntity):
    """A switch that drives a switch target based on a Jinja condition."""

    _attr_device_class = SwitchDeviceClass.SWITCH
