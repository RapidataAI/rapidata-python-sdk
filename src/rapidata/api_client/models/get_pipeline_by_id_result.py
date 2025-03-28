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

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, ClassVar, Dict, List
from rapidata.api_client.models.feature_flag import FeatureFlag
from rapidata.api_client.models.get_pipeline_by_id_result_artifacts_value import GetPipelineByIdResultArtifactsValue
from typing import Optional, Set
from typing_extensions import Self

class GetPipelineByIdResult(BaseModel):
    """
    GetPipelineByIdResult
    """ # noqa: E501
    artifacts: Dict[str, GetPipelineByIdResultArtifactsValue]
    feature_flags: List[FeatureFlag] = Field(alias="featureFlags")
    __properties: ClassVar[List[str]] = ["artifacts", "featureFlags"]

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
        """Create an instance of GetPipelineByIdResult from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of each value in artifacts (dict)
        _field_dict = {}
        if self.artifacts:
            for _key_artifacts in self.artifacts:
                if self.artifacts[_key_artifacts]:
                    _field_dict[_key_artifacts] = self.artifacts[_key_artifacts].to_dict()
            _dict['artifacts'] = _field_dict
        # override the default output from pydantic by calling `to_dict()` of each item in feature_flags (list)
        _items = []
        if self.feature_flags:
            for _item_feature_flags in self.feature_flags:
                if _item_feature_flags:
                    _items.append(_item_feature_flags.to_dict())
            _dict['featureFlags'] = _items
        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of GetPipelineByIdResult from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "artifacts": dict(
                (_k, GetPipelineByIdResultArtifactsValue.from_dict(_v))
                for _k, _v in obj["artifacts"].items()
            )
            if obj.get("artifacts") is not None
            else None,
            "featureFlags": [FeatureFlag.from_dict(_item) for _item in obj["featureFlags"]] if obj.get("featureFlags") is not None else None
        })
        return _obj


