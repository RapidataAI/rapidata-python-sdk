# coding: utf-8

"""
    Rapidata.Dataset

    No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)

    The version of the OpenAPI document: v1
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


from __future__ import annotations
import pprint
import re  # noqa: F401
import json

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator
from typing import Any, ClassVar, Dict, List, Optional, Union
from typing import Optional, Set
from typing_extensions import Self

class BoxShape(BaseModel):
    """
    BoxShape
    """ # noqa: E501
    t: StrictStr = Field(description="Discriminator value for BoxShape", alias="_t")
    x_min: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, alias="xMin")
    y_min: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, alias="yMin")
    x_max: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, alias="xMax")
    y_max: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, alias="yMax")
    __properties: ClassVar[List[str]] = ["_t", "xMin", "yMin", "xMax", "yMax"]

    @field_validator('t')
    def t_validate_enum(cls, value):
        """Validates the enum"""
        if value not in set(['BoxShape']):
            raise ValueError("must be one of enum values ('BoxShape')")
        return value

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of BoxShape from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([
        ])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # set to None if x_min (nullable) is None
        # and model_fields_set contains the field
        if self.x_min is None and "x_min" in self.model_fields_set:
            _dict['xMin'] = None

        # set to None if y_min (nullable) is None
        # and model_fields_set contains the field
        if self.y_min is None and "y_min" in self.model_fields_set:
            _dict['yMin'] = None

        # set to None if x_max (nullable) is None
        # and model_fields_set contains the field
        if self.x_max is None and "x_max" in self.model_fields_set:
            _dict['xMax'] = None

        # set to None if y_max (nullable) is None
        # and model_fields_set contains the field
        if self.y_max is None and "y_max" in self.model_fields_set:
            _dict['yMax'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of BoxShape from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "_t": obj.get("_t") if obj.get("_t") is not None else 'BoxShape',
            "xMin": obj.get("xMin"),
            "yMin": obj.get("yMin"),
            "xMax": obj.get("xMax"),
            "yMax": obj.get("yMax")
        })
        return _obj


