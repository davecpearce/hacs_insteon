# Insteon (extended)

A [HACS](https://hacs.xyz) custom integration that **replaces the Home Assistant core
`insteon` integration** with a lightly extended fork. It keeps `domain: insteon`, so it
shadows core and everything (entities, events, the Insteon panel, existing automations)
keeps working unchanged.

This is a derivative of the Home Assistant core integration written and maintained by
[@teharris1](https://github.com/teharris1) and [@ssyrell](https://github.com/ssyrell),
licensed under Apache 2.0 (see `LICENSE.md`). All credit for the integration itself goes
to them and the Home Assistant project; this repo only adds a small service on top.

## What it adds

### `insteon.update_property` service

Write a device configuration property (operating flag or extended property) to an Insteon
device from an automation or script, then persist it. Core only exposes this through the
Insteon panel UI.

| Field | Type | Notes |
|---|---|---|
| `target_device` | device id | An Insteon device from the device registry |
| `prop_name` | string | e.g. `led_off`, `led_dimming`, `on_level`, `ramp_rate`, `toggle_mode` |
| `prop_value` | string | Parsed as `bool` (`"true"`/`"false"`) or `int` depending on the property's type |

Example: dim the keypad LEDs on every device labelled `Insteon LED Control`:

```yaml
action: insteon.update_property
data:
  target_device: "{{ device_id }}"
  prop_name: led_off
  prop_value: "true"
```

Raises `ServiceValidationError` if the device, address, or property is not found, or if
the device rejects the write.

## Other differences from core

Documented here so they are deliberate rather than accidental. Measured against
core `2026.9.1`, which v1.1 is based on.

| Area | Change | Why |
|---|---|---|
| `services.py`, `schemas.py`, `const.py`, `services.yaml`, `strings.json` | `update_property` action | Feature |
| `compat.py`, `api/config.py`, `api/properties.py` | Schema serialisation goes through a shim that imports `probatio` (HA 2026.9+) and falls back to `voluptuous_serialize` (HA 2026.8) | One build runs on both HA versions |
| `api/properties.py` | Panel always shows advanced properties (ignores the `show_advanced` toggle) | Feature |
| `light.py` | Debug logging of brightness in `brightness` and `async_turn_on` | Harmless diagnostics |
| `manifest.json` | Adds `version` and `issue_tracker`, points `documentation` at this repo | Required for custom components |
| `brand/` | Insteon icon, the same asset core uses | Required by HACS |

Everything else is byte-identical to core 2026.9.1.

## Changes in v1.1

- **Loads on Home Assistant 2026.9.** Core removed `voluptuous_serialize` in 2026.9;
  the shim above picks whichever serialiser the running core ships.
- **Merged upstream 2026.9.** The panel's device view now receives category, model,
  firmware and button data, as the pinned frontend expects.
- **Fixed: the property editor dropped derived settings.** v1.0's panel handler and
  `update_property` action only looked in `operating_flags` and `properties`, so
  `radio_button_groups`, `momentary_delay`, `relay_mode`, per-button toggle modes and
  ramp rate in seconds logged "could not be found" and changed nothing. Both now use
  `device.configuration`, the union pyinsteon maintains.
- **`update_property` parses values by the property's type**: booleans accept
  true/false/on/off/yes/no/1/0, integers and floats are parsed, and mode properties
  accept their mode name. Bad input raises a validation error before anything is
  written, and a rejected write no longer saves the device store.
- **Dropped drift from the old fork**: the deprecated `via_device` argument (removal
  scheduled for HA 2027.8), the pre-2026 device-registry lookups, and dead YAML-import
  code in `__init__.py`.
- **Tests** for the action live in `tests/` and run under core's own harness.

## Compatibility

| Release | Home Assistant | Notes |
|---|---|---|
| v1.1.x | 2026.8.x and 2026.9.x | Based on core 2026.9.1. Verified against core's own Insteon test suite at both 2026.8.3 and 2026.9.1. |
| v1.0.x | 2026.8.x only | Behaviour-identical to the pre-HACS fork. Does not load on 2026.9. |

Pinned requirements match core exactly: `pyinsteon==1.6.4`,
`insteon-frontend-home-assistant==0.6.2`. `probatio` is not declared as a requirement
on purpose: core pins it, and pinning it here would fight core's pin on future releases.

## Installation

The repository URL to add in HACS is:

```
https://github.com/davecpearce/hacs_insteon
```

1. In Home Assistant open **HACS**, click the **⋮** menu in the top right, choose
   **Custom repositories**.
2. Paste the URL above, set **Type** to *Integration*, click **Add**.
3. Search HACS for **Insteon**, open it, click **Download**, pick the latest release.
4. If you previously ran this integration from a hand-copied `custom_components/insteon`,
   HACS overwrites that same directory. Nothing else to move.
5. Restart Home Assistant.

Your existing Insteon config entry, devices, entity IDs, and any renames are picked up
as-is: Home Assistant identifies the integration by its domain (`insteon`) and each entity
by its unique ID, and neither changes. HACS's display name in `hacs.json` is never read by
Home Assistant.

**Before the first install on a production system:** take a full Home Assistant backup,
and keep a copy of the current `custom_components/insteon` directory so you can drop it
back in if needed.

To go back to core, remove the integration in HACS and restart. The config entry survives.

## Development

Core's suite in `tests/components/insteon/` mocks `pyinsteon` and runs without a PLM,
so it is the strongest check available. This repo's own tests in `tests/` are copied
alongside it.

```bash
scripts/run-upstream-tests.sh 2026.9.1
scripts/run-upstream-tests.sh 2026.8.3
```

Each run clones core at that tag, builds a venv, generates translations, runs the
suite on stock core for a baseline, then again with this `custom_components/insteon`
swapped in. Expected result for v1.1: everything stock passes also passes here, except
the three tests that assert the stock "hide advanced properties" behaviour, which this
fork overrides on purpose. See the release notes for the exact numbers per tag.
