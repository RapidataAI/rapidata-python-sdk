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

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr
from typing import Any, ClassVar, Dict, List, Optional, Union
from rapidata.api_client.models.add_validation_rapid_model_payload import AddValidationRapidModelPayload
from rapidata.api_client.models.add_validation_rapid_model_truth import AddValidationRapidModelTruth
from rapidata.api_client.models.dataset_dataset_id_datapoints_post_request_metadata_inner import DatasetDatasetIdDatapointsPostRequestMetadataInner
from typing import Optional, Set
from typing_extensions import Self

class AddValidationRapidModel(BaseModel):
    """
    The model for adding a validation rapid.
    """ # noqa: E501
    payload: AddValidationRapidModelPayload
    metadata: List[DatasetDatasetIdDatapointsPostRequestMetadataInner] = Field(description="Some metadata to attach to the rapid.")
    truth: AddValidationRapidModelTruth
    random_correct_probability: Optional[Union[StrictFloat, StrictInt]] = Field(default=None, description="The probability for an answer to be correct when randomly guessing.", alias="randomCorrectProbability")
    explanation: Optional[StrictStr] = Field(default=None, description="An explanation for the users if they answer the rapid incorrectly.")
    __properties: ClassVar[List[str]] = ["payload", "metadata", "truth", "randomCorrectProbability", "explanation"]

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
        """Create an instance of AddValidationRapidModel from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of payload
        if self.payload:
            _dict['payload'] = self.payload.to_dict()
        # override the default output from pydantic by calling `to_dict()` of each item in metadata (list)
        _items = []
        if self.metadata:
            for _item_metadata in self.metadata:
                if _item_metadata:
                    _items.append(_item_metadata.to_dict())
            _dict['metadata'] = _items
        # override the default output from pydantic by calling `to_dict()` of truth
        if self.truth:
            _dict['truth'] = self.truth.to_dict()
        # set to None if random_correct_probability (nullable) is None
        # and model_fields_set contains the field
        if self.random_correct_probability is None and "random_correct_probability" in self.model_fields_set:
            _dict['randomCorrectProbability'] = None

        # set to None if explanation (nullable) is None
        # and model_fields_set contains the field
        if self.explanation is None and "explanation" in self.model_fields_set:
            _dict['explanation'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of AddValidationRapidModel from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "payload": AddValidationRapidModelPayload.from_dict(obj["payload"]) if obj.get("payload") is not None else None,
            "metadata": [DatasetDatasetIdDatapointsPostRequestMetadataInner.from_dict(_item) for _item in obj["metadata"]] if obj.get("metadata") is not None else None,
            "truth": AddValidationRapidModelTruth.from_dict(obj["truth"]) if obj.get("truth") is not None else None,
            "randomCorrectProbability": obj.get("randomCorrectProbability"),
            "explanation": obj.get("explanation")
        })
        return _obj


