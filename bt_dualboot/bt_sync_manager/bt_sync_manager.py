import sys
from contextlib import contextmanager
from dataclasses import dataclass

from bt_dualboot.bluetooth_device import BluetoothDevice
from bt_dualboot.bt_linux.devices import get_devices as get_linux_devices
from bt_dualboot.bt_windows.convert import hex_string_to_reg_value, mac_to_reg_key
from bt_dualboot.bt_windows.devices import get_devices as get_windows_devices
from bt_dualboot.windows_registry.windows_registry import WindowsRegistry


@dataclass
class _DevicesPair:
    linux: BluetoothDevice | None = None
    windows: BluetoothDevice | None = None


class DeviceNotFoundError(Exception):
    pass


class BtSyncManager:
    """Provides service for syncing of bluetooth pairing keys between Linux and Windows

    Terms:
        push: write pairing keys from Linux to Windows
        pull: write pairing keys from Windows to Linx (not implemented, out of scope of this tool)
    """

    def __init__(self, windows_registry: WindowsRegistry):
        self.windows_registry = windows_registry
        self.index_cache = None

    def flush_cache(self):
        self.index_cache = None

    @contextmanager
    def no_cache(self):
        """
        Usage:
            with sync_manager.no_cache():
                pass
        """
        self.flush_cache()
        yield
        self.flush_cache()

    def __index_devices(self):
        """
        Indexes and chache BluetoothDevice lists both from Linux and Windows

        !cached

        NOTE: this index used to match Windows and Linux devices prior copy&update data

        Returns:
            dict<MAC:list<BluetoothDevice>>:
                key: device MAC
                value: (linux_device, windows_device) pair of BluetoothDevice instances
        """
        if self.index_cache is not None:
            return self.index_cache

        index: dict[str, _DevicesPair] = {}

        linux_devices = get_linux_devices()
        windows_devices = get_windows_devices(self.windows_registry)

        for device in linux_devices:
            if device.mac not in index:
                index[device.mac] = _DevicesPair(linux=device)
            else:
                print(
                    f"WARNING: Device {device.mac} paired on Linux for multiple BT-adapters",
                    file=sys.stderr,
                )

        for device in windows_devices:
            if device.mac not in index:
                index[device.mac] = _DevicesPair(windows=device)
            elif index[device.mac].windows is None:
                index[device.mac].windows = device
            else:
                print(
                    f"WARNING: Device {device.mac} paired on Windows for multiple BT-adapters",
                    file=sys.stderr,
                )

        self.index_cache = index
        return self.index_cache

    def __get_reg_adapter_section_key(self, device: BluetoothDevice):
        return (
            r"ControlSet001\Services\BTHPORT\Parameters\Keys"
            + "\\"
            + mac_to_reg_key(device.adapter_mac)
        )

    def devices_both_synced(self):
        """
        !uses cached

        Returns:
            list<BluetoothDevice>: which have the same pairing_key for Linux and Windows
        """

        index = self.__index_devices()

        synced_devices = [
            devices.linux
            for devices in index.values()
            if devices.linux is not None
            and devices.windows is not None
            and devices.linux.pairing_key == devices.windows.pairing_key
        ]

        return synced_devices

    def devices_needs_sync(self):
        """
        !uses cached

        Returns:
            list<BluetoothDevice>: which exist both in Linux and Windows, but have different pairing keys
        """
        index = self.__index_devices()

        needs_sync_devices = [
            devices.linux
            for devices in index.values()
            if devices.linux is not None
            and devices.windows is not None
            and devices.linux.pairing_key != devices.windows.pairing_key
        ]

        return needs_sync_devices

    def devices_absent_windows(self):
        """
        !uses cached

        Returns:
            list<BluetoothDevice>: which exist both in Linux and Windows, but have different pairing keys
        """

        index = self.__index_devices()

        single_linux_devices = [
            devices.linux
            for devices in index.values()
            if devices.linux is not None and devices.windows is None
        ]

        return single_linux_devices

    def __param_get_macs_list(
        self,
        device_or_mac_or_list: (
            str | BluetoothDevice | list[str] | list[BluetoothDevice]
        ),
    ):
        """Align plural argument to list of devices MACs

        Args:
            device_or_mac_or_list (str|BluetoothDevice|list<str>|list<BluetoothDevice>)

        Returns:
            list<str>: list of devices MACs like ["B6:C2:D3:E5:F2:0D", ...]
        """
        # handling: type|list<type> pluralism
        target_items_dirty = device_or_mac_or_list
        if not isinstance(target_items_dirty, list):
            target_items_dirty = [target_items_dirty]

        # handling: list<str>|list<BluetoothDevice> pluralism
        target_items_macs: list[str] = []
        for item in target_items_dirty:
            if isinstance(item, BluetoothDevice):
                target_items_macs.append(item.mac)
            else:
                target_items_macs.append(item)

        return target_items_macs

    def __update_windows_registry(self, devices: list[BluetoothDevice]):
        """Performs Windows registry import for given devices

        !updates Windows Hive file

        Args:
            devices (list<BluetoothDevice>): list of BluetoothDevice for import
        """
        for_import: dict[str, dict[str, str]] = {}
        for device in devices:
            section_key = self.__get_reg_adapter_section_key(device)
            device_key = f'"{mac_to_reg_key(device.mac)}"'
            pairing_key = hex_string_to_reg_value(device.pairing_key)
            for_import[section_key] = {device_key: pairing_key}

        self.windows_registry.import_dict(for_import)

    def push(
        self,
        device_or_mac_or_list: (
            str | BluetoothDevice | list[str] | list[BluetoothDevice]
        ),
        dry_run: bool = False,
    ):
        """Copy pairing keys from Linux to Windows, import updates into Windows registry

        !updates Windows Hive file

        Args:
            device_or_mac_or_list (str|BluetoothDevice|list<str>|list<BluetoothDevice>)

        Raises:
            DeviceNotFoundError
        """
        target_items_macs = self.__param_get_macs_list(device_or_mac_or_list)

        with self.no_cache():
            index = self.__index_devices()

            needs_sync_macs = [device.mac for device in self.devices_needs_sync()]
            absent_in_needs_sync = set(target_items_macs) - set(needs_sync_macs)
            if len(absent_in_needs_sync) > 0:
                macs_msg = ", ".join(list(absent_in_needs_sync))
                raise DeviceNotFoundError(
                    f"Can't push {macs_msg}! Not found or already in sync!"
                )

            devices_for_update: list[BluetoothDevice] = []
            for device_mac in target_items_macs:
                if device_mac not in index.keys():
                    raise DeviceNotFoundError(f"Can't push {device_mac}! Not found!")

                devices = index[device_mac]
                if devices.linux is None:
                    raise DeviceNotFoundError(
                        f"Can't push {device_mac}! Not found on Linux!"
                    )

                if devices.windows is None:
                    raise DeviceNotFoundError(
                        f"Can't push {device_mac}! Not found on Windows!"
                    )

                devices.windows.pairing_key = devices.linux.pairing_key
                devices_for_update.append(devices.windows)

            if dry_run is not True:
                self.__update_windows_registry(devices_for_update)
            else:
                print(
                    f"> DRY RUN: push devices {', '.join([device.mac for device in devices_for_update])}"
                )
