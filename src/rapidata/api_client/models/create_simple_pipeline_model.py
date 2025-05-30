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

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from typing import Any, ClassVar, Dict, List
from rapidata.api_client.models.create_simple_pipeline_model_artifacts_inner import CreateSimplePipelineModelArtifactsInner
from rapidata.api_client.models.create_simple_pipeline_model_pipeline_steps_inner import CreateSimplePipelineModelPipelineStepsInner
from typing import Optional, Set
from typing_extensions import Self

class CreateSimplePipelineModel(BaseModel):
    """
    Model for creating a simple pipeline
    """ # noqa: E501
    t: StrictStr = Field(description="Discriminator value for CreateSimplePipelineModel", alias="_t")
    artifacts: List[CreateSimplePipelineModelArtifactsInner] = Field(description="The list of static artifacts")
    pipeline_steps: List[CreateSimplePipelineModelPipelineStepsInner] = Field(description="The list of pipeline steps", alias="pipelineSteps")
    name_prefix: StrictStr = Field(description="The prefix for the pipeline name", alias="namePrefix")
    __properties: ClassVar[List[str]] = ["_t", "artifacts", "pipelineSteps", "namePrefix"]

    @field_validator('t')
    def t_validate_enum(cls, value):
        """Validates the enum"""
        if value not in set(['CreateSimplePipelineModel']):
            raise ValueError("must be one of enum values ('CreateSimplePipelineModel')")
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
        """Create an instance of CreateSimplePipelineModel from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of each item in artifacts (list)
        _items = []
        if self.artifacts:
            for _item_artifacts in self.artifacts:
                if _item_artifacts:
                    _items.append(_item_artifacts.to_dict())
            _dict['artifacts'] = _items
        # override the default output from pydantic by calling `to_dict()` of each item in pipeline_steps (list)
        _items = []
        if self.pipeline_steps:
            for _item_pipeline_steps in self.pipeline_steps:
                if _item_pipeline_steps:
                    _items.append(_item_pipeline_steps.to_dict())
            _dict['pipelineSteps'] = _items
        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of CreateSimplePipelineModel from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "_t": obj.get("_t") if obj.get("_t") is not None else 'CreateSimplePipelineModel',
            "artifacts": [CreateSimplePipelineModelArtifactsInner.from_dict(_item) for _item in obj["artifacts"]] if obj.get("artifacts") is not None else None,
            "pipelineSteps": [CreateSimplePipelineModelPipelineStepsInner.from_dict(_item) for _item in obj["pipelineSteps"]] if obj.get("pipelineSteps") is not None else None,
            "namePrefix": obj.get("namePrefix")
        })
        return _obj


