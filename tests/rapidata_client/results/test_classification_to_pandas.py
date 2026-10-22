"""Classification results as one dataframe row per datapoint and answer option."""

from __future__ import annotations

import pytest

from rapidata.rapidata_client.results.rapidata_results import RapidataResults


def _datapoint(identifier: str, counts: dict[str, int], **extra) -> dict:
    total = sum(counts.values()) or 1
    return {
        "identifier": identifier,
        "text": identifier,
        "aggregatedResults": counts,
        "aggregatedResultsRatios": {k: v / total for k, v in counts.items()},
        "summedUserScores": {k: v * 0.5 for k, v in counts.items()},
        "summedUserScoresRatios": {k: v / total for k, v in counts.items()},
        "detailedResults": [
            {"selectedCategory": k, "userDetails": {"country": "CH"}}
            for k, v in counts.items()
            for _ in range(v)
        ],
        **extra,
    }


def _results(*datapoints: dict) -> RapidataResults:
    return RapidataResults(
        {
            "info": {"type": "Classification"},
            "summary": {},
            "results": list(datapoints),
        }
    )


def test_each_datapoint_keeps_its_own_options():
    results = _results(
        _datapoint("banana", {"Yellow": 8, "Blue": 1, "Purple": 1}),
        _datapoint("A dog", {"Woof": 9, "Meow": 1}),
    )

    df = results.to_pandas()

    assert list(zip(df["identifier"], df["option"], df["count"])) == [
        ("banana", "Yellow", 8),
        ("banana", "Blue", 1),
        ("banana", "Purple", 1),
        ("A dog", "Woof", 9),
        ("A dog", "Meow", 1),
    ]
    woof = df[df["option"] == "Woof"].iloc[0]
    assert woof["ratio"] == pytest.approx(0.9)
    assert woof["summedUserScore"] == pytest.approx(4.5)
    assert woof["summedUserScoreRatio"] == pytest.approx(0.9)


def test_columns_are_datapoint_fields_then_option_metrics():
    df = _results(_datapoint("banana", {"Yellow": 1, "Blue": 1})).to_pandas()

    assert list(df.columns) == [
        "identifier",
        "text",
        "option",
        "count",
        "ratio",
        "summedUserScore",
        "summedUserScoreRatio",
    ]


def test_private_metadata_and_confidence_are_kept():
    df = _results(
        _datapoint(
            "banana",
            {"Yellow": 1, "Blue": 0},
            privateMetadata={"source": "set-a"},
            confidencePerCategory={"Yellow": 0.7, "Blue": 0.3},
        )
    ).to_pandas()

    assert list(df["privateMetadata_source"]) == ["set-a", "set-a"]
    assert list(df["confidence"]) == [0.7, 0.3]


def test_datapoint_without_votes_has_no_ratio():
    datapoint = _datapoint("banana", {"Yellow": 0, "Blue": 0})
    datapoint["aggregatedResultsRatios"] = {}
    datapoint["summedUserScoresRatios"] = {}

    df = _results(datapoint).to_pandas()

    assert list(df["count"]) == [0, 0]
    assert df["ratio"].isna().all()


def test_split_details_still_gives_one_row_per_response():
    df = _results(_datapoint("A dog", {"Woof": 2, "Meow": 1})).to_pandas(
        split_details=True
    )

    assert list(df["selectedCategory"]) == ["Woof", "Woof", "Meow"]
