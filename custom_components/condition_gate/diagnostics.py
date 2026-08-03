"""Diagnostics support for condition_gate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .switch import CriteriaSwitchEntity

TO_REDACT = {"condition"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "unique_id": entry.unique_id,
            "entry_id": entry.entry_id,
        }
    }

    entity: CriteriaSwitchEntity | None = None
    for stacked in hass.data.get(DOMAIN, {}).values():
        if isinstance(stacked, CriteriaSwitchEntity):
            entity = stacked
            break

    if entity is not None:
        data["state"] = {
            "is_on": entity.is_on,
            "criteria_met": entity._criteria_met,
            "target_state": entity._target_state,
            "last_reconcile": (
                entity._last_reconcile.isoformat()
                if entity._last_reconcile
                else None
            ),
            "last_action": entity._last_action,
            "last_error": entity._last_error,
        }

    return data
