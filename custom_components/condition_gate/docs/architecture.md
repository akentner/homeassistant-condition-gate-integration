# Architecture

How Condition Gate works internally.

## High-level

```
┌─────────────────────────────────────────────────────────────┐
│ CriteriaSwitchEntity                                        │
│                                                             │
│  is_on ──────── User active/inactive flag (RestoreEntity)   │
│                                                             │
│  async_added_to_hass():                                     │
│    1. Restore previous is_on                                │
│    2. Subscribe template for dependency tracking             │
│    3. Run initial reconcile                                 │
│                                                             │
│  async_turn_on() / async_turn_off():                        │
│    set is_on, immediately fire force-off + reconcile         │
│                                                             │
│  _async_reconcile():                                        │
│    if not is_on: target.turn_off() (force)                  │
│    else: render template; turn_on if truthy, else off        │
│                                                             │
│  Two trigger paths:                                         │
│    - Template subscription (state change, time tick)        │
│    - User toggle                                            │
│    - Service: condition_gate.re_evaluate                   │
└─────────────────────────────────────────────────────────────┘
```

## State vs. attributes

The switch's `state` is the user-controlled active/inactive flag (one
of `on` / `off`). It is the only field the user toggles through the UI.

Everything else lives in attributes:

| Attribute | Type | Notes |
|---|---|---|
| `criteria_met` | bool | Rendered-template result, truthy/falsy. |
| `target_entity` | str | The wrapped entity. |
| `target_state` | str | Current state of the wrapped entity. |
| `last_reconcile` | ISO datetime | When the criteria was last evaluated. |
| `last_action` | `"on"` / `"off"` / null | The action that fired on the last reconcile. |
| `error` | str / null | Last error message, if any. |

## Icon

The wrapper entity's icon is state-dependent, so the user can see at
a glance whether the gate is active, met, or not met:

| State | Icon | Default |
|---|---|---|
| Inactive (switch off, force-off) | `inactive` icon | inherits from target |
| Active, criterion met (target on) | `active_on` icon | inherits from target |
| Active, criterion not met (target off) | `active_off` icon | `mdi:gate-alert` |

The inheritance means that if the target is a `light.kitchen`, the
wrapper's icon matches the light's icon while the gate is active
and met. This keeps the wrapper visually grouped with the target in
the UI. The `active_off` state uses a custom fallback
(`mdi:gate-alert`) so that "active but criterion not met" is visually
distinct from the target's plain-off icon (which would look the same
as the inactive state).

All three icons are user-overridable through optional config fields.

## `this.state` two-phase render

The condition template can reference three things:

1. **HA state** — `is_state('light.x', 'on')`, `state_attr('sun.sun', 'elevation')`.
2. **Helpers** — `is_state('input_boolean.y', 'on')`.
3. **Self** — `this.state`, `this.entity_id`, `this.attributes`.

The `this` variable is not a built-in HA template variable. We inject it
during render. Internally the integration uses two render phases:

**Phase 1 — Subscription (dependency tracking)**

```python
self._tracker_info = async_track_template_result(
    self.hass,
    [TrackTemplate(self._template, {"this": self})],
    self._handle_template_update,
)
```

The `variables={"this": self}` makes `this` available during the
initial render so the dependency-tracking render does not warn that
`this` is undefined. The result is used to register every entity
referenced in the template. From then on, HA triggers the callback
whenever one of those entities changes.

**Phase 2 — Real evaluation (with `this`)**

```python
result = self._template.async_render(variables={"this": self})
```

Inside the template, `this` is the `CriteriaSwitchEntity` instance.
It exposes `state`, `entity_id`, and `attributes` as Jinja-accessible
attributes. The `this.state` value is the current `is_on` flag — i.e.
the user's active/inactive choice.

## Target type dispatch

The integration only accepts `light` and `switch` targets. When
`criteria_met` is true, `_async_turn_on` calls
`hass.services.async_call("homeassistant", "turn_on", ...)`. The
`homeassistant.turn_on` service dispatches to the right per-domain
service based on the target entity's domain:

