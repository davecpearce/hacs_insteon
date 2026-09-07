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
core `2026.8.3`.

| Area | Change | Status |
|---|---|---|
| `services.py`, `schemas.py`, `const.py`, `services.yaml` | `update_property` service | **Feature** |
| `api/properties.py` | Panel always shows advanced properties (ignores the `show_advanced` toggle) | Feature |
| `api/properties.py` | Websocket property update looks up `operating_flags` / `properties` directly instead of `device.configuration`, logs a missing property instead of raising | **Drift, and a bug**: see Known issues |
| `light.py` | Debug logging of brightness in `brightness` and `async_turn_on` | Harmless |
| `__init__.py` | Leftover YAML-import options migration (`SOURCE_IMPORT`) | Dead code; never triggers |
| `entity.py`, `utils.py`, `api/aldb.py`, `api/config.py`, `services.py` | Uses `via_device=` and `async_get_device(identifiers=)` instead of core's `via_device_id=` / `async_get_device_by_identifier(..., config_entry_id)` | Drift; `via_device` is deprecated in 2026.8 and removed in 2027.8. To be re-aligned in v1.1 |
| `manifest.json` | Adds `version` (required for custom components), drops `@connorgallopo` from codeowners | Packaging |

`api/scenes.py` is byte-identical to core and is **not** a fork addition.

## Known issues in v1.0

v1.0 is deliberately behaviour-identical to the fork it came from, so these ship as-is and
are fixed in v1.1. Found by running core's own `tests/components/insteon/` suite against
the fork (see Development).

- **Panel property editor drops derived properties.** `pyinsteon` exposes some settings
  only through `device.configuration` (`radio_button_groups`, `momentary_delay`,
  `relay_mode`, per-button toggle modes, ramp rate in seconds). The fork's websocket
  handler and the `update_property` service look only in `operating_flags` and
  `properties`, so saving one of these from the Insteon panel logs
  `Property <name> could not be found` and changes nothing. Raw operating flags such as
  `led_off` and raw extended properties such as `led_dimming` and `on_level` still work,
  which is why the LED automation is unaffected.
- **`via_device` deprecation warning** at startup on 2026.8+. Harmless until 2027.8.
- **Does not load on HA 2026.9** (`voluptuous_serialize` removed from core).

## Compatibility

| Release | Home Assistant | Notes |
|---|---|---|
| v1.0.x | 2026.8.x only | Behaviour-identical to the pre-HACS fork. **Does not load on 2026.9** (`voluptuous_serialize` was removed from core). |
| v1.1.x | 2026.8.x and 2026.9+ | Planned: `probatio` shim for the serializer, merge upstream `api/device.py` fields, re-align the drift above. |

Pinned requirements match core exactly: `pyinsteon==1.6.4`,
`insteon-frontend-home-assistant==0.6.2`.

## Installation

1. HACS → Integrations → ⋮ → **Custom repositories** → add this repo, category *Integration*.
2. Install **Insteon (extended)**, restart Home Assistant.
3. Your existing Insteon config entry is picked up as-is; nothing to reconfigure.

To go back to core, uninstall in HACS and restart. The config entry survives.

## Development

The fork carries no tests of its own yet. Core's suite in `tests/components/insteon/`
mocks `pyinsteon` and runs without a PLM, so it is the strongest check available:

```bash
scripts/run-upstream-tests.sh 2026.8.3
```

This clones core at that tag, builds a venv, runs the suite on stock core for a baseline,
then again with this `custom_components/insteon` swapped in. Baseline at core 2026.8.3:

| | passed | failed | errors |
|---|---|---|---|
| stock core | 79 | 0 | 7 (environmental: translation checks, config-flow teardown) |
| this fork | 70 | 9 | 8 (the same 7, plus one lingering-task teardown) |

Of the 9 fork failures, 3 are the deliberate "always show advanced" change, 1 is the
`async_device_name` signature (2 args vs core's 3), and 5 are the property-editor bug
listed under Known issues.
