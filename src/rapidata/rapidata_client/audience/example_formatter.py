from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.query_examples_for_audience_endpoint_output import (
        QueryExamplesForAudienceEndpointOutput,
    )
    from rapidata.api_client.models.i_asset_model import IAssetModel
    from rapidata.api_client.models.i_example_truth import IExampleTruth


class ExampleFormatter:
    @staticmethod
    def format_to_csv_rows(
        items: list[QueryExamplesForAudienceEndpointOutput],
        asset_url_prefix: str,
    ) -> list[dict[str, str | None]]:
        rows = []
        for item in items:
            rows.append(
                {
                    "asset": ExampleFormatter._format_asset(
                        item.asset, asset_url_prefix
                    ),
                    "truth": ExampleFormatter._format_truth(item.truth),
                    "context": item.context,
                    "contextAsset": ExampleFormatter._format_asset(
                        item.context_asset, asset_url_prefix
                    ),
                }
            )
        return rows

    @staticmethod
    def _format_asset(asset: IAssetModel | None, asset_url_prefix: str) -> str | None:
        if asset is None or asset.actual_instance is None:
            return None

        from rapidata.api_client.models.i_asset_model_file_asset_model import (
            IAssetModelFileAssetModel,
        )
        from rapidata.api_client.models.i_asset_model_multi_asset_model import (
            IAssetModelMultiAssetModel,
        )
        from rapidata.api_client.models.i_asset_model_text_asset_model import (
            IAssetModelTextAssetModel,
        )

        instance = asset.actual_instance
        if isinstance(instance, IAssetModelFileAssetModel):
            return f"{asset_url_prefix}{instance.file_name}"
        if isinstance(instance, IAssetModelMultiAssetModel):
            return str(
                [
                    ExampleFormatter._format_asset(a, asset_url_prefix)
                    for a in instance.assets
                ]
            )
        if isinstance(instance, IAssetModelTextAssetModel):
            return instance.text
        return None

    @staticmethod
    def _format_truth(truth: IExampleTruth | None) -> str | None:
        if truth is None or truth.actual_instance is None:
            return None

        from rapidata.api_client.models.i_example_truth_classify_example_truth import (
            IExampleTruthClassifyExampleTruth,
        )
        from rapidata.api_client.models.i_example_truth_compare_example_truth import (
            IExampleTruthCompareExampleTruth,
        )

        instance = truth.actual_instance
        if isinstance(instance, IExampleTruthClassifyExampleTruth):
            return str(instance.correct_categories)
        if isinstance(instance, IExampleTruthCompareExampleTruth):
            return instance.winner_id
        return None