* `light.<id>` → `light.turn_on`
* `switch.<id>` → `switch.turn_on`

The same dispatch happens for `homeassistant.turn_off` →
`light.turn_off` / `switch.turn_off`. This means the integration does
not need to know the target's domain at the call site — HA routes it.

This is also why the domain filter in the config flow is sufficient:
any entity that supports `homeassistant.turn_on` / `turn_off` works.
`light` and `switch` are the only standard domains in HA where this is
guaranteed, so the form selector filters to those and the config flow
rejects anything else with `unsupported_domain`. The same applies to
`input_boolean` (`input_boolean.turn_on` / `turn_off`) and a handful
of media-player variants, but those are not in the form selector and
would be rejected at flow time if submitted directly.

## Wrapper matches target domain

The wrapper entity itself uses the same domain as the target:

| Target | Wrapper |
|---|---|
| `light.livingroom22_candles` | `light.condition_gate_<name>` |
| `switch.some_switch` | `switch.condition_gate_<name>` |

This means the wrapper appears in the same domain as the target in
the UI, can be grouped with other lights or switches, and shows up in
the same dashboards. A user who looks for "candles" in the light
domain finds the wrapper next to the real light.

### How the dispatch works

`__init__.py` reads the target's domain at setup time and forwards
the entry to one of two platforms:

```python
PLATFORMS_BY_DOMAIN = {
    "light": ["light"],
    "switch": ["switch"],
}
```

Both `light.py` and `switch.py` are thin subclasses of `CriteriaBase`
(the shared logic). `CriteriaBase` does the heavy lifting:
`RestoreEntity` for state persistence, template subscription for
auto-reconciliation, service-call dispatch, and force-off. The
subclasses only add what makes them different:

```python
# switch.py
class CriteriaSwitchEntity(CriteriaBase, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

# light.py
class CriteriaLightEntity(CriteriaBase, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
```

The light entity is an on/off light: brightness, color, and
transition are not exposed. The criteria switch only drives on/off,
so the wrapper is a `ColorMode.ONOFF` light with no other controls.

### Reconfigure caveat

The platform is set at setup time and does not change on
reconfigure. If you change the target from a `light` to a `switch`
(or vice versa) via Reconfigure, the wrapper entity will still
appear in the original domain. To change the domain, remove the
entry and re-add it.

## Re-evaluation

Triggers that fire a reconcile:

* **Template subscription** (state change of any referenced entity, or
  per-minute time tick for `now()` / `utcnow()`).
* **User toggle** — `async_turn_on` and `async_turn_off` both trigger
  a reconcile, with `async_turn_off` also doing a force-off
  immediately.
* **Service** — `condition_gate.re_evaluate` runs reconcile on one or
  all switches. Useful for manual triggers from automations or scripts.

The `now()` / `utcnow()` per-minute tick is built into HA's
`async_track_template_result` and does not need any extra polling
code in the integration.

## RestoreEntity

`is_on` is persisted via `RestoreEntity`. On HA startup:

1. `async_added_to_hass` runs.
2. `await self.async_get_last_state()` returns the last `State` saved on
   shutdown, or `None` if this is the first install.
3. If non-`None`, `is_on` is restored.
4. `criteria_met`, `target_state`, `last_reconcile`, `last_action`,
   `error` are **not** persisted. They are re-derived on first
   reconcile.

Note: the condition-template result is re-evaluated on first
reconcile after start. If the user was previously active and the
condition is still met, the target entity is brought to the right
state.

## Concurrency

`asyncio.Lock` per instance. Reconcile is serialized; template updates
and the user toggle cannot interleave. Toggle from the UI awaits the
lock before returning, so the user sees the new state and the new
target state atomically.

## Lifecycle

```
config entry created
    -> CriteriaSwitchEntity instantiated
    -> async_added_to_hass
        -> restore is_on
        -> parse template
        -> subscribe to template changes
        -> first reconcile
    -> async_turn_on / async_turn_off (user interactions)
    -> config entry removed
        -> async_will_remove_from_hass
            -> unsubscribe template
            -> unregister from hass.data
```
