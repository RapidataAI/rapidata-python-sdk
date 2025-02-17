import pandas as pd

class RapidataResults(dict):
    def to_pandas(self) -> pd.DataFrame:
        """
        Converts the results to a pandas DataFrame, optimized for consistent structure.
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
            
        return pd.DataFrame(data, columns=columns)
    
    def _build_column_structure(self, d, columns, path_map, parent_key='', current_path=None):
        """
        Builds the column structure and paths to reach values.
        """
        if current_path is None:
            current_path = []
            
        for key, value in d.items():
            new_key = f"{parent_key}_{key}" if parent_key else key
            new_path = current_path + [key]
            
            if isinstance(value, dict):
                self._build_column_structure(value, columns, path_map, new_key, new_path)
            else:
                columns.append(new_key)
                path_map[new_key] = new_path
    
    def _get_value_from_path(self, d, path):
        """
        Gets a value from a dictionary using a path list.
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
