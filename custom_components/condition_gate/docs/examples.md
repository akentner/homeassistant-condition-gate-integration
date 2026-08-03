# Examples

Real-world setups that motivated this integration.

## Living-room candles

A nightly candle ritual: candles come on after dusk, off at 01:00. See
[`examples/candles.yaml`](../examples/candles.yaml) for the full
configuration.

| Field | Value |
|---|---|
| Target entity | `light.livingroom22_candles` |
| Condition template | `{{ state_attr('sun.sun', 'elevation') is not none and state_attr('sun.sun', 'elevation') < -3 and now().hour < 1 }}` |

### Behavior

| Time | Switch | Criterion | Target |
|---|---|---|---|
| 18:00 user toggles on | on | false (sun above -3°) | off |
| 21:35 sun crosses -3° | on | true | on |
| 01:00 cutoff | on | false (hour >= 1) | off |
| 21:35 next day | on | true | on |

The switch stays on until the user manually disarms.

### Card-mod tile color

```yaml
type: tile
entity: switch.condition_gate_wohnzimmer_kerzen
card_mod:
  style: |
    ha-card {
      {% if is_state('switch.condition_gate_wohnzimmer_kerzen', 'off') %}
        --shape-color: var(--secondary-text-color);
      {% elif state_attr('switch.condition_gate_wohnzimmer_kerzen', 'criteria_met') %}
        --shape-color: #ff8c1e;
      {% else %}
        --shape-color: #ffc850;
      {% endif %}
    }
```

## Presence-based hallway light

A hallway light that follows presence after sunset:

```jinja
{{ state_attr('sun.sun', 'elevation') is not none
   and state_attr('sun.sun', 'elevation') < 0
   and is_state('binary_sensor.hallway_motion', 'on') }}
```

This is a bit awkward because `binary_sensor.hallway_motion` is only
on for a moment. The criterion is only true briefly. A better
approach is to use a "presence held" helper, but for the example
this is illustrative.

## Threshold-based heater switch

A heater that follows a sensor reading:

```jinja
{{ states('sensor.bedroom_temperature') | float(0) < 18 }}
```

| Field | Value |
|---|---|
| Target entity | `switch.bedroom_heater` |
| Condition | as above |
| Scan interval | n/a (template auto-tracks state changes per minute) |

## Adding your own

If you want to add a new example, please:

1. Create a `.yaml` file under `examples/` describing the setup.
2. Reference it here with a brief description.
3. Keep the format consistent: a table of config fields, a behavior
   matrix, and any tile/dashboard snippets.

Examples are documentation first; they are not loaded by HA.
