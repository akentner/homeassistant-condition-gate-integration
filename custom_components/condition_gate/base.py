"""Shared logic for the condition_gate wrapper entity.

Both `light.py` and `switch.py` define a thin subclass that combines
`CriteriaBase` with the appropriate HA entity base class
(`LightEntity` or `SwitchEntity`). All the actual logic — restore,
template subscription, reconcile, force-off — lives here.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import (
    CALLBACK_TYPE,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.event import (
    TrackTemplate,
    TrackTemplateResult,
    async_track_template_result,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.template import Template

from .const import (
    CONF_CONDITION,
    CONF_ICON_ACTIVE_OFF,
    CONF_ICON_ACTIVE_ON,
    CONF_ICON_INACTIVE,
    CONF_TARGET_ENTITY,
    DEFAULT_ICON_ACTIVE_OFF,
    DEFAULT_ICON_ACTIVE_ON,
    DEFAULT_ICON_INACTIVE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class CriteriaBase(RestoreEntity):
    """Shared logic for criteria-driven wrapper entities.

    Subclasses pick the entity class: `LightEntity` for light targets,
    `SwitchEntity` for switch targets. Everything else — state, restore,
    template subscription, reconcile, force-off, service call dispatch
    — lives here and is identical for both subclasses.
    """

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the wrapper entity."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title

        self._is_on: bool = False
        self._criteria_met: bool = False
        self._target_state: str | None = None
        self._last_reconcile: datetime | None = None
        self._last_action: str | None = None
        self._last_error: str | None = None

        self._lock = asyncio.Lock()
        self._template: Template | None = None
        self._tracker_info: Any = None

    # ------------------------------------------------------------------
    # HA lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to template changes."""
        await super().async_added_to_hass()

        last_state: State | None = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

        # Register the entity in hass.data so the re_evaluate service
        # can find it.
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        self.hass.data[DOMAIN][self._entry.entry_id] = self

        template_str = self._entry.data[CONF_CONDITION]
        try:
            self._template = Template(template_str, self.hass)
        except TemplateError as err:
            self._last_error = f"template error: {err}"
            _LOGGER.error(
                "condition_gate %s template parse error: %s",
                self._attr_unique_id,
                err,
            )
            return

        # Bind `this` as a variable so the dependency-tracking render
        # does not warn that `this` is undefined. The reconcile path
        # re-renders the template with the same `this` binding.
        self._tracker_info = async_track_template_result(
            self.hass,
            [TrackTemplate(self._template, {"this": self})],
            self._handle_template_update,
        )

        await self._async_reconcile()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up subscriptions."""
        if self._tracker_info is not None:
            self._tracker_info.async_remove()
            self._tracker_info = None
        if DOMAIN in self.hass.data:
            self.hass.data[DOMAIN].pop(self._entry.entry_id, None)
        await super().async_will_remove_from_hass()

    # ------------------------------------------------------------------
    # Switch / light turn_on / turn_off (identical for both)
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the wrapper. Reconcile decides whether to turn the target on."""
        self._is_on = True
        self.async_write_ha_state()
        await self._async_reconcile()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the wrapper and force the target off."""
        self._is_on = False
        await self._async_force_off()
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Update path
    # ------------------------------------------------------------------

    @callback
    def _handle_template_update(
        self,
        event: Any,
        updates: list[TrackTemplateResult],
    ) -> None:
        """Triggered when any state referenced by the template changes."""
        self.hass.async_create_task(self._async_reconcile())

    # ------------------------------------------------------------------
    # Core reconcile
    # ------------------------------------------------------------------

    async def _async_reconcile(self) -> None:
        """Render the condition, decide on/off, fire service, update state."""
        async with self._lock:
            try:
                if not self._is_on:
                    await self._async_force_off()
                    return

                if self._template is None:
                    return

                result = self._template.async_render(variables={"this": self})
                self._criteria_met = _is_truthy(result)
                self._last_reconcile = datetime.now()

                if self._criteria_met:
                    await self._async_turn_on()
                else:
                    await self._async_turn_off()

                self._last_error = None
                target_id = self._entry.data[CONF_TARGET_ENTITY]
                target_state_obj = self.hass.states.get(target_id)
                self._target_state = (
                    target_state_obj.state if target_state_obj else None
                )

            except Exception as err:  # noqa: BLE001
                self._last_error = str(err)
                _LOGGER.error(
                    "condition_gate %s reconcile failed: %s",
                    self._attr_unique_id,
                    err,
                )

            self.async_write_ha_state()

    async def _async_turn_on(self) -> None:
        """Dispatch homeassistant.turn_on to the target entity."""
        target = self._entry.data[CONF_TARGET_ENTITY]
        try:
            await self.hass.services.async_call(
                "homeassistant",
                "turn_on",
                {"entity_id": target},
                blocking=True,
            )
            self._last_action = "on"
        except Exception as err:  # noqa: BLE001
            self._last_error = f"turn_on failed: {err}"
            _LOGGER.error(
                "condition_gate %s turn_on failed: %s",
                self._attr_unique_id,
                err,
            )

    async def _async_turn_off(self) -> None:
        """Dispatch homeassistant.turn_off to the target entity."""
        target = self._entry.data[CONF_TARGET_ENTITY]
        try:
            await self.hass.services.async_call(
                "homeassistant",
                "turn_off",
                {"entity_id": target},
                blocking=True,
            )
            self._last_action = "off"
        except Exception as err:  # noqa: BLE001
            self._last_error = f"turn_off failed: {err}"
            _LOGGER.error(
                "condition_gate %s turn_off failed: %s",
                self._attr_unique_id,
                err,
            )

    async def _async_force_off(self) -> None:
        """Force the target off (used by async_turn_off)."""
        await self._async_turn_off()
        target_id = self._entry.data[CONF_TARGET_ENTITY]
        target_state_obj = self.hass.states.get(target_id)
        self._target_state = (
            target_state_obj.state if target_state_obj else None
        )
        self._last_reconcile = datetime.now()
        self._criteria_met = False

    # ------------------------------------------------------------------
    # Properties shared by both subclasses
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        """Return whether the wrapper is active."""
        return self._is_on

    @property
    def icon(self) -> str:
        """Return the icon matching the current state and criterion.

        Three states are distinguished visually:
        - inactive: wrapper is off (target is force-off, user disabled)
        - active_on: wrapper is on AND condition is met (target is on)
        - active_off: wrapper is on BUT condition is not met (target off)

        The configured icon (from config flow) is used if set. If unset,
        `inactive` and `active_on` inherit the target's current icon;
        `active_off` always uses DEFAULT_ICON_ACTIVE_OFF so it is
        visually distinct from the target's plain-off state.
        """
        if not self._is_on:
            return self._entry_icon(CONF_ICON_INACTIVE, DEFAULT_ICON_INACTIVE)
        if self._criteria_met:
            return self._entry_icon(CONF_ICON_ACTIVE_ON, DEFAULT_ICON_ACTIVE_ON)
        return self._entry_icon(
            CONF_ICON_ACTIVE_OFF, DEFAULT_ICON_ACTIVE_OFF
        )

    def _entry_icon(self, key: str, default: str) -> str:
        """Return the configured icon, or fall back to the target's icon, or default."""
        configured = self._entry.data.get(key)
        if configured:
            return configured
        target_state = self.hass.states.get(
            self._entry.data[CONF_TARGET_ENTITY]
        )
        if target_state and target_state.attributes.get("icon"):
            return target_state.attributes["icon"]
        return default

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return debug attributes for the entity."""
        return {
            "criteria_met": self._criteria_met,
            "target_entity": self._entry.data[CONF_TARGET_ENTITY],
            "target_state": self._target_state,
            "last_reconcile": (
                self._last_reconcile.isoformat() if self._last_reconcile else None
            ),
            "last_action": self._last_action,
            "error": self._last_error,
        }


def _is_truthy(value: Any) -> bool:
    """Interpret a Jinja-rendered value as boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "on", "1")
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)
