from __future__ import annotations

from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.api_client.models.i_asset_input_text_asset_input import (
    IAssetInputTextAssetInput,
)
from rapidata.api_client.models.i_asset_input_existing_asset_input import (
    IAssetInputExistingAssetInput,
)
from rapidata.api_client.models.i_asset_input_multi_asset_input import (
    IAssetInputMultiAssetInput,
)


class AssetMapper:
    """Maps asset data to IAssetInput API models.

    This class handles the conversion of raw text or uploaded asset names
    into the appropriate IAssetInput model structures. It does NOT handle
    uploading - use AssetUploader for that.
    """

    @staticmethod
    def create_text_input(assets: list[str] | str) -> IAssetInput:
        """Create an IAssetInput from text content.

        Args:
            assets: Text content as a single string or list of strings.

        Returns:
            IAssetInput wrapping TextAssetInput (or MultiAssetInput for lists).
        """
        if isinstance(assets, list):
            return IAssetInput(
                actual_instance=IAssetInputMultiAssetInput(
                    _t="MultiAssetInput",
                    assets=[
                        IAssetInput(
                            actual_instance=IAssetInputTextAssetInput(
                                _t="TextAssetInput", text=asset
                            )
                        )
                        for asset in assets
                    ],
                )
            )
        else:
            return IAssetInput(
                actual_instance=IAssetInputTextAssetInput(
                    _t="TextAssetInput", text=assets
                )
            )

    @staticmethod
    def create_existing_asset_input(uploaded_names: list[str] | str) -> IAssetInput:
        """Create an IAssetInput from already-uploaded asset names.

        Args:
            uploaded_names: Asset name(s) returned from AssetUploader.upload_asset().

        Returns:
            IAssetInput wrapping ExistingAssetInput (or MultiAssetInput for lists).
        """
        if isinstance(uploaded_names, list):
            return IAssetInput(
                actual_instance=IAssetInputMultiAssetInput(
                    _t="MultiAssetInput",
                    assets=[
                        IAssetInput(
                            actual_instance=IAssetInputExistingAssetInput(
                                _t="ExistingAssetInput",
                                name=name,
                            )
                        )
                        for name in uploaded_names
                    ],
                )
            )
        else:
            return IAssetInput(
                actual_instance=IAssetInputExistingAssetInput(
                    _t="ExistingAssetInput",
                    name=uploaded_names,
                )
            )
