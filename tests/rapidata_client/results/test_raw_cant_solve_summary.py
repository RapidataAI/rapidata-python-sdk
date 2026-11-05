from __future__ import annotations

import copy
import json
from unittest.mock import MagicMock

import pytest

from rapidata import RapidataJob
from rapidata.rapidata_client.results import RapidataResults


def _frozen(kind: str) -> dict:
    prefix = "a" if kind == "Compare" else "c"
    return {
        "modelVersion": "score-weighted-categorical-v1",
        "verdict": "Winner",
        "leadingOutcomeIds": [f"{prefix}0"],
        "responseCount": 18,
        "outcomes": [
            {
                "outcomeId": f"{prefix}0",
                "count": 17,
                "userScoreSum": 5.0,
                "share": {"estimate": 1.0, "lower": 0.9, "upper": 1.0},
            },
            {
                "outcomeId": f"{prefix}1",
                "count": 0,
                "userScoreSum": 0.0,
                "share": {"estimate": 0.0, "lower": 0.0, "upper": 0.1},
            },
        ],
        "cantSolve": {
            "count": 1,
            "userScoreSum": 0.4,
            "share": {"estimate": 0.4 / 5.4, "lower": 0.0, "upper": 0.49},
        },
        "ambiguity": {"estimate": 0.0, "lower": 0.0, "upper": 0.9},
        "parameters": {
            "maxVotes": 100,
            "minConfidence": 0.9,
            "ambiguityThreshold": 0.64,
            "unsolvableThreshold": 0.5,
            "maxOutcomeCount": 1,
        },
    }


def _payload(kind: str, snapshot: str = "absent") -> dict:
    row = {
        "identifier": "rapid-1",
        "aggregatedResults": {"count": 17, "userScoreSum": 0},
        "summedUserScores": {"count": 5.0, "userScoreSum": 0.0},
        "cantSolve": {"count": 3, "userScoreSum": 1.7},
    }
    if kind == "Compare":
        row["assetUrls"] = {"count": "https://left", "userScoreSum": "https://right"}
        row["detailedResults"] = [
            {
                "_t": "CompareResult",
                "rapidId": "rapid-1",
                "winners": [],
                "cantSolve": True,
            },
            {
                "_t": "CompareResult",
                "rapidId": "rapid-1",
                "winners": ["count"],
                "cantSolve": False,
            },
        ]
    else:
        row["detailedResults"] = [
            {"_t": "AttachCategoryResult", "rapidId": "rapid-1", "cantSolve": True},
            {
                "_t": "AttachCategoryResult",
                "rapidId": "rapid-1",
                "category": "count",
                "cantSolve": False,
            },
        ]
    cs, substantive = row["detailedResults"]
    row["detailedResults"] = [copy.deepcopy(cs) for _ in range(3)] + [
        copy.deepcopy(substantive) for _ in range(17)
    ]
    if snapshot == "null":
        row["adaptiveStopping"] = None
    elif snapshot == "frozen":
        row["adaptiveStopping"] = _frozen(kind)
    return {"info": {"type": kind}, "results": [row]}


@pytest.mark.parametrize(
    "kind", ["Compare", "Classify", "Classification", "FutureTask"]
)
@pytest.mark.parametrize("snapshot", ["absent", "null", "frozen"])
@pytest.mark.parametrize("split_details", [False, True])
def test_raw_cs_summary_is_opaque_and_separate_from_frozen_evidence_and_markers(
    kind, snapshot, split_details, tmp_path
):
    payload = _payload(kind, snapshot)
    original = copy.deepcopy(payload)
    result = RapidataResults(payload)
    frame = result.to_pandas(split_details=split_details)
    raw_summary = original["results"][0]["cantSolve"]
    assert all(value == raw_summary for value in frame["cantSolve"])
    assert "share" not in frame.iloc[0]["cantSolve"]
    assert "A_cantSolve" not in frame and "B_cantSolve" not in frame
    if split_details:
        assert list(frame["responseCantSolve"]) == [True] * 3 + [False] * 17
    else:
        assert "responseCantSolve" not in frame
    if snapshot == "frozen":
        assert all(value == _frozen(kind) for value in frame["adaptiveStopping"])
        assert result["results"][0]["verdict"] == "Winner"
        assert result["results"][0]["responses"] == 18
        assert frame.iloc[0]["adaptiveStopping"]["cantSolve"]["count"] == 1
    else:
        assert "verdict" not in result["results"][0]
        assert "responses" not in result["results"][0]
    path = tmp_path / "raw-cs.json"
    result.to_json(str(path))
    saved = json.loads(path.read_text())["results"][0]
    assert saved["cantSolve"] == raw_summary
    assert saved["detailedResults"] == original["results"][0]["detailedResults"]
    assert ("adaptiveStopping" in saved) == (snapshot != "absent")


