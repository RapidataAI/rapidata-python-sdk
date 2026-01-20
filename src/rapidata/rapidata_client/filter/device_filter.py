from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.rapidata_client.filter.models.device_type import DeviceType
from pydantic import BaseModel, ConfigDict


class DeviceFilter(RapidataFilter, BaseModel):
    """DeviceFilter Class

    Can be used to filter who to target based on their device type.

    Args:
        device_types (list[DeviceType]): List of device types to filter by.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    device_types: list[DeviceType]

    def __init__(self, device_types: list[DeviceType]):
        super().__init__(device_types=device_types)

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_device_user_filter_model import (
            IUserFilterModelDeviceUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelDeviceUserFilterModel(
                _t="DeviceFilter",
                deviceTypes=[dt._to_backend_model() for dt in self.device_types],
            )
        )

    def _to_audience_model(self):
        raise NotImplementedError("DeviceFilter is not supported for audiences")
