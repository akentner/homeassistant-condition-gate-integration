"""Light platform for condition_gate.

This platform is selected when the target entity is a `light.*`.
The shared logic lives in `base.py`; this file is a thin subclass
that picks the correct HA entity base class and configures the
light-specific attributes (color_mode, supported_color_modes).

The light is an on/off light: brightness, color, and transition are
not exposed. The criteria switch only drives on/off.
"""

from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .base import CriteriaBase


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the criteria light entity from a config entry."""
    async_add_entities([CriteriaLightEntity(hass, entry)])


class CriteriaLightEntity(CriteriaBase, LightEntity):
    """A light that drives a light target based on a Jinja condition."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
