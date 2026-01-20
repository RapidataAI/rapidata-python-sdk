from enum import Enum


class DeviceType(Enum):
    """DeviceType Enum

    Represents the device type of a user. Used to filter who to target based on device types.

    Attributes:
        UNKNOWN (DeviceType): Unknown device type.
        PHONE (DeviceType): Phone device.
        TABLET (DeviceType): Tablet device.
    """

    UNKNOWN = "Unknown"
    PHONE = "Phone"
    TABLET = "Tablet"

    def _to_backend_model(self) -> str:
        return self.value
