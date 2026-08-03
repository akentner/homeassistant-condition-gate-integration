# Condition Gate

A tiny Home Assistant integration that wraps a `light` or `switch`
entity in a user-facing entity of the same domain. When the wrapper
is active, a Jinja condition template is evaluated against live HA
state and the special `this` variable that references the wrapper
itself. If the condition is truthy, the target entity is turned on;
otherwise it is turned off. When inactive, the target is forced off.

* The wrapper's own state is the user-controlled **active / inactive**
  flag.
* The wrapper's domain matches the target: `light` target → `light`
  wrapper, `switch` target → `switch` wrapper.
* When active, the condition template decides whether the target is
  on or off.
* When inactive, the target is forced off.
* The state persists across restarts via `RestoreEntity`.

## When to use it

Use Condition Gate when you want a single toggleable surface that
controls a light or switch with a declarative rule, without writing an
automation. Common patterns:

* Candles that come on after dusk and off at 01:00.
* A light that follows presence + a time window.
* A switch that depends on a sensor threshold.

## When not to use it

* You need a true automation with multiple triggers or complex
  branching. Use `automation:` for that.
* The target is not a `light` or `switch` (for example `scene`,
  `automation`, `input_boolean`).
* You need a high-frequency re-evaluation. The default time tracking
  fires once per minute; for tighter reactivity, use a proper
  automation with a `time` trigger.

## How it works

```
Wrapper-Entity (is_on = active/inactive, same domain as target)
        │
        ▼ when active
   Condition-Template (Jinja) ── true ──▶ homeassistant.turn_on(target)
        │                          │
        │                          └─false──▶ homeassistant.turn_off(target)
        │
        ▼ when inactive
   homeassistant.turn_off(target) (force)
```

Triggers:
* **Template subscription** (`async_track_template_result`): any state
  change referenced by the condition template, plus per-minute time
  updates for `now()` / `utcnow()` (HA standard, no manual polling).
* **User toggle**: `turn_on` / `turn_off` triggers a reconcile.
* **Service**: `condition_gate.re_evaluate` re-runs the reconcile.

## Quick reference

```yaml
# Settings → Devices & Services → Add Integration → Condition Gate
Name:           My Switch
Target entity:  light.livingroom22_candles
Condition:      {{
    state_attr('sun.sun', 'elevation') is not none
    and state_attr('sun.sun', 'elevation') < -3
    and now().hour < 1
}}
```

## Documentation

* [Architecture](architecture.md) — internal design, lifecycle, `this`
  rendering, persistence.
* [Configuration](configuration.md) — config flow, validation, supported
  domains.
* [Condition templates](condition-template.md) — Jinja syntax, `this`,
  common patterns.
* [Examples](examples.md) — real-world setups.

## Versioning

See the project-root `CHANGELOG.md` for version history and
migration steps between major releases.
