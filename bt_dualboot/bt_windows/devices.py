import re

from bt_dualboot.bluetooth_device import BluetoothDevice
from bt_dualboot.windows_registry.windows_registry import WindowsRegistry

from .convert import hex_string_from_reg, is_mac_reg_key, mac_from_reg_key

REG_KEY__BLUETOOTH_PAIRING_KEYS = r"ControlSet001\Services\BTHPORT\Parameters\Keys"


def extract_adapter_mac(from_section_key: str):
    """Extracts adapter MAC from section key
    Args:
        from_section_key (str): kind of 'ControlSet001\\Services\\BTHPORT\\Parameters\\Keys\\d46d6d97629b'

    Returns:
        str: adapter MAC kind of 'D4:6D:6D:97:62:9B'
    """

    res = re.search("Services.BTHPORT.Parameters.Keys.([a-f0-9]+)$", from_section_key)
    if res is None:
        return None

    return mac_from_reg_key(res.groups()[0])


def get_devices(windows_registry: WindowsRegistry):
    """Returns all BluetoothDevice instances from windows registry
    Args:
        windows_registry (WindowsRegistry): instance used for export data

    Returns:
        list<BluetoothDevice>
            NOTE: filled only `mac`, `adapter_mac` and `pairing_key`
    """

    reg_data = windows_registry.export_as_config(REG_KEY__BLUETOOTH_PAIRING_KEYS)

    bluetooth_devices: list[BluetoothDevice] = []
    for section_key in reg_data.keys():
        adapter_mac = extract_adapter_mac(section_key)
        if adapter_mac is None:
            continue

        section = reg_data[section_key]
        for device_mac_raw, pairing_key_raw in section.items():
            if not is_mac_reg_key(device_mac_raw):
                continue

            bluetooth_devices.append(
                BluetoothDevice(
                    mac=mac_from_reg_key(device_mac_raw),
                    pairing_key=hex_string_from_reg(pairing_key_raw),
                    adapter_mac=adapter_mac,
                    source=BluetoothDevice.source_windows(),
                )
            )

    return bluetooth_devices
