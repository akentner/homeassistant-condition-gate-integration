# Condition Gate

A tiny Home Assistant integration that wraps a `light` or `switch`
entity in a user-facing entity of the same domain. When the wrapper
is active, a Jinja condition template decides whether the target is
turned on or off. When inactive, the target is forced off.

* The wrapper's state is the user-controlled **active / inactive**
  flag.
* The wrapper's domain matches the target: `light` target → `light`
  wrapper, `switch` target → `switch` wrapper.
* When active, the condition template decides whether the target is
  on or off.
* When inactive, the target is forced off.
* State persists across restarts.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋯ → **Custom repositories**.
2. Repository: `akentner/homeassistant-condition-gate-integration`.
3. Category: **Integration**.
4. Install **Condition Gate**.
5. Restart Home Assistant.
6. Settings → Devices & Services → **Add Integration** →
   **Condition Gate**.

### Manual

1. Copy `custom_components/condition_gate/` into your HA config
   directory under `custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** →
   **Condition Gate**.

## Configuration

The config flow has three required fields:

| Field | Description |
|---|---|
| Name | Display name shown in the UI. |
| Target entity | A `light.*` or `switch.*` entity the wrapper drives. |
| Condition template | Jinja expression that evaluates to truthy / falsy. |

Three optional icon fields override the wrapper's state-dependent
icon:

| Field | Default |
|---|---|
| `icon_inactive` | inherits from the target's icon |
| `icon_active_on` | inherits from the target's icon |
| `icon_active_off` | `mdi:gate-alert` |

Only `light` and `switch` targets are accepted. The wrapper entity
itself uses the same domain as the target, so a `light.x` target
produces a `light.<name>` wrapper.

See [`custom_components/condition_gate/docs/configuration.md`](custom_components/condition_gate/docs/configuration.md)
for the full configuration reference.

## Quick example

```yaml
# Settings → Devices & Services → Add Integration → Condition Gate
Name:           Candles
Target entity:  light.livingroom22_candles
Condition:      {{
    state_attr('sun.sun', 'elevation') is not none
    and state_attr('sun.sun', 'elevation') < -3
    and now().hour < 1
}}
```

## Documentation

* [Architecture](custom_components/condition_gate/docs/architecture.md) —
  internal design, lifecycle, `this` rendering, persistence.
* [Configuration](custom_components/condition_gate/docs/configuration.md) —
  config flow, validation, supported domains.
* [Condition templates](custom_components/condition_gate/docs/condition-template.md) —
  Jinja syntax, `this`, common patterns.
* [Examples](custom_components/condition_gate/docs/examples.md) —
  real-world setups.
* [Lovelace / card-mod examples](custom_components/condition_gate/examples/) —
  drop-in YAML for cards.

## Re-evaluation

Triggers that fire a reconcile:

* **Template subscription** — any state change referenced in the
  condition, plus a per-minute tick for `now()` / `utcnow()` (HA
  standard, no manual polling).
* **User toggle** — `turn_on` / `turn_off` trigger a reconcile.
* **Service** — `condition_gate.re_evaluate` runs reconcile on one
  or all wrappers. Useful from automations or scripts.

## Known limitations

* Only `light` and `switch` targets are supported. `scene`,
  `automation`, `input_boolean`, etc. are rejected at config-flow
  time.
* The wrapper domain is fixed at setup time and does not change on
  reconfigure. To change `light` ↔ `switch`, remove and re-add the
  entry.
* The default time tracking fires once per minute. For tighter
  reactivity (sub-minute polling), use a real `automation:` with a
  `time` trigger.

## License

MIT — see [`LICENSE`](LICENSE). Built for the
[Home Assistant](https://www.home-assistant.io/) community.