"""Job definitions take ``UploadedAsset`` references, alone or mixed with paths and URLs."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rapidata.rapidata_client.datapoints.assets.uploaded_asset import UploadedAsset
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager

A = UploadedAsset("0b4a1f8e-a.png")
B = UploadedAsset("5c2d9e7f-b.png")


def _datapoints_sent(create_job_definition, **kwargs):
    manager = RapidataJobManager(MagicMock())
    with patch.object(manager, "_create_general_job_definition") as create:
        create_job_definition(
            manager, name="n", instruction="Which is better?", **kwargs
        )
    return create.call_args.kwargs["datapoints"]


def test_classification_accepts_references_and_paths() -> None:
    datapoints = _datapoints_sent(
        RapidataJobManager.create_classification_job_definition,
        answer_options=["Yes", "No"],
        datapoints=[A, "https://host/b.png"],
        media_contexts=[[B], ["ref.png"]],
    )

    assert [d.asset for d in datapoints] == [A, "https://host/b.png"]
    assert [d.media_context for d in datapoints] == [[B], ["ref.png"]]


def test_compare_accepts_reference_pairs() -> None:
    datapoints = _datapoints_sent(
        RapidataJobManager.create_compare_job_definition,
        datapoints=[[A, B], [A, "https://host/c.png"]],
    )

    assert [d.asset for d in datapoints] == [[A, B], [A, "https://host/c.png"]]


def test_compare_rejects_the_same_reference_twice() -> None:
    with pytest.raises(ValueError, match="exactly two unique options"):
        _datapoints_sent(
            RapidataJobManager.create_compare_job_definition,
            datapoints=[[A, UploadedAsset(A.name)]],
        )


def test_ranking_accepts_references_in_rankings_and_media_contexts() -> None:
    datapoints = _datapoints_sent(
        RapidataJobManager.create_ranking_job_definition,
        datapoints=[[A, B, "https://host/c.png"]],
        comparison_budget_per_ranking=3,
        media_contexts=[[B]],
    )

    assert [d.asset for d in datapoints] == [A, B, "https://host/c.png"]
    assert all(d.media_context == [B] for d in datapoints)
