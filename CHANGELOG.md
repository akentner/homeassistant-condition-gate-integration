# Changelog

## 1.0.0 — HACS release

First public release through HACS. No code changes since `0.4.1` —
the version bump marks the move from local-only development to a
distributable repository. The repository layout now follows the
HACS convention: integration code under
`custom_components/condition_gate/`, HACS metadata at the project
root (`hacs.json`, `info.md`, top-level `README.md`, `LICENSE`,
`CODEOWNERS`, `icon.png`).

### What changed

- **Repository layout**: integration code moved into
  `custom_components/condition_gate/`. The full integration
  directory is what HACS installs into the user's HA config.
- **HACS metadata**: `hacs.json`, `info.md`, top-level `README.md`,
  `LICENSE` (MIT + Home Assistant Community addendum), `CODEOWNERS`,
  `icon.png` (512×512), GitHub issue templates and a `hacs-action`
  workflow are now at the project root.
- **Manifest**: `codeowners` populated (`@akentner`),
  `issue_tracker` populated, `documentation` populated, version
  bumped to `1.0.0`.

### Migrating from 0.4.x

No code changes — config entries from `0.4.x` keep working
unchanged. The change is purely in the distribution channel:

- **Manual users** can keep using the integration as before. The
  files just live one directory deeper than they used to.
- **HACS users** can install from the new repository and add the
  integration through Settings → Devices & Services as usual. If
  you installed manually before and want to switch to HACS, delete
  the manual copy from `custom_components/`, install via HACS, and
  restart Home Assistant. Existing config entries survive.

## 0.4.1 — Configurable icons

The wrapper entity's icon now adapts to its state and criterion
result. Three icons are configurable in the config flow, with sensible
defaults that inherit from the target entity.

### What changed

- **Dynamic icon**: the wrapper entity now has a state-dependent
  icon. Three states are distinguished:
  - `inactive` — switch is off (force-off), the target's icon is
    shown by default
  - `active_on` — switch is on AND criterion is met, the target's
    icon is shown by default
  - `active_off` — switch is on BUT criterion is not met, the
    fallback `mdi:gate-alert` is shown by default (the target's
    plain-off icon would look the same as the inactive state)
- **Optional icon fields**: three new optional fields in the config
  flow (`icon_inactive`, `icon_active_on`, `icon_active_off`) let
  the user override the defaults with any MDI icon.
- **Smart default**: when the user does not override, the wrapper
  inherits the target entity's current `icon` attribute. If the
  target has no `icon` attribute, MDI fallback icons are used.

### Migration

`0.4.0` config entries keep working — the new icon fields are
optional. After updating to `0.4.1`, the existing icon (set on
`CriteriaBase` by HA's default `SwitchEntity.icon` for `switch.*`
wrappers) is replaced by the dynamic logic on the next reload.

## 0.4.0 — Rename

The integration is renamed from `criteria_switch` to
`condition_gate`. The new name describes what the integration does
— a gate that opens or closes based on a Jinja condition — rather
than the input concept (criteria) it uses to do so.

### What changed

- Python module: `custom_components/criteria_switch/` →
  `custom_components/condition_gate/`
- Manifest domain: `criteria_switch` → `condition_gate`
- Display name: "Criteria Switch" → "Condition Gate"
- Service: `criteria_switch.re_evaluate` → `condition_gate.re_evaluate`
- Docs: `docs/criteria-template.md` → `docs/condition-template.md`

### Migrating from 0.3.x

This is a breaking change. Existing entries from `0.3.x` cannot be
auto-migrated because the integration directory and the manifest
domain both change. The user has to:

1. Note the current configuration of each existing entry (name,
   target entity, condition).
2. Delete the entries in Settings → Devices & Services.
3. Add the integration fresh through the config flow. The form
   looks identical except the title is now "Condition Gate".
4. Re-enter the configuration.

The entity_id of the wrapper is derived from the title, so
restoring the same title gives back the same entity_id. Card-mod
and dashboard references continue to work.

## 0.3.0 — Domain-matched wrapper entity

