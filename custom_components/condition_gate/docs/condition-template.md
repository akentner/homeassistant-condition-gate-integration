# Condition templates

The condition template is a Jinja2 expression that returns truthy or
falsy. Condition Gate renders it against live HA state plus the
special `this` variable that references the switch itself.

## Standard Jinja

Most HA Jinja conventions apply. The most useful building blocks:

| Pattern | What it does |
|---|---|
| `is_state('light.x', 'on')` | `True` if the entity's state equals the given string. |
| `state_attr('sensor.x', 'y')` | The named attribute, or `None`. |
| `states('sensor.x')` | The state as a string. |
| `now().hour` | Current hour (0–23). |
| `now().weekday()` | Day of week (0 = Monday). |
| `as_timestamp(states('sensor.x'))` | Parse a string into a Unix timestamp. |
| `is_state_attr('light.x', 'brightness', 255)` | `True` if state + attribute match. |

Full reference: [HA template docs](https://www.home-assistant.io/docs/configuration/templating/).

## `this`

The `this` variable is provided by Condition Gate. It is the switch's
own entity instance. Useful attributes:

| `this.X` | Resolves to |
|---|---|
| `this.state` | The switch's own state (`"on"` / `"off"`). Use this to gate the condition on the user's active flag. |
| `this.entity_id` | The switch's `entity_id`. |
| `this.attributes.X` | Any attribute of the switch. |

The most common pattern:

```jinja
{{ this.state == 'on' and <other condition> }}
```

The integration injects `this` only during the evaluation phase. The
template-subscription phase uses `variables={"this": self}` so it can
register all referenced entities without polluting dependencies with
`this`.

## Common patterns

### Sun-elevation gate

Activate only after dusk (sun below -3°):

```jinja
{{ state_attr('sun.sun', 'elevation') is not none
   and state_attr('sun.sun', 'elevation') < -3 }}
```

`is none` guard covers the brief window during HA startup where
`sun.sun` may not be loaded yet.

### Time window

Activate only between 22:00 and 06:00:

```jinja
{{ now().hour >= 22 or now().hour < 6 }}
```

### Cutoff at 01:00

Activate when sun is below -3° **and** before 01:00. After 01:00 the
criterion goes false and the target is turned off automatically,
while the switch remains on (the user has not manually disarmed).

```jinja
{{ state_attr('sun.sun', 'elevation') is not none
   and state_attr('sun.sun', 'elevation') < -3
   and now().hour < 1 }}
```

### Combined presence + time

Activate when someone is home and it's late:

```jinja
{{ is_state('person.alex', 'home')
   and now().hour >= 22 }}
```

### Sensor-based

Activate when a sensor value crosses a threshold:

```jinja
{{ states('sensor.temperature') | float(0) < 18 }}
```

`| float(0)` converts the state string to a number with a fallback.
Without it, comparing a string state to a number raises a TypeError.

### Switch state gate

Activate only when this switch is on (rare, since the integration
already force-disables the target when off, but useful for chaining):

```jinja
{{ this.state == 'on' and is_state('binary_sensor.door', 'off') }}
```

## Common mistakes

| Mistake | Fix |
|---|---|
| `now().hour` doesn't trigger on its own | HA's `async_track_template_result` fires per minute for `now()` / `utcnow()` automatically. The default time tracking is enough. |
| `state_attr('sun.sun', 'elevation')` raises when sun is missing | Wrap with `is not none` or `| float(0)`. |
| Comparing a string to a number | Cast with `\| float(N)` or `\| int(N)`. |
| `states('sensor.x') == 'on'` returns False for numerical sensors | Use `is_state` only for state-string entities. |
| `this.state` is not recognised | The switch's entity must be set up before the template is rendered. If you see errors, check the integration was added successfully. |

## Testing a template

Before committing to a config, test a template directly via the
Developer Tools → Template editor. The template editor does not bind
`this`, so substitute it with the entity id of your switch:

```jinja
{{ is_state('switch.condition_gate_my_switch', 'on')
   and state_attr('sun.sun', 'elevation') < -3
   and now().hour < 1 }}
```

If this returns true in the template editor, the in-config version
(`this.state == 'on' ...`) will behave identically once the switch
is set up.
