# coding: utf-8

"""
    Rapidata.Dataset

    No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)

    The version of the OpenAPI document: v1
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


from __future__ import annotations
import json
import pprint
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError, field_validator
from typing import Any, List, Optional
from rapidata.api_client.models.bounding_box_payload import BoundingBoxPayload
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.free_text_payload import FreeTextPayload
from rapidata.api_client.models.line_payload import LinePayload
from rapidata.api_client.models.locate_payload import LocatePayload
from rapidata.api_client.models.named_entity_payload import NamedEntityPayload
from rapidata.api_client.models.polygon_payload import PolygonPayload
from rapidata.api_client.models.transcription_payload import TranscriptionPayload
from pydantic import StrictStr, Field
from typing import Union, List, Set, Optional, Dict
from typing_extensions import Literal, Self

ADDVALIDATIONRAPIDMODELPAYLOAD_ONE_OF_SCHEMAS = ["BoundingBoxPayload", "ClassifyPayload", "ComparePayload", "FreeTextPayload", "LinePayload", "LocatePayload", "NamedEntityPayload", "PolygonPayload", "TranscriptionPayload"]

class AddValidationRapidModelPayload(BaseModel):
    """
    The payload to use for the rapid.
    """
    # data type: TranscriptionPayload
    oneof_schema_1_validator: Optional[TranscriptionPayload] = None
    # data type: PolygonPayload
    oneof_schema_2_validator: Optional[PolygonPayload] = None
    # data type: NamedEntityPayload
    oneof_schema_3_validator: Optional[NamedEntityPayload] = None
    # data type: LocatePayload
    oneof_schema_4_validator: Optional[LocatePayload] = None
    # data type: LinePayload
    oneof_schema_5_validator: Optional[LinePayload] = None
    # data type: FreeTextPayload
    oneof_schema_6_validator: Optional[FreeTextPayload] = None
    # data type: ComparePayload
    oneof_schema_7_validator: Optional[ComparePayload] = None
    # data type: ClassifyPayload
    oneof_schema_8_validator: Optional[ClassifyPayload] = None
    # data type: BoundingBoxPayload
    oneof_schema_9_validator: Optional[BoundingBoxPayload] = None
    actual_instance: Optional[Union[BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload]] = None
    one_of_schemas: Set[str] = { "BoundingBoxPayload", "ClassifyPayload", "ComparePayload", "FreeTextPayload", "LinePayload", "LocatePayload", "NamedEntityPayload", "PolygonPayload", "TranscriptionPayload" }

    model_config = ConfigDict(
        validate_assignment=True,
        protected_namespaces=(),
    )


    discriminator_value_class_map: Dict[str, str] = {
    }

    def __init__(self, *args, **kwargs) -> None:
        if args:
            if len(args) > 1:
                raise ValueError("If a position argument is used, only 1 is allowed to set `actual_instance`")
            if kwargs:
                raise ValueError("If a position argument is used, keyword arguments cannot be used.")
            super().__init__(actual_instance=args[0])
        else:
            super().__init__(**kwargs)

    @field_validator('actual_instance')
    def actual_instance_must_validate_oneof(cls, v):
        instance = AddValidationRapidModelPayload.model_construct()
        error_messages = []
        match = 0
        # validate data type: TranscriptionPayload
        if not isinstance(v, TranscriptionPayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `TranscriptionPayload`")
        else:
            match += 1
        # validate data type: PolygonPayload
        if not isinstance(v, PolygonPayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `PolygonPayload`")
        else:
            match += 1
        # validate data type: NamedEntityPayload
        if not isinstance(v, NamedEntityPayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `NamedEntityPayload`")
        else:
            match += 1
        # validate data type: LocatePayload
        if not isinstance(v, LocatePayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `LocatePayload`")
        else:
            match += 1
        # validate data type: LinePayload
        if not isinstance(v, LinePayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `LinePayload`")
        else:
            match += 1
        # validate data type: FreeTextPayload
        if not isinstance(v, FreeTextPayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `FreeTextPayload`")
        else:
            match += 1
        # validate data type: ComparePayload
        if not isinstance(v, ComparePayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `ComparePayload`")
        else:
            match += 1
        # validate data type: ClassifyPayload
        if not isinstance(v, ClassifyPayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `ClassifyPayload`")
        else:
            match += 1
        # validate data type: BoundingBoxPayload
        if not isinstance(v, BoundingBoxPayload):
            error_messages.append(f"Error! Input type `{type(v)}` is not `BoundingBoxPayload`")
        else:
            match += 1
        if match > 1:
            # more than 1 match
            raise ValueError("Multiple matches found when setting `actual_instance` in AddValidationRapidModelPayload with oneOf schemas: BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload. Details: " + ", ".join(error_messages))
        elif match == 0:
            # no match
            raise ValueError("No match found when setting `actual_instance` in AddValidationRapidModelPayload with oneOf schemas: BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload. Details: " + ", ".join(error_messages))
        else:
            return v

    @classmethod
    def from_dict(cls, obj: Union[str, Dict[str, Any]]) -> Self:
        return cls.from_json(json.dumps(obj))

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Returns the object represented by the json string"""
        instance = cls.model_construct()
        error_messages = []
        match = 0

        # deserialize data into TranscriptionPayload
        try:
            instance.actual_instance = TranscriptionPayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into PolygonPayload
        try:
            instance.actual_instance = PolygonPayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into NamedEntityPayload
        try:
            instance.actual_instance = NamedEntityPayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into LocatePayload
        try:
            instance.actual_instance = LocatePayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into LinePayload
        try:
            instance.actual_instance = LinePayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into FreeTextPayload
        try:
            instance.actual_instance = FreeTextPayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into ComparePayload
        try:
            instance.actual_instance = ComparePayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into ClassifyPayload
        try:
            instance.actual_instance = ClassifyPayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))
        # deserialize data into BoundingBoxPayload
        try:
            instance.actual_instance = BoundingBoxPayload.from_json(json_str)
            match += 1
        except (ValidationError, ValueError) as e:
            error_messages.append(str(e))

        if match > 1:
            # more than 1 match
            raise ValueError("Multiple matches found when deserializing the JSON string into AddValidationRapidModelPayload with oneOf schemas: BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload. Details: " + ", ".join(error_messages))
        elif match == 0:
            # no match
            raise ValueError("No match found when deserializing the JSON string into AddValidationRapidModelPayload with oneOf schemas: BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload. Details: " + ", ".join(error_messages))
        else:
            return instance

    def to_json(self) -> str:
        """Returns the JSON representation of the actual instance"""
        if self.actual_instance is None:
            return "null"

        if hasattr(self.actual_instance, "to_json") and callable(self.actual_instance.to_json):
            return self.actual_instance.to_json()
        else:
            return json.dumps(self.actual_instance)

    def to_dict(self) -> Optional[Union[Dict[str, Any], BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload]]:
        """Returns the dict representation of the actual instance"""
        if self.actual_instance is None:
            return None

        if hasattr(self.actual_instance, "to_dict") and callable(self.actual_instance.to_dict):
            return self.actual_instance.to_dict()
        else:
            # primitive type
            return self.actual_instance

    def to_str(self) -> str:
        """Returns the string representation of the actual instance"""
        return pprint.pformat(self.model_dump())

