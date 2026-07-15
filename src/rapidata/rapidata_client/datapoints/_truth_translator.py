from __future__ import annotations

from rapidata.api_client.models.i_validation_truth import IValidationTruth
from rapidata.api_client.models.i_validation_truth_compare_truth import (
    IValidationTruthCompareTruth,
)
from rapidata.api_client.models.i_validation_truth_multi_compare_truth import (
    IValidationTruthMultiCompareTruth,
)


def translate_compare_truth(
    truth: IValidationTruth | None,
    asset_to_uploaded: dict[str, str],
) -> IValidationTruth | None:
    """Rewrite compare-truth asset references from original paths/URLs to uploaded names.

    Compare truths are built before upload, so ``winnerId`` /
    ``correctCombinations`` reference assets by the caller-supplied path or
    URL, while the API expects uploaded asset names. Only call this for media
    rapids — text truths reference the text itself and must pass through
    unchanged. Raises ``ValueError`` if a referenced asset is not in the map,
    since sending the untranslated reference would silently break validation.
    """
    if truth is None or truth.actual_instance is None:
        return truth

    instance = truth.actual_instance

    if isinstance(instance, IValidationTruthCompareTruth):
        winner_id = instance.winner_id
        if winner_id not in asset_to_uploaded:
            raise ValueError(
                f"Compare truth winner '{winner_id}' is not one of the rapid's "
                f"assets: {list(asset_to_uploaded)}"
            )
        return IValidationTruth(
            actual_instance=IValidationTruthCompareTruth(
                _t="CompareTruth", winnerId=asset_to_uploaded[winner_id]
            )
        )

    if isinstance(instance, IValidationTruthMultiCompareTruth):
        translated_combinations: list[list[str]] = []
        for combination in instance.correct_combinations:
            translated_combination: list[str] = []
            for asset_id in combination:
                if asset_id not in asset_to_uploaded:
                    raise ValueError(
                        f"Multi-compare truth asset '{asset_id}' is not one of "
                        f"the rapid's assets: {list(asset_to_uploaded)}"
                    )
                translated_combination.append(asset_to_uploaded[asset_id])
            translated_combinations.append(translated_combination)
        return IValidationTruth(
            actual_instance=IValidationTruthMultiCompareTruth(
                _t="MultiCompareTruth", correctCombinations=translated_combinations
            )
        )

    return truth
