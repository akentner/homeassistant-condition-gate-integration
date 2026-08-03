# Configuration

## Installation

### Manual (local development)

1. Copy the entire `custom_components/condition_gate/` directory into
   your HA config directory under `custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **Condition Gate**.

### HACS (after publishing)

1. HACS → Integrations → ⋯ → Custom repositories → add the repo URL.
2. Install **Condition Gate**.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → **Condition Gate**.

## Config flow

The user-facing form has three fields.

| Field | Selector | Description |
|---|---|---|
| Name | `text` | Display name shown in the UI. |
| Target entity | `entity` (filter: `light`, `switch`) | The light or switch entity this drives. |
| Condition template | `template` (multi-line, syntax highlighting) | Jinja expression that evaluates to truthy/falsy. |

### Supported target domains

Only `light` and `switch` are accepted. The integration dispatches
`homeassistant.turn_on` / `homeassistant.turn_off` to dispatch to the
right per-domain service. Other domains (`scene`, `automation`,
`input_boolean`, `media_player`, ...) are rejected at config-flow
time with the error `Target must be a light or switch entity.`

### Wrapper matches target domain

The wrapper entity itself is in the same domain as the target:

| Target | Wrapper entity |
|---|---|
| `light.livingroom22_candles` | `light.condition_gate_<name>` |
| `switch.some_switch` | `switch.condition_gate_<name>` |

The platform is determined at setup time from the target's domain
and does not change on reconfigure. To change the wrapper's domain,
remove the entry and re-add it.

### Validation

The form blocks submission if:

* The target entity's domain is not `light` or `switch`.
* The condition template fails to parse (e.g. unbalanced braces).

The form aborts with a generic message if the same target entity is
already configured (unique-id protection).

## Reconfigure flow

All three fields are editable, plus three optional icon overrides.
The target entity can change because the unique_id is derived from
the config-entry id, not from the target. To reconfigure:

1. Settings → Devices & Services → Condition Gate.
2. ⋯ → **Reconfigure**.
3. Edit name, target entity, condition template, or icon overrides.
4. Save.

The entry is reloaded automatically after Reconfigure save.

### Icon overrides (optional)

The config flow exposes three optional icon fields:

| Field | Default | When shown |
|---|---|---|
| `icon_inactive` | inherits from target's current icon | wrapper is off (force-off) |
| `icon_active_on` | inherits from target's current icon | wrapper is on AND criterion is met |
| `icon_active_off` | `mdi:gate-alert` | wrapper is on BUT criterion is not met |

If the user does not override `inactive` and `active_on`, the wrapper
inherits the target's current `icon` attribute. This keeps the wrapper
visually grouped with the target in the UI. The `active_off` state
always uses a custom fallback so the "active but not met" state is
visually distinct from the target's plain-off icon.

## Editing from the entity

The switch entity has a `config_entry_id` set automatically, so the
"Settings" cog on the entity detail page links to the integration
page. From there, the user can reach Reconfigure via the `⋯` menu.
This matches the navigation pattern of built-in HA helpers, with one
extra click through the integration page.

## Unique ID

The unique ID is `entry.entry_id`. This is stable across
reconfigurations, including target-entity changes. Removing and
re-adding the integration creates a new unique ID.
