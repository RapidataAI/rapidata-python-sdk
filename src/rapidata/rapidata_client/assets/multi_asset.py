"""Multi Asset Module

Defines the MultiAsset class for handling multiple BaseAsset instances.
"""

from rapidata.rapidata_client.assets.base_asset import BaseAsset
from typing import Iterator, List


class MultiAsset(BaseAsset):
    """MultiAsset Class

    Represents a collection of multiple BaseAsset instances.

    Args:
        assets (List[BaseAsset]): A list of BaseAsset instances to be managed together.
    """

    def __init__(self, assets: list[BaseAsset]):
        """
        Initialize a MultiAsset instance.

        Args:
            assets (List[BaseAsset]): A list of BaseAsset instances to be managed together.
        """
        self.assets = assets

    def __len__(self) -> int:
        """
        Get the number of assets in the MultiAsset.

        Returns:
            int: The number of assets.
        """
        return len(self.assets)

    def __iter__(self) -> Iterator[BaseAsset]:
        """
        Return an iterator over the assets in the MultiAsset.

        Returns:
            Iterator[BaseAsset]: An iterator over the assets.
        """
        return iter(self.assets)
