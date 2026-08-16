"""
Student information export to Excel.

This script exports student information from the database to Excel files.
Supports custom column selection and filtering by institution ID.
"""
import os
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report.db_helper import get_db_connection, close_db_connection
from report.excel_helper import write_excel_file
from config import REPORT_OUTPUT_DIR, REPORT_DEFAULT_INS_ID


# Available column mappings
COLUMN_MAPPING: Dict[str, str] = {
    'first_name': 's.first_name',
    'last_name': 's.last_name',
    'phone': 'u.phone',
    'password': 'CAST(NULL AS NVARCHAR(255)) as password',
    'gender': """
        CASE 
            WHEN s.sex = 1 THEN 'پسر'
            WHEN s.sex = 2 THEN 'دختر'
            ELSE 'نامشخص'
        END as gender
    """,
    'birth_date': 's.birth_date',
    'city': 's.city',
    'user_id': 's.user_id',
    'stu_id': 's.stu_id',
    'created_date': 's.created_time',
}


def get_students_by_ins_id(
    ins_id: int,
    columns: Optional[List[str]] = None,
) -> Optional[pd.DataFrame]:
    """
    Get students by institution ID with customizable columns.

    Args:
        ins_id: Institution ID to filter by.
        columns: List of column names to include. If None, uses default columns.

    Returns:
        DataFrame containing student data, or None if error occurs.
    """
    if columns is None:
        columns = ['first_name', 'last_name', 'phone', 'password']

    # Build SELECT clause
    select_columns = []
    for col in columns:
        if col in COLUMN_MAPPING:
            select_columns.append(COLUMN_MAPPING[col])
        else:
            # Allow custom SQL expressions
            select_columns.append(col)

    select_clause = ", ".join(select_columns)

    conn, cursor = get_db_connection()

    try:
        query = f"""
        SELECT {select_clause}
        FROM stu s
        INNER JOIN users u ON u.user_id = s.user_id
        WHERE s.ins_id = ?
        ORDER BY s.first_name, s.last_name
        """

        cursor.execute(query, ins_id)
        students = cursor.fetchall()

        if not students:
            print(f"No students found for ins_id={ins_id}")
            return pd.DataFrame()

        # Get column names from cursor description
        column_names = [desc[0] for desc in cursor.description]

        df = pd.DataFrame.from_records(students, columns=column_names)
        return df

    except Exception as e:
        print(f"✗ Error querying students: {e}")
        return None

    finally:
        close_db_connection(conn, cursor)


def export_students_to_excel(
    ins_id: int,
    output_file_path: str,
    columns: Optional[List[str]] = None,
) -> bool:
    """
    Export students to an Excel file.

    Args:
        ins_id: Institution ID to filter by.
        output_file_path: Path where the Excel file will be saved.
        columns: List of column names to include.

    Returns:
        True if successful, False otherwise.
    """
    print(f"🔄 Exporting students with ins_id={ins_id}...")

    df = get_students_by_ins_id(ins_id, columns)

    if df is None:
        print("✗ Failed to retrieve student data")
        return False

    if len(df) == 0:
        print("✗ No students found")
        return False

    try:
        write_excel_file(df, output_file_path, column_order=columns)
        print(f"✅ Successfully exported {len(df)} students to: {output_file_path}")
        print(f"📊 Columns: {', '.join(df.columns.tolist())}")

        # Show preview
        print(f"\n📋 PREVIEW (first 10 rows):")
        print(df.head(10).to_string(index=False))
        return True

    except Exception as e:
        print(f"✗ Error writing Excel file: {e}")
        return False


def export_custom_student_report() -> None:
    """
    Interactive function to export custom student reports.
    """
    print("🎯 Custom Student Export Tool")
    print("=" * 40)

    # Get institution ID
    ins_id_input = input(f"Enter institution ID (default: {REPORT_DEFAULT_INS_ID}): ").strip()
    ins_id = int(ins_id_input) if ins_id_input else REPORT_DEFAULT_INS_ID

    # Available columns
    available_columns = list(COLUMN_MAPPING.keys())

    print("\nAvailable columns:")
    for i, col in enumerate(available_columns, 1):
        print(f"  {i}. {col}")

    # Get column selection
    selected_indices = input(
        "\nEnter column numbers (comma-separated, default: 1,2,3,4 for basic info): "
    ).strip()

    if selected_indices:
        try:
            indices = [int(x.strip()) for x in selected_indices.split(',')]
            selected_columns = [
                available_columns[i - 1]
                for i in indices
                if 1 <= i <= len(available_columns)
            ]
        except ValueError:
            print("Invalid input, using default columns")
            selected_columns = ['first_name', 'last_name', 'phone', 'password']
    else:
        selected_columns = ['first_name', 'last_name', 'phone', 'password']

    # Get output file name
    output_file = input("Enter output file name (default: students_export.xlsx): ").strip()
    output_file = output_file if output_file else "students_export.xlsx"

    if not output_file.endswith('.xlsx'):
        output_file += '.xlsx'

    # Ensure output directory exists
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(REPORT_OUTPUT_DIR, output_file)

    # Export data
    success = export_students_to_excel(ins_id, output_path, selected_columns)

    if not success:
        print("❌ Export failed")


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export student information to Excel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic export with default settings
  python select_student_info.py

  # Export with custom institution ID
  python select_student_info.py --ins-id 7017

  # Export specific columns
  python select_student_info.py --columns first_name last_name phone password

  # Interactive mode
  python select_student_info.py --interactive
        """
    )

    parser.add_argument(
        '--ins-id',
        type=int,
        default=REPORT_DEFAULT_INS_ID,
        help=f'Institution ID (default: {REPORT_DEFAULT_INS_ID})',
    )
    parser.add_argument(
        '--columns',
        nargs='+',
        default=None,
        help='Columns to export (default: first_name, last_name, phone, password)',
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path (default: auto-generated)',
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode',
    )

    args = parser.parse_args()

    if args.interactive:
        export_custom_student_report()
        return

    # Generate output filename if not provided
    if args.output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"students_export_{args.ins_id}_{timestamp}.xlsx"
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(REPORT_OUTPUT_DIR, output_filename)
    else:
        output_path = args.output

    success = export_students_to_excel(
        ins_id=args.ins_id,
        output_file_path=output_path,
        columns=args.columns,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
