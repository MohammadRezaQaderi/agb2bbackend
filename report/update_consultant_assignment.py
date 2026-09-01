"""
Update consultant assignments for students from Excel file.

This script reads student data from an Excel file and updates their consultant
assignments (con_id) in the database based on advisor names.
"""
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report.db_helper import get_db_connection, close_db_connection
from report.excel_helper import read_excel_file, write_excel_file, validate_excel_columns
from helper.response.password_response import build_display_password
from config import REPORT_OUTPUT_DIR


# Required Excel columns
REQUIRED_COLUMNS = ['نام', 'نام خانوادگی', 'مشاور']


def load_advisor_mapping(config_path: Optional[str] = None) -> Dict[str, int]:
    """
    Load advisor name to ID mapping.

    Args:
        config_path: Optional path to configuration file (future enhancement).

    Returns:
        Dictionary mapping advisor names to consultant IDs.
    """
    # Default mapping - can be moved to config file or database
    return {
        'آقای معاون افشار': 10657,
        'آقای اسلامیان': 10658,
        'آقای سید حسینی': 10659,
        'آقای موسوی': 10656,
        'آقای علی': 10655,
    }


def create_update_report_data(
    row: pd.Series,
    index: int,
    status: str,
    user_id: Optional[int] = None,
    phone: Optional[str] = None,
    password: Optional[str] = None,
    con_id: Optional[int] = None,
    previous_con_id: Optional[int] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a report entry for a consultant update attempt.

    Args:
        row: DataFrame row containing student data.
        index: Row index (0-based).
        status: Status of update ('Success', 'Error', 'Pending').
        user_id: Student user ID if found.
        phone: Student phone if found.
        password: Student password if found.
        con_id: New consultant ID.
        previous_con_id: Previous consultant ID.
        error_message: Error message if failed.

    Returns:
        Dictionary containing report data for the update.
    """
    return {
        'row_number': index + 2,  # Excel row number
        'first_name': str(row['نام']),
        'last_name': str(row['نام خانوادگی']),
        'advisor_name': str(row['مشاور']),
        'status': status,
        'user_id': user_id,
        'phone': phone,
        'password': password,
        'con_id': con_id,
        'previous_con_id': previous_con_id,
        'error_message': error_message,
    }


def find_student(
    cursor,
    first_name: str,
    last_name: str,
    user_id_min: int = 9883,
    user_id_max: int = 10646,
) -> Optional[Tuple[int, int, int, str, str]]:
    """
    Find a student in the database by name within a user_id range.

    Args:
        cursor: Database cursor.
        first_name: Student's first name.
        last_name: Student's last name.
        user_id_min: Minimum user_id to search.
        user_id_max: Maximum user_id to search.

    Returns:
        Tuple of (user_id, stu_id, current_con_id, phone, password) if found, None otherwise.
    """
    cursor.execute("""
        SELECT s.user_id, s.stu_id, s.consultant_user_id AS con_id, u.phone, u.password AS password
        FROM stu s
        INNER JOIN users u ON u.user_id = s.user_id
        WHERE s.user_id BETWEEN ? AND ? 
        AND s.first_name = ? 
        AND s.last_name = ?
    """, user_id_min, user_id_max, first_name, last_name)

    student = cursor.fetchone()
    if student:
        return student
    return None


def update_student_consultant(
    cursor,
    stu_id: int,
    con_id: int,
    editor_id: int = 7017,
) -> bool:
    """
    Update the consultant ID for a student.

    Args:
        cursor: Database cursor.
        stu_id: Student ID.
        con_id: New consultant ID.
        editor_id: User ID of the editor.

    Returns:
        True if successful, False otherwise.
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE stu
            SET consultant_user_id = ?, editor_id = ?, DC_Edited_Time = ?
            WHERE stu_id = ?
        """, con_id, editor_id, current_time, stu_id)
        return True
    except Exception as e:
        print(f"Database update error: {e}")
        return False


def process_student_update(
    row: pd.Series,
    index: int,
    cursor,
    advisor_mapping: Dict[str, int],
    user_id_min: int = 9883,
    user_id_max: int = 10646,
    editor_id: int = 7017,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Process a single student row for consultant update.

    Args:
        row: DataFrame row containing student data.
        index: Row index.
        cursor: Database cursor.
        advisor_mapping: Dictionary mapping advisor names to consultant IDs.
        user_id_min: Minimum user_id to search.
        user_id_max: Maximum user_id to search.
        editor_id: User ID of the editor.
        dry_run: If True, don't actually update the database.

    Returns:
        Report data dictionary for this update.
    """
    student_report = create_update_report_data(row, index, 'Pending')

    try:
        # Extract and validate data
        first_name = str(row['نام']).strip()
        last_name = str(row['نام خانوادگی']).strip()
        advisor_name = str(row['مشاور']).strip()

        if not first_name or not last_name:
            raise ValueError("First name or last name is empty")

        # Get advisor ID from mapping
        con_id = advisor_mapping.get(advisor_name)
        if con_id is None:
            raise ValueError(f"Advisor '{advisor_name}' not found in mapping")

        # Find the student
        student = find_student(cursor, first_name, last_name, user_id_min, user_id_max)

        if student is None:
            raise ValueError(f"Student not found in stu table (user_id {user_id_min}-{user_id_max})")

        user_id, stu_id, current_con_id, phone, password = student

        # Update the consultant ID
        if not dry_run:
            success = update_student_consultant(cursor, stu_id, con_id, editor_id)
            if not success:
                raise ValueError("Failed to update consultant ID in database")
        else:
            success = True

        if success:
            student_report.update({
                'status': 'Success',
                'user_id': user_id,
                'phone': phone,
                'password': build_display_password(password),
                'con_id': con_id,
                'previous_con_id': current_con_id,
            })
            print(
                f"✓ Successfully {'would update' if dry_run else 'updated'}: "
                f"{first_name} {last_name} - Phone: {phone} - "
                f"con_id: {current_con_id} -> {con_id}"
            )

    except Exception as e:
        error_msg = str(e)
        student_report.update({
            'status': 'Error',
            'error_message': error_msg,
        })
        print(f"✗ Error updating {first_name} {last_name}: {error_msg}")

    return student_report


def update_consultants_from_excel(
    excel_file_path: str,
    advisor_mapping: Optional[Dict[str, int]] = None,
    user_id_min: int = 9883,
    user_id_max: int = 10646,
    editor_id: int = 7017,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Update consultant assignments from Excel file.

    Args:
        excel_file_path: Path to the Excel file.
        advisor_mapping: Dictionary mapping advisor names to consultant IDs.
        user_id_min: Minimum user_id to search.
        user_id_max: Maximum user_id to search.
        editor_id: User ID of the editor.
        dry_run: If True, process but don't update database.

    Returns:
        Dictionary containing update summary and report data.
    """
    if advisor_mapping is None:
        advisor_mapping = load_advisor_mapping()

    # Read Excel file
    df = read_excel_file(excel_file_path)

    # Validate required columns
    if not validate_excel_columns(df, REQUIRED_COLUMNS):
        raise ValueError(f"Excel file must contain columns: {', '.join(REQUIRED_COLUMNS)}")

    total_rows = len(df)
    updated_count = 0
    error_count = 0
    report_data = []

    print(f"Starting {'DRY RUN - ' if dry_run else ''}consultant update process for {total_rows} students...")
    print(f"Searching user_id range: {user_id_min} - {user_id_max}")

    # Get database connection
    conn, cursor = get_db_connection()

    try:
        for index, row in df.iterrows():
            student_report = process_student_update(
                row=row,
                index=index,
                cursor=cursor,
                advisor_mapping=advisor_mapping,
                user_id_min=user_id_min,
                user_id_max=user_id_max,
                editor_id=editor_id,
                dry_run=dry_run,
            )

            if student_report['status'] == 'Success':
                updated_count += 1
            else:
                error_count += 1

            report_data.append(student_report)

        # Commit all updates
        if not dry_run:
            conn.commit()
            print(f"\n=== UPDATE SUMMARY ===")
        else:
            print(f"\n=== DRY RUN SUMMARY ===")
        print(f"Total rows processed: {total_rows}")
        print(f"Successfully {'processed' if dry_run else 'updated'}: {updated_count}")
        print(f"Errors encountered: {error_count}")
        if total_rows > 0:
            print(f"Success rate: {(updated_count / total_rows) * 100:.1f}%")

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        if not dry_run:
            conn.rollback()
        raise

    finally:
        close_db_connection(conn, cursor)

    # Generate report file
    report_filename = f"consultant_update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    report_file_path = os.path.join(REPORT_OUTPUT_DIR, report_filename)

    # Ensure output directory exists
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

    column_order = [
        'row_number', 'first_name', 'last_name', 'advisor_name', 'status',
        'user_id', 'phone', 'password', 'con_id', 'previous_con_id',
        'error_message'
    ]

    write_excel_file(report_data, report_file_path, column_order=column_order)

    print(f"\n=== FINAL REPORT ===")
    print(f"Detailed report saved to: {report_file_path}")
    print(f"Total records in Excel: {total_rows}")
    print(f"Successfully {'processed' if dry_run else 'updated'}: {updated_count}")
    print(f"Failed: {error_count}")

    return {
        'total_rows': total_rows,
        'updated_count': updated_count,
        'error_count': error_count,
        'report_file_path': report_file_path,
        'report_data': report_data,
        'dry_run': dry_run,
    }


def print_summary(result: Dict[str, Any]) -> None:
    """
    Print a detailed summary of the update process.

    Args:
        result: Result dictionary from update_consultants_from_excel.
    """
    print("\n" + "=" * 80)
    print("DETAILED SUMMARY")
    print("=" * 80)
    print(f"Excel File Rows: {result['total_rows']}")
    action = "Processed" if result.get('dry_run') else "Updated"
    print(f"Successfully {action}: {result['updated_count']}")
    print(f"Errors: {result['error_count']}")
    if result['total_rows'] > 0:
        print(f"Success Rate: {(result['updated_count'] / result['total_rows']) * 100:.1f}%")
    print(f"Report File: {result['report_file_path']}")

    # Show successful updates
    successes = [r for r in result['report_data'] if r['status'] == 'Success']
    if successes:
        print(f"\n✓ SUCCESSFUL UPDATES ({len(successes)} students):")
        print("-" * 80)
        for i, success in enumerate(successes[:10], 1):  # Show first 10
            print(f"  {i}. {success['first_name']} {success['last_name']}")
            print(f"     Phone: {success['phone']} | Password: {success['password']}")
            print(
                f"     Advisor: {success['advisor_name']} | "
                f"con_id: {success['previous_con_id']} → {success['con_id']}"
            )
            print()

        if len(successes) > 10:
            print(f"  ... and {len(successes) - 10} more successful updates")

    # Show errors
    errors = [r for r in result['report_data'] if r['status'] == 'Error']
    if errors:
        print(f"\n✗ ERRORS ({len(errors)} students):")
        print("-" * 80)
        for i, error in enumerate(errors[:5], 1):  # Show first 5 errors
            print(f"  {i}. {error['first_name']} {error['last_name']}: {error.get('error_message', 'Unknown error')}")

    # Print advisor distribution
    print(f"\n📊 ADVISOR DISTRIBUTION:")
    print("-" * 40)
    advisor_counts = {}
    for record in result['report_data']:
        if record['status'] == 'Success':
            advisor = record['advisor_name']
            advisor_counts[advisor] = advisor_counts.get(advisor, 0) + 1

    for advisor, count in advisor_counts.items():
        print(f"  {advisor}: {count} students")


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update consultant assignments from Excel file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python update_consultant_assignment.py --file stu_update.xlsx

  # Dry run (test without updating)
  python update_consultant_assignment.py --file stu_update.xlsx --dry-run

  # Custom user_id range
  python update_consultant_assignment.py --file stu_update.xlsx --user-id-min 9000 --user-id-max 11000
        """
    )

    parser.add_argument(
        '--file',
        type=str,
        required=True,
        help='Path to Excel file',
    )
    parser.add_argument(
        '--user-id-min',
        type=int,
        default=9883,
        help='Minimum user_id to search (default: 9883)',
    )
    parser.add_argument(
        '--user-id-max',
        type=int,
        default=10646,
        help='Maximum user_id to search (default: 10646)',
    )
    parser.add_argument(
        '--editor-id',
        type=int,
        default=7017,
        help='Editor user ID (default: 7017)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process without updating database',
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"✗ Error: Excel file '{args.file}' not found!")
        sys.exit(1)

    try:
        result = update_consultants_from_excel(
            excel_file_path=args.file,
            user_id_min=args.user_id_min,
            user_id_max=args.user_id_max,
            editor_id=args.editor_id,
            dry_run=args.dry_run,
        )
        print_summary(result)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
