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

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator
from typing import Any, ClassVar, Dict, List, Optional
from rapidata.api_client.models.compare_workflow_config_rapid_selection_configs_inner import CompareWorkflowConfigRapidSelectionConfigsInner
from rapidata.api_client.models.compare_workflow_config_referee import CompareWorkflowConfigReferee
from rapidata.api_client.models.feature_flag import FeatureFlag
from rapidata.api_client.models.simple_workflow_config_blueprint import SimpleWorkflowConfigBlueprint
from typing import Optional, Set
from typing_extensions import Self

class SimpleWorkflowConfig(BaseModel):
    """
    SimpleWorkflowConfig
    """ # noqa: E501
    t: StrictStr = Field(description="Discriminator value for SimpleWorkflowConfig", alias="_t")
    referee: CompareWorkflowConfigReferee
    blueprint: SimpleWorkflowConfigBlueprint
    target_country_codes: List[StrictStr] = Field(alias="targetCountryCodes")
    feature_flags: Optional[List[FeatureFlag]] = Field(default=None, alias="featureFlags")
    priority: Optional[StrictStr] = None
    is_fallback: Optional[StrictBool] = Field(default=None, alias="isFallback")
    rapid_selection_configs: Optional[List[CompareWorkflowConfigRapidSelectionConfigsInner]] = Field(default=None, alias="rapidSelectionConfigs")
    __properties: ClassVar[List[str]] = ["_t", "referee", "blueprint", "targetCountryCodes", "featureFlags", "priority", "isFallback", "rapidSelectionConfigs"]

    @field_validator('t')
    def t_validate_enum(cls, value):
        """Validates the enum"""
        if value not in set(['SimpleWorkflowConfig']):
            raise ValueError("must be one of enum values ('SimpleWorkflowConfig')")
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
        """Create an instance of SimpleWorkflowConfig from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of referee
        if self.referee:
            _dict['referee'] = self.referee.to_dict()
        # override the default output from pydantic by calling `to_dict()` of blueprint
        if self.blueprint:
            _dict['blueprint'] = self.blueprint.to_dict()
        # override the default output from pydantic by calling `to_dict()` of each item in feature_flags (list)
        _items = []
        if self.feature_flags:
            for _item_feature_flags in self.feature_flags:
                if _item_feature_flags:
                    _items.append(_item_feature_flags.to_dict())
            _dict['featureFlags'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in rapid_selection_configs (list)
        _items = []
        if self.rapid_selection_configs:
            for _item_rapid_selection_configs in self.rapid_selection_configs:
                if _item_rapid_selection_configs:
                    _items.append(_item_rapid_selection_configs.to_dict())
            _dict['rapidSelectionConfigs'] = _items
        # set to None if priority (nullable) is None
        # and model_fields_set contains the field
        if self.priority is None and "priority" in self.model_fields_set:
            _dict['priority'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of SimpleWorkflowConfig from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "_t": obj.get("_t") if obj.get("_t") is not None else 'SimpleWorkflowConfig',
            "referee": CompareWorkflowConfigReferee.from_dict(obj["referee"]) if obj.get("referee") is not None else None,
            "blueprint": SimpleWorkflowConfigBlueprint.from_dict(obj["blueprint"]) if obj.get("blueprint") is not None else None,
            "targetCountryCodes": obj.get("targetCountryCodes"),
            "featureFlags": [FeatureFlag.from_dict(_item) for _item in obj["featureFlags"]] if obj.get("featureFlags") is not None else None,
            "priority": obj.get("priority"),
            "isFallback": obj.get("isFallback"),
            "rapidSelectionConfigs": [CompareWorkflowConfigRapidSelectionConfigsInner.from_dict(_item) for _item in obj["rapidSelectionConfigs"]] if obj.get("rapidSelectionConfigs") is not None else None
        })
        return _obj

