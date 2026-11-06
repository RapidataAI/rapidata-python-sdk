from __future__ import annotations

import math

import pytest

from rapidata.rapidata_client.referee._adaptive_stopping_compat import (
    normalise_adaptive_stopping_config,
)


DEFAULTS = {
    "maxVotes": 100,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
    "unsolvableThreshold": 0.5,
    "maxOutcomeCount": 1,
}


@pytest.mark.parametrize(
    "discriminator",
    [
        "AdaptiveStoppingReferee",
        "AdaptiveStoppingRefereeConfig",
        "AdaptiveStoppingRefereeInfo",
    ],
)
def test_read_normalization_preserves_discriminator_and_resolves_all_five_defaults(
    discriminator,
):
    original = {"_t": discriminator}

    assert normalise_adaptive_stopping_config(original) == {
        "_t": discriminator,
        **DEFAULTS,
    }
    assert original == {"_t": discriminator}


def test_all_nondefault_settings_are_retained():
    original = {
        "_t": "AdaptiveStoppingRefereeConfig",
        "maxVotes": 47,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.73,
        "unsolvableThreshold": 0.6,
        "maxOutcomeCount": 3,
    }
    assert normalise_adaptive_stopping_config(original) == original


@pytest.mark.parametrize(
    "legacy_range, threshold", [(0.6, 0.64), (0.5, 0.75), (0.3, 0.91)]
)
def test_legacy_range_is_converted_without_mutating_the_input(legacy_range, threshold):
    original = {"_t": "AdaptiveStoppingRefereeConfig", "ambiguityRange": legacy_range}

    canonical = normalise_adaptive_stopping_config(original)

    assert canonical == {
        "_t": "AdaptiveStoppingRefereeConfig",
        **DEFAULTS,
        "ambiguityThreshold": pytest.approx(threshold),
    }
    assert original["ambiguityRange"] == legacy_range
    assert "ambiguityRange" not in canonical


@pytest.mark.parametrize("value", [0, 1, True, None, math.nan, math.inf, "0.6"])
def test_invalid_legacy_range_does_not_silently_become_a_default(value):
    with pytest.raises(ValueError, match="ambiguityRange"):
        normalise_adaptive_stopping_config({"ambiguityRange": value})


def test_canonical_threshold_takes_precedence_and_legacy_field_is_not_emitted():
    canonical = normalise_adaptive_stopping_config(
        {"ambiguityThreshold": 0.8, "ambiguityRange": 0.6}
    )
    assert canonical == {**DEFAULTS, "ambiguityThreshold": 0.8}


def test_explicit_null_is_left_for_model_validation_instead_of_defaulted():
    canonical = normalise_adaptive_stopping_config({"unsolvableThreshold": None})
    assert canonical["unsolvableThreshold"] is None
