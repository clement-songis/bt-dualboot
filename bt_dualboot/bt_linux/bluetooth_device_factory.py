import re
from configparser import ConfigParser
from typing import Literal

from bt_dualboot.bluetooth_device import BluetoothDevice


def extract_macs(
    device_info_path: str,
) -> dict[Literal["device_mac", "adapter_mac"], str] | None:
    """Extracts adapter and device MAC from path to /info file

    Args:
        device_info_path (str): Kind of .../foo/A4:6B:6C:9D:E2:FB/B6:C2:D3:E5:F2:0D/info

    Returns:
        hash: Kind of { device_mac: <device MAC>, adapter_mac: <adapter MAC> }
    """

    match = re.search("([A-F0-9:]+)/([A-F0-9:]+)/info$", device_info_path)
    if match is None:
        return None

    adapter_mac, device_mac = match.groups()
    return {"device_mac": device_mac, "adapter_mac": adapter_mac}


def extract_info(device_info_path: str):
    """Extracts adapter info from Linux /path/to/info

    Args:
        device_info_path (str): Kind of .../foo/A4:6B:6C:9D:E2:FB/B6:C2:D3:E5:F2:0D/info

    Returns:
        hash: Kind of { name:, class:, pairing_key: }
    """
    config = ConfigParser()
    config.read(device_info_path)
    return {
        "name": config.get("General", "Name"),
        "class": config.get("General", "Class", fallback=None),
        "pairing_key": config.get("LinkKey", "Key", fallback=None),
    }


def bluetooth_device_factory(device_info_path: str):
    """Build BluetoothDevice instance for given /path/to/info

    Args:
        device_info_path (str): Kind of .../foo/A4:6B:6C:9D:E2:FB/B6:C2:D3:E5:F2:0D/info

    Returns:
        BluetoothDevice
    """

    macs = extract_macs(device_info_path)
    info = extract_info(device_info_path)

    if macs is None:
        return None

    if info["pairing_key"] is None:
        return None

    return BluetoothDevice(
        mac=macs["device_mac"],
        name=info["name"],
        pairing_key=info["pairing_key"],
        adapter_mac=macs["adapter_mac"],
        device_class=info["class"],
        source=BluetoothDevice.source_linux(),
    )
