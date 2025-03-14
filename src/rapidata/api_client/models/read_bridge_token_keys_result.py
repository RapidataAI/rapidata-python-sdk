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

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator
from typing import Any, ClassVar, Dict, List, Optional
from typing import Optional, Set
from typing_extensions import Self

class ReadBridgeTokenKeysResult(BaseModel):
    """
    ReadBridgeTokenKeysResult
    """ # noqa: E501
    t: StrictStr = Field(description="Discriminator value for ReadBridgeTokenKeysResult", alias="_t")
    access_token: Optional[StrictStr] = Field(default=None, alias="accessToken")
    expires_in: Optional[StrictInt] = Field(default=None, alias="expiresIn")
    refresh_token: Optional[StrictStr] = Field(default=None, alias="refreshToken")
    id_token: Optional[StrictStr] = Field(default=None, alias="idToken")
    token_type: Optional[StrictStr] = Field(default=None, alias="tokenType")
    scope: Optional[StrictStr] = None
    __properties: ClassVar[List[str]] = ["_t", "accessToken", "expiresIn", "refreshToken", "idToken", "tokenType", "scope"]

    @field_validator('t')
    def t_validate_enum(cls, value):
        """Validates the enum"""
        if value not in set(['ReadBridgeTokenKeysResult']):
            raise ValueError("must be one of enum values ('ReadBridgeTokenKeysResult')")
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
        """Create an instance of ReadBridgeTokenKeysResult from a JSON string"""
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
        # set to None if access_token (nullable) is None
        # and model_fields_set contains the field
        if self.access_token is None and "access_token" in self.model_fields_set:
            _dict['accessToken'] = None

        # set to None if expires_in (nullable) is None
        # and model_fields_set contains the field
        if self.expires_in is None and "expires_in" in self.model_fields_set:
            _dict['expiresIn'] = None

        # set to None if refresh_token (nullable) is None
        # and model_fields_set contains the field
        if self.refresh_token is None and "refresh_token" in self.model_fields_set:
            _dict['refreshToken'] = None

        # set to None if id_token (nullable) is None
        # and model_fields_set contains the field
        if self.id_token is None and "id_token" in self.model_fields_set:
            _dict['idToken'] = None

        # set to None if token_type (nullable) is None
        # and model_fields_set contains the field
        if self.token_type is None and "token_type" in self.model_fields_set:
            _dict['tokenType'] = None

        # set to None if scope (nullable) is None
        # and model_fields_set contains the field
        if self.scope is None and "scope" in self.model_fields_set:
            _dict['scope'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of ReadBridgeTokenKeysResult from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "_t": obj.get("_t") if obj.get("_t") is not None else 'ReadBridgeTokenKeysResult',
            "accessToken": obj.get("accessToken"),
            "expiresIn": obj.get("expiresIn"),
            "refreshToken": obj.get("refreshToken"),
            "idToken": obj.get("idToken"),
            "tokenType": obj.get("tokenType"),
            "scope": obj.get("scope")
        })
        return _obj


