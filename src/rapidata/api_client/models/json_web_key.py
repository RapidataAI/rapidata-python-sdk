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

from pydantic import BaseModel, ConfigDict, Field, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from typing import Optional, Set
from typing_extensions import Self

class JsonWebKey(BaseModel):
    """
    JsonWebKey
    """ # noqa: E501
    alg: Optional[StrictStr] = None
    crv: Optional[StrictStr] = None
    d: Optional[StrictStr] = None
    dp: Optional[StrictStr] = None
    dq: Optional[StrictStr] = None
    e: Optional[StrictStr] = None
    k: Optional[StrictStr] = None
    key_ops: Optional[List[StrictStr]] = None
    kid: Optional[StrictStr] = None
    kty: Optional[StrictStr] = None
    n: Optional[StrictStr] = None
    oth: Optional[List[StrictStr]] = None
    p: Optional[StrictStr] = None
    q: Optional[StrictStr] = None
    qi: Optional[StrictStr] = None
    use: Optional[StrictStr] = None
    x: Optional[StrictStr] = None
    x5c: Optional[List[StrictStr]] = None
    x5t: Optional[StrictStr] = None
    x5t_s256: Optional[StrictStr] = Field(default=None, alias="x5t#S256")
    x5u: Optional[StrictStr] = None
    y: Optional[StrictStr] = None
    additional_properties: Dict[str, Any] = {}
    __properties: ClassVar[List[str]] = ["alg", "crv", "d", "dp", "dq", "e", "k", "key_ops", "kid", "kty", "n", "oth", "p", "q", "qi", "use", "x", "x5c", "x5t", "x5t#S256", "x5u", "y"]

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
        """Create an instance of JsonWebKey from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        * OpenAPI `readOnly` fields are excluded.
        * OpenAPI `readOnly` fields are excluded.
        * OpenAPI `readOnly` fields are excluded.
        * Fields in `self.additional_properties` are added to the output dict.
        """
        excluded_fields: Set[str] = set([
            "key_ops",
            "oth",
            "x5c",
            "additional_properties",
        ])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # puts key-value pairs in additional_properties in the top level
        if self.additional_properties is not None:
            for _key, _value in self.additional_properties.items():
                _dict[_key] = _value

        # set to None if alg (nullable) is None
        # and model_fields_set contains the field
        if self.alg is None and "alg" in self.model_fields_set:
            _dict['alg'] = None

        # set to None if crv (nullable) is None
        # and model_fields_set contains the field
        if self.crv is None and "crv" in self.model_fields_set:
            _dict['crv'] = None

        # set to None if d (nullable) is None
        # and model_fields_set contains the field
        if self.d is None and "d" in self.model_fields_set:
            _dict['d'] = None

        # set to None if dp (nullable) is None
        # and model_fields_set contains the field
        if self.dp is None and "dp" in self.model_fields_set:
            _dict['dp'] = None

        # set to None if dq (nullable) is None
        # and model_fields_set contains the field
        if self.dq is None and "dq" in self.model_fields_set:
            _dict['dq'] = None

        # set to None if e (nullable) is None
        # and model_fields_set contains the field
        if self.e is None and "e" in self.model_fields_set:
            _dict['e'] = None

        # set to None if k (nullable) is None
        # and model_fields_set contains the field
        if self.k is None and "k" in self.model_fields_set:
            _dict['k'] = None

        # set to None if key_ops (nullable) is None
        # and model_fields_set contains the field
        if self.key_ops is None and "key_ops" in self.model_fields_set:
            _dict['key_ops'] = None

        # set to None if kid (nullable) is None
        # and model_fields_set contains the field
        if self.kid is None and "kid" in self.model_fields_set:
            _dict['kid'] = None

        # set to None if kty (nullable) is None
        # and model_fields_set contains the field
        if self.kty is None and "kty" in self.model_fields_set:
            _dict['kty'] = None

        # set to None if n (nullable) is None
        # and model_fields_set contains the field
        if self.n is None and "n" in self.model_fields_set:
            _dict['n'] = None

        # set to None if oth (nullable) is None
        # and model_fields_set contains the field
        if self.oth is None and "oth" in self.model_fields_set:
            _dict['oth'] = None

        # set to None if p (nullable) is None
        # and model_fields_set contains the field
        if self.p is None and "p" in self.model_fields_set:
            _dict['p'] = None

        # set to None if q (nullable) is None
        # and model_fields_set contains the field
        if self.q is None and "q" in self.model_fields_set:
            _dict['q'] = None

        # set to None if qi (nullable) is None
        # and model_fields_set contains the field
        if self.qi is None and "qi" in self.model_fields_set:
            _dict['qi'] = None

        # set to None if use (nullable) is None
        # and model_fields_set contains the field
        if self.use is None and "use" in self.model_fields_set:
            _dict['use'] = None

        # set to None if x (nullable) is None
        # and model_fields_set contains the field
        if self.x is None and "x" in self.model_fields_set:
            _dict['x'] = None

        # set to None if x5c (nullable) is None
        # and model_fields_set contains the field
        if self.x5c is None and "x5c" in self.model_fields_set:
            _dict['x5c'] = None

        # set to None if x5t (nullable) is None
        # and model_fields_set contains the field
        if self.x5t is None and "x5t" in self.model_fields_set:
            _dict['x5t'] = None

        # set to None if x5t_s256 (nullable) is None
        # and model_fields_set contains the field
        if self.x5t_s256 is None and "x5t_s256" in self.model_fields_set:
            _dict['x5t#S256'] = None

        # set to None if x5u (nullable) is None
        # and model_fields_set contains the field
        if self.x5u is None and "x5u" in self.model_fields_set:
            _dict['x5u'] = None

        # set to None if y (nullable) is None
        # and model_fields_set contains the field
        if self.y is None and "y" in self.model_fields_set:
            _dict['y'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of JsonWebKey from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "alg": obj.get("alg"),
            "crv": obj.get("crv"),
            "d": obj.get("d"),
            "dp": obj.get("dp"),
            "dq": obj.get("dq"),
            "e": obj.get("e"),
            "k": obj.get("k"),
            "key_ops": obj.get("key_ops"),
            "kid": obj.get("kid"),
            "kty": obj.get("kty"),
            "n": obj.get("n"),
            "oth": obj.get("oth"),
            "p": obj.get("p"),
            "q": obj.get("q"),
            "qi": obj.get("qi"),
            "use": obj.get("use"),
            "x": obj.get("x"),
            "x5c": obj.get("x5c"),
            "x5t": obj.get("x5t"),
            "x5t#S256": obj.get("x5t#S256"),
            "x5u": obj.get("x5u"),
            "y": obj.get("y")
        })
        # store additional fields in additional_properties
        for _key in obj.keys():
            if _key not in cls.__properties:
                _obj.additional_properties[_key] = obj.get(_key)

        return _obj


