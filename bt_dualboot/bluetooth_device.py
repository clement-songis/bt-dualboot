from typing import Literal


class BluetoothDevice:
    """Representation of bluetooth device

    Properties:
        mac (str)
        name (str)
        pairing_key (str)
        adapter_mac (str)
        device_class (str)
        source (str): kind of 'Windows', 'Linux'

    """

    def __init__(
        self,
        mac: str,
        pairing_key: str,
        adapter_mac: str,
        name: str | None = None,
        device_class: str | None = None,
        source: Literal["Windows", "Linux"] | None = None,
    ):
        self.source = source
        self.klass = device_class
        self.mac = mac
        self.name = name
        self.pairing_key = pairing_key
        self.adapter_mac = adapter_mac

    def __repr__(self):
        source = "?"
        if self.source is not None:
            source = self.source[0]
        return f"{self.__class__} {source} [{self.mac}] {self.name}"

    @classmethod
    def source_linux(cls):
        return "Linux"

    @classmethod
    def source_windows(cls):
        return "Windows"

    def is_source_linux(self):
        return self.source == "Linux"

    def is_source_windows(self):
        return self.source == "Windows"
