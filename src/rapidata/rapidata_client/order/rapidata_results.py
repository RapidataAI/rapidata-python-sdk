import pandas as pd
from typing import Any
from pandas.core.indexes.base import Index
import json
from rapidata.rapidata_client.logging import managed_print

class RapidataResults(dict):
    """
    A specialized dictionary class for handling Rapidata API results.
    Extends the built-in dict class with specialized methods.
    """
    def to_pandas(self, split_details: bool = False) -> pd.DataFrame:
        """
        Warning:
            This method is currently under development. The structure of the results may change in the future.

        Converts the results to a pandas DataFrame.
        
        For Compare results, creates standardized A/B columns for metrics.
        For regular results, flattens nested dictionaries into columns with underscore-separated names.
        
        Args:
            split_details: If True, splits each datapoint by its detailed results,
                          creating a row for each response with global metrics copied.
                          
        Returns:
            pd.DataFrame: A DataFrame containing the processed results
            
        Raises:
            ValueError: If split_details is True but no detailed results are found
        """
        if "results" not in self or not self["results"]:
            return pd.DataFrame()
        
        if self["info"].get("orderType") is None:
            managed_print("Warning: Results are old and Order type is not specified. Dataframe might be wrong.")
        
        # Check for detailed results if split_details is True
        if split_details:
            if not self._has_detailed_results():
                raise ValueError("No detailed results found in the data")
            return self._to_pandas_with_detailed_results()
            
        if self["info"].get("orderType") == "Compare" or self["info"].get("orderType") == "Ranking":
            return self._compare_to_pandas()
        
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
        return "detailedResults" in first_result and isinstance(first_result["detailedResults"], list)
    
    def _to_pandas_with_detailed_results(self) -> pd.DataFrame:
        """
        Converts results to a pandas DataFrame with detailed results split into separate rows.
        
        Returns:
            pd.DataFrame: A DataFrame with one row per detailed result
        """
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
    
    def _flatten_dict(self, d: dict[str, Any], parent_key: str = '') -> dict[str, Any]:
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
        parent_key: str = '', 
        current_path: list[str] | None = None
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
                self._build_column_structure(value, columns, path_map, new_key, new_path)
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

    def _compare_to_pandas(self) -> pd.DataFrame:
        """
        Converts Compare results to a pandas DataFrame dynamically.
        """
        if not self.get("results"):
            return pd.DataFrame()

        rows = []
        for result in self["results"]:
            # Get all asset names from the first metric we find
            assets = []
            for key in result:
                if isinstance(result[key], dict) and len(result[key]) >= 2:
                    assets = list(result[key].keys())
                    break
            else:
                continue

            assets = [asset for asset in assets if asset not in ["Both", "Neither"]]
            
            # Initialize row with non-comparative fields
            row = {
                key: value for key, value in result.items() 
                if not isinstance(value, dict)
            }
            row["assetA"] = assets[0]
            row["assetB"] = assets[1]

            # Handle comparative metrics
            for key, values in result.items():
                if isinstance(values, dict) and len(values) >= 2:
                    # Add main asset columns
                    for i, asset in enumerate(assets[:2]):  # Limit to first 2 main assets
                        column_prefix = "A_" if i == 0 else "B_"
                        row[f'{column_prefix}{key}'] = values.get(asset, 0)
                    
                    # Add special option columns if they exist
                    if "Both" in values:
                        row[f'Both_{key}'] = values.get("Both", 0)
                    if "Neither" in values:
                        row[f'Neither_{key}'] = values.get("Neither", 0)
                        
            rows.append(row)
            
        return pd.DataFrame(rows)

    def to_json(self, path: str="./results.json") -> None:
        """
        Saves the results to a JSON file.
        
        Args:
            path: The file path where the JSON should be saved. Defaults to "./results.json".
        """
        with open(path, 'w') as f:
            json.dump(self, f)
