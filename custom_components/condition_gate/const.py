"""Constants for the condition_gate integration."""

from __future__ import annotations

DOMAIN = "condition_gate"
PLATFORMS = ["light", "switch"]

CONF_NAME = "name"
CONF_TARGET_ENTITY = "target_entity"
CONF_CONDITION = "condition"

# Optional icon overrides. If unset, the wrapper inherits the icon
# from the target entity (via its current_state.attributes.icon) for
# active_on and inactive. For active_off (criterion not met, target
# forced off) a custom default is used because the target's icon in
# that state would just look like the inactive icon.
CONF_ICON_ACTIVE_ON = "icon_active_on"
CONF_ICON_ACTIVE_OFF = "icon_active_off"
CONF_ICON_INACTIVE = "icon_inactive"

# Only entities that have turn_on/turn_off services are supported.
# This is the set of domains where homeassistant.turn_on/turn_off can
# dispatch to the right service (light, switch).
ALLOWED_TARGET_DOMAINS = ("light", "switch")

# Fallback icon used when no override is configured and the target
# entity has no icon attribute. MDI style, simple gate with a small
# alert triangle, indicating "the gate is active but the criterion
# is not met".
DEFAULT_ICON_ACTIVE_ON = "mdi:gate-open"
DEFAULT_ICON_ACTIVE_OFF = "mdi:gate-alert"
DEFAULT_ICON_INACTIVE = "mdi:gate"
