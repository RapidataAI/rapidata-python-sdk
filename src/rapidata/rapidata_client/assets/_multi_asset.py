"""Multi Asset Module

Defines the MultiAsset class for handling multiple BaseAsset instances.
"""

from rapidata.rapidata_client.assets._base_asset import BaseAsset
from rapidata.rapidata_client.assets import MediaAsset, TextAsset
from typing import Iterator, Sequence


class MultiAsset(BaseAsset):
    """MultiAsset Class

    Represents a collection of multiple BaseAsset instances.

    Args:
        assets (List[BaseAsset]): A list of BaseAsset instances to be managed together.
    """

    def __init__(self, assets: Sequence[BaseAsset]) -> None:
        """
        Initialize a MultiAsset instance.

        Args:
            assets (List[BaseAsset]): A list of BaseAsset instances to be managed together.
        """
        if len(assets) != 2:
            raise ValueError("Assets must come in pairs for comparison tasks.")
        
        for asset in assets:
            if not isinstance(asset, (TextAsset, MediaAsset)):
                raise TypeError("All assets must be a TextAsset or MediaAsset.")    
        
        if not all(isinstance(asset, type(assets[0])) for asset in assets):
            raise ValueError("All assets must be of the same type.")
        
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
