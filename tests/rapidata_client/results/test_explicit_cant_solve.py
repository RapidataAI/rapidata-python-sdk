from __future__ import annotations

import copy
import json

import pytest
from pydantic import Field, StrictBool, ValidationError

from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.lazy_model import LazyValidatedModel
from rapidata.api_client.models.attach_category_result import AttachCategoryResult
from rapidata.api_client.models.compare_result import CompareResult
from rapidata.api_client.models.i_rapid_result import IRapidResult
from rapidata.api_client.models.i_rapid_result_model import IRapidResultModel
from rapidata.api_client.models.i_rapid_result_attach_category_result import (
    IRapidResultAttachCategoryResult,
)
from rapidata.api_client.models.i_rapid_result_compare_result import (
    IRapidResultCompareResult,
)
from rapidata.api_client.models.i_rapid_result_model_attach_category_result_model import (
    IRapidResultModelAttachCategoryResultModel,
)
from rapidata.api_client.models.i_rapid_result_model_compare_result_model import (
    IRapidResultModelCompareResultModel,
)
from rapidata.rapidata_client.results._explicit_cant_solve import adapt_response_model

_COMPARE_MODELS = [
    CompareResult,
    IRapidResultCompareResult,
    IRapidResultModelCompareResultModel,
    IRapidResult,
    IRapidResultModel,
]
_CLASSIFY_MODELS = [
    AttachCategoryResult,
    IRapidResultAttachCategoryResult,
    IRapidResultModelAttachCategoryResultModel,
    IRapidResult,
    IRapidResultModel,
]


def _actual(model):
    return (
        model.actual_instance
        if isinstance(model, (IRapidResult, IRapidResultModel))
        else model
    )


@pytest.mark.parametrize("model_type", _COMPARE_MODELS)
@pytest.mark.parametrize(
    "answer",
    [
        {"winners": [], "cantSolve": True},
        {"winners": [], "cantSolve": False},
        {"winners": []},
        {"winners": ["雪.asset", "arbitrary.string"], "cantSolve": False},
        {"winners": ["雪.asset"]},
    ],
)
def test_typed_compare_responses_preserve_explicit_markers_and_substantive_selections(
    model_type, answer
):
    wire = {"_t": "CompareResult", "rapidId": "rapid-1", **copy.deepcopy(answer)}
    original = copy.deepcopy(wire)
    model = model_type.from_dict(wire)
    expected = {**wire, "cantSolve": wire.get("cantSolve", False)}
    actual = _actual(model)
    assert actual.cant_solve is wire.get("cantSolve", False)
    assert actual.winners == answer["winners"]
    assert model.to_dict() == expected
    assert json.loads(model.to_json()) == expected
    with ApiClient() as client:
        assert client.sanitize_for_serialization(model) == expected
    assert wire == original


@pytest.mark.parametrize("model_type", _CLASSIFY_MODELS)
@pytest.mark.parametrize(
    "answer",
    [
        {"cantSolve": True},
        {"category": "", "cantSolve": True},
        {"category": "雪.arbitrary/value", "cantSolve": False},
        {"category": "", "cantSolve": False},
        {"category": "bothGood"},
        {"category": "c0"},
    ],
)
def test_typed_classify_cs_allows_no_category_without_relabeling_category_values(
    model_type, answer
):
    wire = {"_t": "AttachCategoryResult", "rapidId": "rapid-1", **copy.deepcopy(answer)}
    original = copy.deepcopy(wire)
    model = model_type.from_json(json.dumps(wire))
    actual = _actual(model)
    expected = {**wire, "cantSolve": wire.get("cantSolve", False)}
    assert actual.cant_solve is wire.get("cantSolve", False)
    assert actual.category == answer.get("category")
    assert model.to_dict() == expected
    assert json.loads(model.to_json()) == expected
    with ApiClient() as client:
        assert client.sanitize_for_serialization(model) == expected
    assert wire == original


@pytest.mark.parametrize("model_type", _CLASSIFY_MODELS[1:])
def test_missing_category_without_cs_marker_keeps_lazy_validation_error(model_type):
    model = _actual(
        model_type.from_dict({"_t": "AttachCategoryResult", "rapidId": "rapid-1"})
    )
    assert model.cant_solve is False
    with pytest.raises(TypeError, match="category"):
        _ = model.category


def test_explicit_response_adapter_defers_to_native_marker_fields():
    class NativeResponse(LazyValidatedModel):
        winners: list[str] | None = None
        cant_solve: StrictBool = Field(False, alias="cantSolve")

    assert (
        adapt_response_model(
            NativeResponse, {"_t": "CompareResult", "winners": [], "cantSolve": True}
        )
        is None
    )


def test_older_concrete_model_keeps_eager_validation_for_missing_normal_category():
    with pytest.raises(ValidationError, match="category"):
        AttachCategoryResult.from_dict(
            {"_t": "AttachCategoryResult", "rapidId": "rapid-1"}
        )
