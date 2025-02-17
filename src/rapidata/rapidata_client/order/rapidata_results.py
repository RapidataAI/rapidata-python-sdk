import pandas as pd
from typing import Any
from pandas.core.indexes.base import Index
import json

class RapidataResults(dict):
    """
    A specialized dictionary class for handling Rapidata API results.
    Extends the built-in dict class with specialized methods.
    """
    def to_pandas(self) -> pd.DataFrame:
        """
        Converts the results to a pandas DataFrame.
        
        For Compare results, creates standardized A/B columns for metrics like:
        - aggregatedResults
        - aggregatedResultsRatios
        - summedUserScores
        - summedUserScoresRatios
        
        For regular results, flattens nested dictionaries into columns with underscore-separated names.
        
        Returns:
            pd.DataFrame: A DataFrame containing the processed results
        """
        if "results" not in self or not self["results"]:
            return pd.DataFrame()
        
        if self["info"].get("orderType") == "Compare":
            return self._compare_to_pandas()
        
        if self["info"].get("orderType") is None:
            print("Warning: Results are old and Order type is not specified. Dataframe might be wrong.")

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

    def _compare_to_pandas(self):
        """
        Converts Compare results to a pandas DataFrame dynamically.
        """
        if not self.get("results"):
            return pd.DataFrame()

        rows = []
        for result in self["results"]:
            # Get the image names from the first metric we find
            for key in result:
                if isinstance(result[key], dict) and len(result[key]) == 2:
                    assets = list(result[key].keys())
                    break
            else:
                continue

            asset_a, asset_b = assets[0], assets[1]
            
            # Initialize row with non-comparative fields
            row = {
                key: value for key, value in result.items() 
                if not isinstance(value, dict)
            }
            
            # Handle comparative metrics
            for key, values in result.items():
                if isinstance(values, dict) and len(values) == 2:
                    row[f'A_{key}'] = values[asset_a]
                    row[f'B_{key}'] = values[asset_b]
                    
            rows.append(row)
            
        return pd.DataFrame(rows)

    def to_json(self, path: str="./results.json"):
        """
        Saves the results to a JSON file.
        
        Args:
            path: The file path where the JSON should be saved. Defaults to "./results.json".
        """
        with open(path, 'w') as f:
            json.dump(self, f)
