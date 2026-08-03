"""The condition_gate integration.

Wraps a light or switch entity in a user-facing entity of the same
domain that drives the target based on a Jinja condition. See
docs/architecture.md for the design rationale.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .base import CriteriaBase
from .const import ALLOWED_TARGET_DOMAINS, CONF_TARGET_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema

RE_EVALUATE_SERVICE = "re_evaluate"
RE_EVALUATE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)


def _target_domain(entity_id: str) -> str | None:
    """Return the domain prefix of an entity_id, or None if malformed."""
    if not isinstance(entity_id, str) or "." not in entity_id:
        return None
    return entity_id.split(".", 1)[0]


def _platform_for_target(target_entity: str) -> str | None:
    """Return the integration platform to forward the entry to.

    The target's domain determines the platform: a `light` target gets
    a `light.<name>` wrapper entity, a `switch` target gets a
    `switch.<name>` wrapper. The platform is fixed at setup time and
    does not change on reconfigure; if the user changes the target
    domain, the integration should be removed and re-added.
    """
    domain = _target_domain(target_entity)
    if domain == "light":
        return "light"
    if domain == "switch":
        return "switch"
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up condition_gate from a config entry.

    Forwards to the platform that matches the target entity's domain
    (light or switch). The form rejects other domains at config-flow
    time, so this dispatch always succeeds.
    """
    target = entry.data[CONF_TARGET_ENTITY]
    platform = _platform_for_target(target)
    if platform is None:
        _LOGGER.error(
            "condition_gate %s has unsupported target %s; remove and re-add",
            entry.entry_id,
            target,
        )
        return False
    await hass.config_entries.async_forward_entry_setups(entry, [platform])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, [ALLOWED_TARGET_DOMAINS])


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration-wide service handler (re_evaluate)."""

    async def _handle_re_evaluate(call: ServiceCall) -> None:
        requested: list[str] | None = call.data.get(ATTR_ENTITY_ID)
        for entry_id, entity in list(hass.data.get(DOMAIN, {}).items()):
            if not isinstance(entity, CriteriaBase):
                continue
            if requested and entity.entity_id not in requested:
                continue
            await entity._async_reconcile()  # noqa: SLF001

    hass.services.async_register(
        DOMAIN,
        RE_EVALUATE_SERVICE,
        _handle_re_evaluate,
        schema=RE_EVALUATE_SCHEMA,
    )
    return True
