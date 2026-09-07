"""Tests for the fork-only insteon.update_property action."""

import json
from unittest.mock import AsyncMock, patch

from pyinsteon.config import RAMP_RATE_IN_SEC, TOGGLE_BUTTON
from pyinsteon.constants import ResponseStatus, ToggleMode
import pytest

from homeassistant.components import insteon
from homeassistant.components.insteon.const import (
    CONF_PROP_NAME,
    CONF_PROP_VALUE,
    CONF_TARGET_DEVICE,
    DOMAIN,
    SRV_UPDATE_PROPERTY,
)
from homeassistant.components.insteon.services import async_setup_services
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .mock_devices import MockDevices

from tests.common import MockConfigEntry, load_fixture

KPL = "33.33.33"


@pytest.fixture(name="kpl_properties_data", scope="module")
def kpl_properties_data_fixture():
    """Load the KeypadLinc properties fixture."""
    return json.loads(load_fixture("insteon/kpl_properties.json"))


async def _setup(hass: HomeAssistant, kpl_properties_data) -> tuple[MockDevices, str]:
    """Register the action and a device-registry entry for the mock KeypadLinc."""
    devices = MockDevices()
    await devices.async_load()
    devices.fill_properties(KPL, kpl_properties_data)
    devices[KPL].async_write_config = AsyncMock(return_value=ResponseStatus.SUCCESS)

    config_entry = MockConfigEntry(domain=DOMAIN)
    config_entry.add_to_hass(hass)
    ha_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, KPL)}
    )
    async_setup_services(hass)
    return devices, ha_device.id


async def _call(hass: HomeAssistant, device_id: str, name: str, value: str) -> None:
    await hass.services.async_call(
        DOMAIN,
        SRV_UPDATE_PROPERTY,
        {CONF_TARGET_DEVICE: device_id, CONF_PROP_NAME: name, CONF_PROP_VALUE: value},
        blocking=True,
    )


async def test_service_registered(hass: HomeAssistant) -> None:
    """The action is registered alongside the core ones."""
    async_setup_services(hass)
    assert hass.services.has_service(DOMAIN, SRV_UPDATE_PROPERTY)


async def test_bool_operating_flag(hass: HomeAssistant, kpl_properties_data) -> None:
    """A boolean operating flag such as led_off is parsed from text and written."""
    devices, device_id = await _setup(hass, kpl_properties_data)
    prop = devices[KPL].configuration["led_off"]
    assert prop.value is False

    with patch.object(insteon.services, "devices", devices):
        await _call(hass, device_id, "led_off", "true")

    assert prop.new_value is True
    devices[KPL].async_write_config.assert_awaited_once()
    devices.async_save.assert_awaited_once()


async def test_derived_property(hass: HomeAssistant, kpl_properties_data) -> None:
    """Derived settings that exist only in device.configuration can be set.

    This is the case the previous fork got wrong: ramp_rate_in_sec is not in
    operating_flags or properties, so it was silently dropped.
    """
    devices, device_id = await _setup(hass, kpl_properties_data)

    with patch.object(insteon.services, "devices", devices):
        await _call(hass, device_id, RAMP_RATE_IN_SEC, "4.5")

    assert devices[KPL].properties["ramp_rate"].new_value == 0x1A


async def test_mode_property(hass: HomeAssistant, kpl_properties_data) -> None:
    """Mode properties accept the mode name, case-insensitively."""
    devices, device_id = await _setup(hass, kpl_properties_data)
    prop = devices[KPL].configuration[f"{TOGGLE_BUTTON}_c"]
    assert prop.value == ToggleMode.TOGGLE

    with patch.object(insteon.services, "devices", devices):
        await _call(hass, device_id, f"{TOGGLE_BUTTON}_c", "on_only")

    assert prop.new_value == ToggleMode.ON_ONLY


@pytest.mark.parametrize(
    ("name", "value", "match"),
    [
        ("no_such_property", "1", "not found"),
        ("led_off", "maybe", "Invalid value"),
        (RAMP_RATE_IN_SEC, "fast", "Invalid value"),
        (f"{TOGGLE_BUTTON}_c", "sideways", "Invalid value"),
        ("radio_button_groups", "1,2", "Insteon panel"),
    ],
)
async def test_bad_input_raises(
    hass: HomeAssistant, kpl_properties_data, name: str, value: str, match: str
) -> None:
    """Unknown properties and unparsable values raise and write nothing."""
    devices, device_id = await _setup(hass, kpl_properties_data)

    with (
        patch.object(insteon.services, "devices", devices),
        pytest.raises(ServiceValidationError, match=match),
    ):
        await _call(hass, device_id, name, value)

    devices[KPL].async_write_config.assert_not_awaited()
    devices.async_save.assert_not_awaited()


async def test_unknown_device_raises(hass: HomeAssistant, kpl_properties_data) -> None:
    """A device id that is not in the registry is rejected."""
    devices, _ = await _setup(hass, kpl_properties_data)

    with (
        patch.object(insteon.services, "devices", devices),
        pytest.raises(ServiceValidationError, match="not found for device ID"),
    ):
        await _call(hass, "does-not-exist", "led_off", "true")


async def test_write_failure_raises(hass: HomeAssistant, kpl_properties_data) -> None:
    """A device that rejects the write surfaces an error and is not saved."""
    devices, device_id = await _setup(hass, kpl_properties_data)
    devices[KPL].async_write_config = AsyncMock(return_value=ResponseStatus.FAILURE)

    with (
        patch.object(insteon.services, "devices", devices),
        pytest.raises(ServiceValidationError, match="rejected the write"),
    ):
        await _call(hass, device_id, "led_off", "true")

    devices.async_save.assert_not_awaited()