The wrapper entity now matches the target's domain. A `light` target
gets a `light.<name>` wrapper; a `switch` target gets a `switch.<name>`
wrapper. The integration forwards the entry to the right platform
based on the target's domain.

### What changed

- **New platform dispatch**: `light.py` and `switch.py` now both
  exist. The `__init__.py` reads the target's domain from
  `entry.data[CONF_TARGET_ENTITY]` and forwards the entry to the
  matching platform.
- **Shared logic**: a new `base.py` holds `CriteriaBase` (the
  RestoreEntity + template subscription + reconcile + service
  dispatch). `CriteriaLightEntity` and `CriteriaSwitchEntity` are
  thin subclasses that pick the right entity class.
- **Light entity attributes**: `CriteriaLightEntity` declares itself
  as an on/off light with `color_mode = ONOFF` and
  `supported_color_modes = {ONOFF}`. No brightness, no color, no
  transition — the integration drives on/off only.
- **No more `switch` fallback**: if the target's domain is neither
  `light` nor `switch`, the config flow already rejects it; the
  platform dispatch in `__init__.py` is therefore `light` or
  `switch` only.

### Migrating from 0.2.x

Existing `0.2.x` entries that targeted a `light` entity are still
registered as `switch` wrapper entities. The migration is manual:

1. Delete the existing entry in Settings → Devices & Services.
2. Re-add through the config flow. The wrapper will be created in
   the matching domain this time.

The `unique_id` is derived from the config entry id, so the
integration does not auto-collide on re-add. The previous entity
will appear as `unavailable` until the entry is removed.

### Reconfigure caveat

The platform is set at setup time and does not change on
reconfigure. If you change the target from a `light` to a `switch`
(or vice versa) via Reconfigure, the wrapper entity will still
appear in the original domain. Remove and re-add to change the
domain.

## 0.2.0 — Breaking change

The integration was simplified around the natural `light` / `switch`
target model. Previous versions exposed `on_action` / `off_action` /
`scan_interval` configuration fields; these are gone.

### What changed

- **New condition field**: a single Jinja2 template replaces
  `on_action` + `off_action` + `scan_interval`. The template
  returns truthy/falsy; truthy drives `homeassistant.turn_on` on
  the target, falsy drives `homeassistant.turn_off`.
- **Domain restriction**: only `light` and `switch` targets are
  supported. The form selector filters to those domains; the
  config flow rejects others with `unsupported_domain`.
- **No scan_interval**: condition re-evaluation uses HA's standard
  `async_track_template_result`, which auto-tracks `now()` per
  minute plus entity state changes. No manual polling.
- **Reconfigure allows target changes**: the unique_id is derived
  from the config entry id, not from the target. Reconfigure lets
  the user change name, target entity, and condition.
- **Removed**: the per-instance `options` flow. There is nothing
  to edit after the initial setup beyond the main configuration.

### Migrating from 0.1.x

Config entries from `0.1.x` are not auto-migrated. To upgrade:

1. Delete the existing entry in Settings → Devices & Services.
2. Re-add through the config flow. Pick the same target entity
   (or a new one) and a condition template that captures the
   semantics of the old `on_action` and `off_action`.

For example, an `0.1.x` entry with:

```yaml
on_action:  {service: scene.turn_on, data: {entity_id: scene.candles_on}}
off_action: {service: scene.turn_on, data: {entity_id: scene.candles_off}}
```

…becomes a `0.2.x` entry with:

```yaml
target_entity: light.livingroom22_candles
condition: |
  {{
    state_attr('sun.sun', 'elevation') is not none
    and state_attr('sun.sun', 'elevation') < -3
    and now().hour < 1
  }}
```

`homeassistant.turn_on` and `homeassistant.turn_off` dispatch to the
correct per-domain service based on the target's domain, so scenes
that controlled multiple lights must be replaced by a single target
plus a scene-as-side-effect, or a script that the condition invokes
through `homeassistant.turn_on` of an `input_boolean` or
`automation.trigger` service.
