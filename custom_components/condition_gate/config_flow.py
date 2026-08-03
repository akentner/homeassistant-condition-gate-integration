"""Config flow for condition_gate."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import selector
from homeassistant.helpers.template import Template

from .const import (
    ALLOWED_TARGET_DOMAINS,
    CONF_CONDITION,
    CONF_ICON_ACTIVE_OFF,
    CONF_ICON_ACTIVE_ON,
    CONF_ICON_INACTIVE,
    CONF_NAME,
    CONF_TARGET_ENTITY,
    DEFAULT_ICON_ACTIVE_OFF,
    DEFAULT_ICON_ACTIVE_ON,
    DEFAULT_ICON_INACTIVE,
    DOMAIN,
)


def _validate_template(template_str: str, hass) -> str | None:
    """Return None if the template parses, else an error message."""
    try:
        Template(template_str, hass)
    except TemplateError as err:
        return str(err)
    return None


def _target_domain(entity_id: str) -> str | None:
    """Return the domain prefix of an entity_id, or None if malformed."""
    if not isinstance(entity_id, str) or "." not in entity_id:
        return None
    return entity_id.split(".", 1)[0]


def _target_icon(hass: HomeAssistant, target: str) -> str | None:
    """Return the current icon attribute of the target entity, if any."""
    state: State | None = hass.states.get(target)
    if state is None:
        return None
    return state.attributes.get("icon")


def _resolve_icon_defaults(
    hass: HomeAssistant, target: str
) -> dict[str, str]:
    """Build the default values for the three icon fields.

    `inactive` and `active_on` inherit from the target entity's current
    icon. `active_off` always uses a custom fallback so that the
    "active but criterion not met" state is visually distinct from
    the target's plain-off icon.
    """
    inherited = _target_icon(hass, target) or DEFAULT_ICON_INACTIVE
    return {
        CONF_ICON_INACTIVE: inherited,
        CONF_ICON_ACTIVE_ON: inherited,
        CONF_ICON_ACTIVE_OFF: DEFAULT_ICON_ACTIVE_OFF,
    }


def _core_schema() -> vol.Schema:
    """Return the user / reconfigure schema with the three core fields
    plus the three optional icon overrides.

    The icon fields are `vol.Optional` with `str` type. They use the
    `IconSelector` so the form renders an MDI icon picker. The
    `selector.IconSelector()` is the canonical HA selector for icon
    fields. We accept any MDI icon string the user enters; if they
    leave it empty, the entry-creation path falls back to the
    `_*_defaults` computed from the target entity.
    """
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(str, vol.Length(min=1)),
            vol.Required(CONF_TARGET_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=list(ALLOWED_TARGET_DOMAINS),
                    multiple=False,
                )
            ),
            vol.Required(CONF_CONDITION): selector.TemplateSelector(),
            vol.Optional(
                CONF_ICON_INACTIVE, default=DEFAULT_ICON_INACTIVE
            ): selector.IconSelector(),
            vol.Optional(
                CONF_ICON_ACTIVE_ON, default=DEFAULT_ICON_ACTIVE_ON
            ): selector.IconSelector(),
            vol.Optional(
                CONF_ICON_ACTIVE_OFF, default=DEFAULT_ICON_ACTIVE_OFF
            ): selector.IconSelector(),
        }
    )


class ConditionGateConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the user-initiated and reconfigure config flows."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Only the three core fields are shown in the form. The three
        icon overrides are set to defaults (inherit from target, or
        `mdi:gate-alert` for active_off) and can be edited later via
        Reconfigure.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            target_entity: str = user_input[CONF_TARGET_ENTITY]
            condition: str = user_input[CONF_CONDITION]

            domain = _target_domain(target_entity)
            if domain is None or domain not in ALLOWED_TARGET_DOMAINS:
                errors[CONF_TARGET_ENTITY] = "unsupported_domain"
            elif _validate_template(condition, self.hass) is not None:
                errors[CONF_CONDITION] = "invalid_template"
            else:
                # Resolve icon defaults based on the chosen target.
                icon_defaults = _resolve_icon_defaults(
                    self.hass, target_entity
                )
                # Let HA auto-assign a unique id from the config entry.
                # The entity's unique_id is taken from entry.entry_id
                # in the entity platform, so multiple condition_gate
                # entries can coexist with different names and targets.
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_TARGET_ENTITY: target_entity,
                        CONF_CONDITION: condition,
                        CONF_ICON_INACTIVE: icon_defaults[CONF_ICON_INACTIVE],
                        CONF_ICON_ACTIVE_ON: icon_defaults[CONF_ICON_ACTIVE_ON],
                        CONF_ICON_ACTIVE_OFF: icon_defaults[CONF_ICON_ACTIVE_OFF],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_core_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure an existing entry.

        Only the three core fields are shown in the form. The three
        icon overrides are filled with the current values and
        pre-filled via `add_suggested_values_to_schema` so the form
        carries them through. They are then merged into `data_updates`
        on save.
        """
        entry = self._get_reconfigure_entry()
        current_target = entry.data[CONF_TARGET_ENTITY]

        # Build the schema with the current values pre-filled, plus the
        # icon values carried through as suggested values.
        schema = _core_schema()
        schema = self.add_suggested_values_to_schema(
            schema,
            {
                CONF_NAME: entry.data[CONF_NAME],
                CONF_TARGET_ENTITY: current_target,
                CONF_CONDITION: entry.data[CONF_CONDITION],
                CONF_ICON_INACTIVE: entry.data.get(
                    CONF_ICON_INACTIVE, DEFAULT_ICON_INACTIVE
                ),
                CONF_ICON_ACTIVE_ON: entry.data.get(
                    CONF_ICON_ACTIVE_ON, DEFAULT_ICON_ACTIVE_ON
                ),
                CONF_ICON_ACTIVE_OFF: entry.data.get(
                    CONF_ICON_ACTIVE_OFF, DEFAULT_ICON_ACTIVE_OFF
                ),
            },
        )

        if user_input is not None:
            errors: dict[str, str] = {}
            target_entity: str = user_input[CONF_TARGET_ENTITY]
            condition: str = user_input[CONF_CONDITION]

            domain = _target_domain(target_entity)
            if domain is None or domain not in ALLOWED_TARGET_DOMAINS:
                errors[CONF_TARGET_ENTITY] = "unsupported_domain"
            elif _validate_template(condition, self.hass) is not None:
                errors[CONF_CONDITION] = "invalid_template"

            if not errors:
                icon_defaults = _resolve_icon_defaults(
                    self.hass, target_entity
                )
                return self.async_update_reload_and_abort(
                    entry,
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_TARGET_ENTITY: target_entity,
                        CONF_CONDITION: condition,
                        CONF_ICON_INACTIVE: icon_defaults[CONF_ICON_INACTIVE],
                        CONF_ICON_ACTIVE_ON: icon_defaults[CONF_ICON_ACTIVE_ON],
                        CONF_ICON_ACTIVE_OFF: icon_defaults[CONF_ICON_ACTIVE_OFF],
                    },
                )

            # Validation failed - show the form again with the user's input pre-filled.
            schema = self.add_suggested_values_to_schema(schema, user_input)
            return self.async_show_form(
                step_id="reconfigure", data_schema=schema, errors=errors
            )

        return self.async_show_form(step_id="reconfigure", data_schema=schema)
