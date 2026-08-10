"""
Excel helper utilities for Report scripts.

Provides functions for reading, writing, and formatting Excel files.
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path


def read_excel_file(file_path: str) -> pd.DataFrame:
    """
    Read an Excel file and return a DataFrame.

    Args:
        file_path: Path to the Excel file.

    Returns:
        DataFrame containing the Excel data.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file cannot be read.
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    try:
        return pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def write_excel_file(
    data: pd.DataFrame | List[Dict[str, Any]],
    output_path: str,
    column_order: Optional[List[str]] = None,
    index: bool = False,
) -> None:
    """
    Write data to an Excel file.

    Args:
        data: DataFrame or list of dictionaries to write.
        output_path: Path where the Excel file will be saved.
        column_order: Optional list of column names to reorder.
        index: Whether to include the DataFrame index.

    Raises:
        ValueError: If data cannot be written.
    """
    try:
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()

        # Reorder columns if specified
        if column_order:
            existing_columns = [col for col in column_order if col in df.columns]
            if existing_columns:
                df = df[existing_columns]

        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        df.to_excel(output_path, index=index, engine='openpyxl')
        print(f"✓ Report saved to: {output_path}")
    except Exception as e:
        raise ValueError(f"Error writing Excel file: {e}")


def validate_excel_columns(df: pd.DataFrame, required_columns: List[str]) -> bool:
    """
    Validate that required columns exist in the DataFrame.

    Args:
        df: DataFrame to validate.
        required_columns: List of required column names.

    Returns:
        True if all required columns exist, False otherwise.
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"✗ Missing required columns: {', '.join(missing_columns)}")
        return False
    return True


if __name__ == "__main__":
    """Test Excel helper functions."""
    print("Excel helper module loaded successfully!")
    print("Available functions:")
    print("  - read_excel_file(file_path)")
    print("  - write_excel_file(data, output_path, column_order=None)")
    print("  - validate_excel_columns(df, required_columns)")

