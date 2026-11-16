"""Ranking results nest one entry per ranking, with its matchups under ``results``."""

from __future__ import annotations

from rapidata.rapidata_client.results.rapidata_results import RapidataResults


def _matchup(a: str, b: str, winner: str) -> dict:
    return {
        "winner": winner,
        "winnerIndex": [a, b].index(winner),
        "assetUrls": {a: f"https://assets/{a}", b: f"https://assets/{b}"},
        "aggregatedResults": {a: int(winner == a), b: int(winner == b)},
        "summedUserScores": {a: 0.8 * (winner == a), b: 0.8 * (winner == b)},
        "detailedResults": [
            {"votedFor": winner, "userDetails": {"country": "CH"}},
        ],
    }


def _results() -> RapidataResults:
    return RapidataResults(
        {
            "info": {"type": "Ranking"},
            "results": [
                {
                    "group": "0",
                    "context": "rabbits",
                    "summary": {"r1.jpg": 1200, "r3.jpg": 1335, "r2.jpg": 1064},
                    "results": [
                        _matchup("r1.jpg", "r3.jpg", "r3.jpg"),
                        _matchup("r2.jpg", "r1.jpg", "r1.jpg"),
                    ],
                },
                {
                    "group": "1",
                    "summary": {"c1.jpg": 1180, "c2.jpg": 1220},
                    "results": [_matchup("c1.jpg", "c2.jpg", "c2.jpg")],
                },
            ],
        }
    )


def test_one_row_per_ranked_datapoint_best_first():
    df = _results().to_pandas()

    assert list(zip(df["group"], df["datapoint"], df["score"], df["rank"])) == [
        ("0", "r3.jpg", 1335, 1),
        ("0", "r1.jpg", 1200, 2),
        ("0", "r2.jpg", 1064, 3),
        ("1", "c2.jpg", 1220, 1),
        ("1", "c1.jpg", 1180, 2),
    ]
    assert df.loc[0, "context"] == "rabbits"


def test_split_details_gives_one_row_per_matchup_response():
    df = _results().to_pandas(split_details=True)

    assert list(df["group"]) == ["0", "0", "1"]
    assert list(df["assetA"]) == ["r1.jpg", "r2.jpg", "c1.jpg"]
    assert list(df["votedFor"]) == ["r3.jpg", "r1.jpg", "c2.jpg"]
    assert list(df["B_aggregatedResults"]) == [1, 1, 1]
