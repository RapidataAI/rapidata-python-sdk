from typing import TYPE_CHECKING, Any
from rapidata.rapidata_client.config import managed_print
import json

if TYPE_CHECKING:
    import pandas as pd
    from pandas.core.indexes.base import Index


class RapidataResults(dict):
    """
    A specialized dictionary class for handling Rapidata API results.
    Extends the built-in dict class with specialized methods.
    """

    def to_pandas(self, split_details: bool = False) -> "pd.DataFrame":
        """
        Warning:
            This method is currently under development. The structure of the results may change in the future.

        Converts the results to a pandas DataFrame.

        For Compare results (exactly 2 assets), creates standardized ``A_``/``B_``
        columns for each metric (plus ``Both_``/``Neither_`` when those options
        are present). For Ranking results with N assets, creates one
        ``<asset>_<metric>`` column per asset. For non-compare results, flattens
        nested dictionaries into columns with underscore-separated names.

        Args:
            split_details: If True, splits each datapoint by its detailed results,
                          creating a row for each response with global metrics copied.

        Returns:
            pd.DataFrame: A DataFrame containing the processed results

        Raises:
            ValueError: If split_details is True but no detailed results are found
        """
        import pandas as pd
        from pandas.core.indexes.base import Index

        if "results" not in self or not self["results"]:
            return pd.DataFrame()

        if self["info"].get("orderType") is None:
            managed_print(
                "Warning: Results are old and Order type is not specified. Dataframe might be wrong."
            )

        if split_details and not self._has_detailed_results():
            raise ValueError("No detailed results found in the data")

        # Compare/Ranking have an asset-aware shape; route them to the
        # compare-specific path even when split_details=True so we keep the
        # A_/B_ (or per-asset) column splitting.
        if self["info"].get("orderType") in ("Compare", "Ranking"):
            return self._compare_to_pandas(split_details=split_details)

        if split_details:
            return self._to_pandas_with_detailed_results()

        # Get the structure from first item
        first_item = self["results"][0]
        columns = []
        path_map = {}  # Maps flattened column names to paths to reach the values

        # Build the column structure once
        self._build_column_structure(first_item, columns, path_map)

        # Extract data using the known structure
        data = []
        for item in self["results"]:
            row = []
            for path in path_map.values():
                value = self._get_value_from_path(item, path)
                row.append(value)
            data.append(row)

        return pd.DataFrame(data, columns=Index(columns))

    def _has_detailed_results(self) -> bool:
        """
        Checks if the results contain detailed results.

        Returns:
            bool: True if detailed results exist, False otherwise
        """
        if not self.get("results"):
            return False

        first_result = self["results"][0]
        return "detailedResults" in first_result and isinstance(
            first_result["detailedResults"], list
        )

    def _to_pandas_with_detailed_results(self) -> "pd.DataFrame":
        """
        Converts results to a pandas DataFrame with detailed results split into separate rows.

        Returns:
            pd.DataFrame: A DataFrame with one row per detailed result
        """
        import pandas as pd

        rows = []

        for result in self["results"]:
            # Get all non-detailed results fields
            base_data = {k: v for k, v in result.items() if k != "detailedResults"}

            # Process each detailed result
            for detailed_result in result["detailedResults"]:
                row = base_data.copy()  # Copy base data for each detailed result

                # Add flattened detailed result data
                flattened = self._flatten_dict(detailed_result)
                for key, value in flattened.items():
                    row[key] = value

                rows.append(row)

        return pd.DataFrame(rows)

    def _flatten_dict(self, d: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
        """
        Flattens a nested dictionary into a single-level dictionary with underscore-separated keys.

        Args:
            d: The dictionary to flatten
            parent_key: The parent key for nested dictionaries

        Returns:
            dict: A flattened dictionary
        """
        items: list[tuple[str, Any]] = []

        for key, value in d.items():
            new_key = f"{parent_key}_{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key).items())
            else:
                items.append((new_key, value))

        return dict(items)

    def _build_column_structure(
        self,
        d: dict[str, Any],
        columns: list[str],
        path_map: dict[str, list[str]],
        parent_key: str = "",
        current_path: list[str] | None = None,
    ) -> None:
        """
        Builds the column structure and paths to reach values in nested dictionaries.

        Args:
            d: The dictionary to analyze
            columns: List to store column names
            path_map: Dictionary mapping column names to paths for accessing values
            parent_key: The parent key for nested dictionaries
            current_path: The current path in the dictionary structure
        """
        if current_path is None:
            current_path = []

        for key, value in d.items():
            new_key = f"{parent_key}_{key}" if parent_key else key
            new_path: list[str] = current_path + [key]

            if isinstance(value, dict):
                self._build_column_structure(
                    value, columns, path_map, new_key, new_path
                )
            else:
                columns.append(new_key)
                path_map[new_key] = new_path

    def _get_value_from_path(self, d: dict[str, Any], path: list[str]) -> Any:
        """
        Retrieves a value from a nested dictionary using a path list.

        Args:
            d: The dictionary to retrieve the value from
            path: List of keys forming the path to the desired value

        Returns:
            The value at the specified path, or None if the path doesn't exist
        """
        for key in path[:-1]:
            d = d.get(key, {})
        return d.get(path[-1])

    @staticmethod
    def _extract_compare_assets(result: dict[str, Any]) -> list[str]:
        """Return the ordered list of asset identifiers for a compare/ranking row.

        Prefers ``assetUrls`` when present (the canonical asset list emitted by
        the backend, never contaminated with ``Both``/``Neither``). Falls back
        to ``aggregatedResults`` (filtering ``Both``/``Neither``) for older
        payloads or text-asset compares that don't include ``assetUrls``.
        """
        excluded = {"Both", "Neither"}

        asset_urls = result.get("assetUrls")
        if isinstance(asset_urls, dict) and asset_urls:
            return [k for k in asset_urls.keys() if k not in excluded]

        aggregated = result.get("aggregatedResults")
        if isinstance(aggregated, dict) and aggregated:
            return [k for k in aggregated.keys() if k not in excluded]

        return []

    def _compare_to_pandas(self, split_details: bool = False) -> "pd.DataFrame":
        """Convert Compare/Ranking results to a pandas DataFrame.

        For Compare (exactly 2 assets), produces ``A_<metric>`` / ``B_<metric>``
        columns (plus ``Both_<metric>`` / ``Neither_<metric>`` when those
        options are present). For Ranking with N assets, produces one
        ``<asset>_<metric>`` column per asset.

        When ``split_details=True``, each datapoint is expanded to one row per
        ``detailedResults`` entry, with the asset/metric columns copied across
        and the per-response fields flattened in.
        """
        import pandas as pd

        if not self.get("results"):
            return pd.DataFrame()

        rows = []
        for result in self["results"]:
            assets = self._extract_compare_assets(result)
            if len(assets) < 2:
                continue

            is_compare = len(assets) == 2

            # Non-comparative fields. Skip dicts (asset metrics, handled below)
            # and lists (e.g. detailedResults — handled separately when
            # split_details=True, otherwise omitted from the tabular export).
            base_row: dict[str, Any] = {
                key: value
                for key, value in result.items()
                if not isinstance(value, (dict, list))
            }

            if is_compare:
                base_row["assetA"] = assets[0]
                base_row["assetB"] = assets[1]
            else:
                for i, asset in enumerate(assets):
                    base_row[f"asset_{i + 1}"] = asset

            # Per-metric asset columns. Only dicts that are actually keyed by
            # asset names count as comparative metrics — this skips fields
            # like ``privateMetadata``/``summary`` that happen to be dicts but
            # don't have per-asset values.
            asset_set = set(assets)
            for key, values in result.items():
                if not isinstance(values, dict) or not values:
                    continue
                if not asset_set.intersection(values.keys()):
                    continue
                if is_compare:
                    base_row[f"A_{key}"] = values.get(assets[0])
                    base_row[f"B_{key}"] = values.get(assets[1])
                    if "Both" in values:
                        base_row[f"Both_{key}"] = values["Both"]
                    if "Neither" in values:
                        base_row[f"Neither_{key}"] = values["Neither"]
                else:
                    for asset in assets:
                        base_row[f"{asset}_{key}"] = values.get(asset)

            detailed = result.get("detailedResults")
            if split_details and isinstance(detailed, list) and detailed:
                for detailed_result in detailed:
                    row = base_row.copy()
                    if isinstance(detailed_result, dict):
                        row.update(self._flatten_dict(detailed_result))
                    rows.append(row)
            else:
                rows.append(base_row)

        return pd.DataFrame(rows)

    def to_json(self, path: str = "./results.json") -> None:
        """
        Saves the results to a JSON file.

        Args:
            path: The file path where the JSON should be saved. Defaults to "./results.json".
        """
        with open(path, "w") as f:
            json.dump(self, f)