@pytest.mark.parametrize("kind", ["Compare", "Classify"])
@pytest.mark.parametrize("split_details", [False, True])
def test_nonadaptive_all_cs_export_keeps_a_row_without_substantive_votes(
    kind, split_details
):
    payload = _payload(kind)
    row = payload["results"][0]
    row["aggregatedResults"] = {}
    row["summedUserScores"] = {}
    row.pop("assetUrls", None)
    row["detailedResults"] = [row["detailedResults"][0]]
    row["cantSolve"] = {
        "count": 1,
        "userScoreSum": 0.0,
        "future": {"estimate": None},
    }
    result = RapidataResults(payload)
    frame = result.to_pandas(split_details=split_details)
    assert len(frame) == 1
    assert frame.iloc[0]["cantSolve"] == row["cantSolve"]
    assert "adaptiveStopping" not in frame
    assert "verdict" not in frame
    assert "winner" not in result["results"][0]


@pytest.mark.parametrize("kind", ["Compare", "Classify", "FutureTask"])
def test_mixed_detail_availability_keeps_every_raw_summary(kind):
    payload = _payload(kind)
    detail_row = payload["results"][0]
    empty_row = copy.deepcopy(detail_row)
    empty_row.update(identifier="no-details", detailedResults=[])
    missing_row = copy.deepcopy(empty_row)
    missing_row.update(identifier="missing-details")
    del missing_row["detailedResults"]
    payload["results"] = [missing_row, empty_row, detail_row]
    frame = RapidataResults(payload).to_pandas(split_details=True)
    assert (
        list(frame["identifier"])
        == ["missing-details", "no-details"] + ["rapid-1"] * 20
    )
    assert all(
        value == {"count": 3, "userScoreSum": 1.7} for value in frame["cantSolve"]
    )


@pytest.mark.parametrize("kind", ["Compare", "Classify"])
@pytest.mark.parametrize("raw", ["missing", None])
def test_missing_raw_summary_is_not_inferred_from_response_markers(kind, raw):
    payload = _payload(kind)
    row = payload["results"][0]
    if raw == "missing":
        del row["cantSolve"]
    else:
        row["cantSolve"] = None
    result = RapidataResults(payload)
    frame = result.to_pandas(split_details=True)
    assert list(frame["responseCantSolve"]) == [True] * 3 + [False] * 17
    assert ("cantSolve" in row) == (raw != "missing")
    if raw == "missing":
        assert "cantSolve" not in frame
    else:
        assert all(value is None for value in frame["cantSolve"])


@pytest.mark.parametrize("kind", ["Compare", "Classify"])
@pytest.mark.parametrize("preliminary", [False, True])
def test_final_and_preliminary_downloads_preserve_raw_cs_separately(kind, preliminary):
    service = MagicMock()
    service.environment = "rapidata.ai"
    job = RapidataJob(
        "job-1", "Job", "global", MagicMock(), "def-1", service, pipeline_id="pip-1"
    )
    job.get_status = MagicMock(return_value="Running" if preliminary else "Completed")
    job._wait_for_status = MagicMock()
    payload = _payload(kind, "frozen")
    service.order.job_api.job_job_id_download_results_get.return_value = json.dumps(
        payload
    )
    pipeline = service.pipeline.pipeline_api
    pipeline.pipeline_pipeline_id_preliminary_download_post.return_value.download_id = (
        "download-1"
    )
    response = (
        pipeline.pipeline_preliminary_download_preliminary_download_id_get_with_http_info.return_value
    )
    response.status_code = 200
    response.raw_data = json.dumps(payload).encode()
    result = job.get_results(preliminary_results=preliminary)
    row = result["results"][0]
    assert row["cantSolve"] == {"count": 3, "userScoreSum": 1.7}
    assert row["adaptiveStopping"] == _frozen(kind)
    frame = result.to_pandas(split_details=True)
    assert list(frame["responseCantSolve"]) == [True] * 3 + [False] * 17
    assert all(value == row["cantSolve"] for value in frame["cantSolve"])


@pytest.mark.parametrize("kind", ["Compare", "Classify"])
@pytest.mark.parametrize("snapshot_cs", ["missing", None])
@pytest.mark.parametrize("split_details", [False, True])
def test_raw_summary_does_not_enable_or_replace_disabled_snapshot_cs(
    kind, snapshot_cs, split_details
):
    payload = _payload(kind, "frozen")
    state = payload["results"][0]["adaptiveStopping"]
    state["parameters"]["unsolvableThreshold"] = None
    if snapshot_cs == "missing":
        del state["cantSolve"]
    else:
        state["cantSolve"] = None
    original = copy.deepcopy(state)
    result = RapidataResults(payload)
    frame = result.to_pandas(split_details=split_details)
    assert all(value == original for value in frame["adaptiveStopping"])
    assert all(
        value == {"count": 3, "userScoreSum": 1.7} for value in frame["cantSolve"]
    )
    assert result["results"][0]["adaptiveStopping"] == original
    assert result["results"][0]["verdict"] == "Winner"


def test_legacy_stopping_snapshot_and_raw_summary_remain_independent():
    payload = _payload("Compare")
    legacy = {"verdict": "A", "responseCount": 18, "ambiguityRange": 0.6}
    payload["results"][0]["stoppingState"] = copy.deepcopy(legacy)
    result = RapidataResults(payload)
    frame = result.to_pandas(split_details=True)
    assert result["results"][0]["stoppingState"] == legacy
    assert result["results"][0]["verdict"] == "A"
    assert all(
        value == {"count": 3, "userScoreSum": 1.7} for value in frame["cantSolve"]
    )
    assert list(frame["responseCantSolve"]) == [True] * 3 + [False] * 17
