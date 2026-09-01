"""
Student insertion from Excel file with capacity validation.

This script reads student data from an Excel file and inserts them into the database.
It validates available capacity before insertion and generates a detailed report.
"""
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import helper.func_helper as func_helper
from report.db_helper import get_db_connection, close_db_connection
from report.excel_helper import read_excel_file, write_excel_file, validate_excel_columns
from config import REPORT_OUTPUT_DIR, REPORT_DEFAULT_INS_ID, REPORT_DEFAULT_CON_ID

REQUIRED_COLUMNS = ['نام', 'نام خانوادگی', 'جنسیت', 'استان', 'سال تولد']


class CapacityValidator:
    """Handles capacity validation for student insertion."""

    def __init__(self, conn, cursor, ins_id: int):
        self.conn = conn
        self.cursor = cursor
        self.ins_id = ins_id
        self._capacity_cache = None

    def get_capacity_info(self) -> Optional[Dict[str, Any]]:
        """
        Get capacity information for the institution.

        Returns:
            Dictionary with capacity info or None if not found.
        """
        try:
            self.cursor.execute("""
                SELECT capacity_id, user_id
                FROM capacity 
                WHERE user_id = ?
            """, self.ins_id)

            capacity = self.cursor.fetchone()
            if not capacity:
                return None

            self.cursor.execute("""
                SELECT capacity_package_id, package_name, allowed, used
                FROM capacity_package 
                WHERE capacity_id = ? and package_name = 'AG'
            """, capacity[0])

            packages = self.cursor.fetchall()

            return {
                'capacity_id': capacity[0],
                'user_id': capacity[1],
                'packages': [
                    {
                        'package_id': p[0],
                        'package_name': p[1],
                        'allowed': p[2],
                        'used': p[3]
                    } for p in packages
                ],
                'total_allowed': sum(p[2] for p in packages),
                'total_used': sum(p[3] for p in packages),
                'remaining': sum(p[2] - p[3] for p in packages)
            }
        except Exception as e:
            print(f"Error getting capacity info: {e}")
            return None

    def check_available_capacity(self, requested_count: int) -> Tuple[bool, int, str]:
        """
        Check if there's enough capacity for the requested number of students.

        Args:
            requested_count: Number of students to insert.

        Returns:
            Tuple of (is_available, available_count, message).
        """
        capacity_info = self.get_capacity_info()

        if not capacity_info:
            return False, 0, f"No capacity record found for institution ID: {self.ins_id}"

        remaining = capacity_info['remaining']

        if requested_count <= remaining:
            return True, remaining, f"Sufficient capacity available. Requested: {requested_count}, Available: {remaining}"
        else:
            return False, remaining, f"Insufficient capacity. Requested: {requested_count}, Available: {remaining}"

    def update_capacity_usage(self, used_count: int) -> bool:
        """
        Update capacity usage after successful insertions.

        Args:
            used_count: Number of students successfully inserted.

        Returns:
            True if update successful, False otherwise.
        """
        try:
            capacity_info = self.get_capacity_info()
            if not capacity_info:
                return False

            remaining_to_update = used_count

            for package in capacity_info['packages']:
                if remaining_to_update <= 0:
                    break

                package_id = package['package_id']
                current_used = package['used']
                allowed = package['allowed']
                available_in_package = allowed - current_used

                update_amount = min(remaining_to_update, available_in_package)

                if update_amount > 0:
                    self.cursor.execute("""
                        UPDATE capacity_package 
                        SET used = used + ?,
                            edited_time = GETDATE()
                        WHERE capacity_package_id = ? and  and package_name = 'AG'
                    """, update_amount, package_id)

                    remaining_to_update -= update_amount

            return True

        except Exception as e:
            print(f"Error updating capacity usage: {e}")
            return False


def create_student_report_data(
        row: pd.Series,
        index: int,
        status: str,
        user_id: Optional[int] = None,
        phone: Optional[str] = None,
        password: Optional[str] = None,
        error_message: Optional[str] = None,
        province_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a report entry for a student insertion attempt.

    Args:
        row: DataFrame row containing student data.
        index: Row index (0-based).
        status: Status of insertion ('Success', 'Error', 'Pending').
        user_id: Generated user ID if successful.
        phone: Generated phone number if successful.
        password: Generated password if successful.
        error_message: Error message if failed.
        province_id: Processed province ID.

    Returns:
        Dictionary containing report data for the student.
    """
    return {
        'row_number': index + 2,
        'first_name': str(row['نام']),
        'last_name': str(row['نام خانوادگی']),
        'original_province': str(row['استان']),
        'status': status,
        'user_id': user_id,
        'phone': phone,
        'password': password,
        'error_message': error_message,
        'processed_province_id': province_id,
    }


def process_province(province_name: str) -> Tuple[int, bool]:
    """
    Process province name and return province ID.

    Args:
        province_name: Name of the province.

    Returns:
        Tuple of (province_id, found_in_list).
    """
    province_name = province_name.strip()
    province = next((p for p in func_helper.PROVINCES if p["name"] == province_name), None)

    if province:
        return province["id"], True
    else:
        # Default to Tehran (id: 8) if not found
        print(f"Warning: Province '{province_name}' not found, using default (تهران)")
        return 8, False


def validate_student_data(row: pd.Series) -> Tuple[bool, Dict[str, Any], str]:
    """
    Validate a single student row data.

    Args:
        row: DataFrame row containing student data.

    Returns:
        Tuple of (is_valid, extracted_data, error_message).
    """
    extracted_data = {}

    try:
        first_name = str(row['نام']).strip()
        if not first_name:
            return False, extracted_data, "First name is empty"
        extracted_data['first_name'] = first_name

        last_name = str(row['نام خانوادگی']).strip()
        if not last_name:
            return False, extracted_data, "Last name is empty"
        extracted_data['last_name'] = last_name

        gender_str = str(row['جنسیت']).strip()
        if gender_str not in ['مرد', 'زن']:
            return False, extracted_data, f"Invalid gender: {gender_str}. Must be 'مرد' or 'زن'"
        extracted_data['sex'] = 1 if gender_str == 'مرد' else 2

        province_name = str(row['استان']).strip()
        if not province_name:
            return False, extracted_data, "Province is empty"
        extracted_data['province_name'] = province_name

        birth_date = str(row['سال تولد']).strip()
        if birth_date and len(birth_date) >= 4:
            birth_year = birth_date[:4]
            if birth_year.isdigit() and 1300 <= int(birth_year) <= 1405:
                extracted_data['birth_date'] = birth_year
            else:
                extracted_data['birth_date'] = '1389'
                print(f"Warning: Invalid birth year '{birth_year}', using default '1389'")
        else:
            extracted_data['birth_date'] = '1389'
            print(f"Warning: Missing birth date, using default '1389'")

        return True, extracted_data, ""

    except Exception as e:
        return False, extracted_data, f"Validation error: {str(e)}"


def insert_student_to_db(
        conn,
        cursor,
        first_name: str,
        last_name: str,
        sex: int,
        province_id: int,
        birth_date: str,
        phone: str,
        password: str,
        ins_id: int,
        con_id: int,
        adder_id: int,
) -> Optional[int]:
    """
    Insert a student into the database.

    Args:
        conn: Database connection.
        cursor: Database cursor.
        first_name: Student's first name.
        last_name: Student's last name.
        sex: Student's gender (1=male, 2=female).
        province_id: Province ID.
        birth_date: Birth year (4 digits).
        phone: Generated phone number.
        password: Generated password.
        ins_id: Institution ID.
        con_id: Consultant ID.
        adder_id: User ID who added the student.

    Returns:
        User ID if successful, None otherwise.
    """
    try:
        province = next((p for p in func_helper.PROVINCES if p["id"] == province_id), None)
        city_str = f"{province_id},{province['name']}" if province else f"{province_id},تهران"

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO users (phone, password, role, created_time, edited_time)
            OUTPUT INSERTED.user_id
            VALUES (?, ?, ?, ?, ?)
        """, phone, password, 'stu', current_time, current_time)

        user_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO stu (user_id, first_name, last_name, sex,
                            city, owner_user_id, consultant_user_id, adder_id,
                            editor_id, comment, birth_date,
                            created_time, edited_time, access)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
                       user_id, first_name, last_name, sex,
                       city_str, ins_id, con_id, adder_id, adder_id,
                       None, birth_date,
                       current_time, current_time, '{"AG": {"permission": 1, "limit": 0}}')

        return user_id
    except Exception as e:
        print(f"Database insertion error: {e}")
        return None


def process_student_row(
        row: pd.Series,
        index: int,
        conn,
        cursor,
        ins_id: int,
        con_id: int,
        dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Process a single student row from the Excel file.

    Args:
        row: DataFrame row containing student data.
        index: Row index.
        conn: Database connection.
        cursor: Database cursor.
        ins_id: Institution ID to assign.
        con_id: Consultant ID to assign.
        dry_run: If True, don't actually insert into database.

    Returns:
        Report data dictionary for this student.
    """
    student_report = create_student_report_data(row, index, 'Pending')

    try:
        is_valid, extracted_data, error_msg = validate_student_data(row)

        if not is_valid:
            raise ValueError(error_msg)

        first_name = extracted_data['first_name']
        last_name = extracted_data['last_name']
        sex = extracted_data['sex']
        province_name = extracted_data['province_name']
        birth_date = extracted_data['birth_date']

        province_id, province_found = process_province(province_name)
        student_report['processed_province_id'] = province_id

        phone = func_helper.random_generate_phone(8)
        plain_password = func_helper.random_generate_password()
        encrypted_password = func_helper.encrypt_password(plain_password)

        print(f"Processing: {first_name} {last_name} - Phone: {phone}")

        user_id = None
        if not dry_run:
            user_id = insert_student_to_db(
                conn=conn,
                cursor=cursor,
                first_name=first_name,
                last_name=last_name,
                sex=sex,
                province_id=province_id,
                birth_date=birth_date,
                phone=phone,
                password=encrypted_password,
                ins_id=ins_id,
                con_id=con_id,
                adder_id=ins_id,
            )

        if user_id or dry_run:
            student_report.update({
                'status': 'Success',
                'user_id': user_id if not dry_run else 0,
                'phone': phone,
                'password': plain_password,
            })
            print(f"✓ Successfully processed: {first_name} {last_name}")
        else:
            raise ValueError("Database insertion returned no user_id")

    except Exception as e:
        error_msg = str(e)
        student_report.update({
            'status': 'Error',
            'error_message': error_msg,
        })
        print(
            f"✗ Error processing {student_report.get('first_name', 'Unknown')} {student_report.get('last_name', '')}: {error_msg}")

    return student_report


def validate_excel_data_batch(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Validate all Excel data before insertion.

    Args:
        df: DataFrame containing student data.

    Returns:
        List of validation results for each row.
    """
    validation_results = []

    for index, row in df.iterrows():
        is_valid, extracted_data, error_msg = validate_student_data(row)
        validation_results.append({
            'row_index': index,
            'is_valid': is_valid,
            'data': extracted_data,
            'error': error_msg if not is_valid else None
        })

    return validation_results


def read_excel_and_insert_students(
        excel_file_path: str,
        ins_id: Optional[int] = None,
        con_id: Optional[int] = None,
        dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Read Excel file and insert students into the database.

    Args:
        excel_file_path: Path to the Excel file.
        ins_id: Institution ID (defaults to config value).
        con_id: Consultant ID (defaults to config value).
        dry_run: If True, process but don't insert into database.

    Returns:
        Dictionary containing insertion summary and report data.
    """
    ins_id = 14715
    con_id = 14718

    df = read_excel_file(excel_file_path)

    if not validate_excel_columns(df, REQUIRED_COLUMNS):
        raise ValueError(f"Excel file must contain columns: {', '.join(REQUIRED_COLUMNS)}")

    total_rows = len(df)

    print("Validating Excel data...")
    validation_results = validate_excel_data_batch(df)
    valid_rows = [r for r in validation_results if r['is_valid']]
    invalid_rows = [r for r in validation_results if not r['is_valid']]

    print(f"Valid rows: {len(valid_rows)}, Invalid rows: {len(invalid_rows)}")

    if invalid_rows:
        print("\nInvalid rows found:")
        for invalid in invalid_rows[:5]:
            print(f"  Row {invalid['row_index'] + 2}: {invalid['error']}")

    conn, cursor = get_db_connection()

    try:
        capacity_validator = CapacityValidator(conn, cursor, ins_id)

        if not dry_run:
            print("\nChecking available capacity...")
            is_available, available_count, capacity_msg = capacity_validator.check_available_capacity(len(valid_rows))
            print(f"Capacity check: {capacity_msg}")

            if not is_available:
                report_filename = f"student_insertion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                report_file_path = os.path.join(REPORT_OUTPUT_DIR, report_filename)
                os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

                report_data = []
                for result in validation_results:
                    report_data.append({
                        'row_number': result['row_index'] + 2,
                        'first_name': result['data'].get('first_name', ''),
                        'last_name': result['data'].get('last_name', ''),
                        'status': 'Error',
                        'user_id': None,
                        'phone': None,
                        'password': None,
                        'error_message': result['error'] if not result['is_valid'] else capacity_msg,
                        'original_province': str(df.iloc[result['row_index']]['استان']) if result['is_valid'] else '',
                        'processed_province_id': None,
                    })

                column_order = [
                    'row_number', 'first_name', 'last_name', 'status',
                    'user_id', 'phone', 'password', 'error_message',
                    'original_province', 'processed_province_id'
                ]

                write_excel_file(report_data, report_file_path, column_order=column_order)

                return {
                    'total_rows': total_rows,
                    'valid_rows': len(valid_rows),
                    'inserted_count': 0,
                    'error_count': total_rows,
                    'report_file_path': report_file_path,
                    'report_data': report_data,
                    'dry_run': dry_run,
                    'capacity_error': capacity_msg
                }

        inserted_count = 0
        error_count = len(invalid_rows)
        report_data = []

        print(f"\nStarting {'DRY RUN - ' if dry_run else ''}insertion process for {len(valid_rows)} students...")
        print(f"Using ins_id={ins_id}, con_id={con_id}")

        for validation_result in valid_rows:
            index = validation_result['row_index']
            row = df.iloc[index]

            student_report = process_student_row(
                row=row,
                index=index,
                conn=conn,
                cursor=cursor,
                ins_id=ins_id,
                con_id=con_id,
                dry_run=dry_run,
            )

            if student_report['status'] == 'Success':
                inserted_count += 1
            else:
                error_count += 1

            report_data.append(student_report)

        for invalid in invalid_rows:
            row = df.iloc[invalid['row_index']]
            report_data.append({
                'row_number': invalid['row_index'] + 2,
                'first_name': invalid['data'].get('first_name', str(row.get('نام', ''))),
                'last_name': invalid['data'].get('last_name', str(row.get('نام خانوادگی', ''))),
                'status': 'Error',
                'user_id': None,
                'phone': None,
                'password': None,
                'error_message': invalid['error'],
                'original_province': str(row.get('استان', '')),
                'processed_province_id': None,
            })

        if not dry_run and inserted_count > 0:
            capacity_validator.update_capacity_usage(inserted_count)
            conn.commit()
            print(f"\n=== INSERTION SUMMARY ===")
        elif not dry_run:
            print(f"\n=== INSERTION SUMMARY ===")
        else:
            print(f"\n=== DRY RUN SUMMARY ===")

        print(f"Total rows processed: {total_rows}")
        print(f"Valid rows: {len(valid_rows)}")
        print(f"Successfully {'processed' if dry_run else 'inserted'}: {inserted_count}")
        print(f"Errors encountered: {error_count}")
        if total_rows > 0:
            print(f"Success rate: {(inserted_count / total_rows) * 100:.1f}%")

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        if not dry_run:
            conn.rollback()
        raise

    finally:
        close_db_connection(conn, cursor)

    report_filename = f"student_insertion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    report_file_path = os.path.join(REPORT_OUTPUT_DIR, report_filename)

    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)

    column_order = [
        'row_number', 'first_name', 'last_name', 'status',
        'user_id', 'phone', 'password', 'error_message',
        'original_province', 'processed_province_id'
    ]

    write_excel_file(report_data, report_file_path, column_order=column_order)

    print(f"\n=== FINAL REPORT ===")
    print(f"Detailed report saved to: {report_file_path}")
    print(f"Total records in Excel: {total_rows}")
    print(f"Successfully {'processed' if dry_run else 'inserted'}: {inserted_count}")
    print(f"Failed: {error_count}")

    return {
        'total_rows': total_rows,
        'valid_rows': len(valid_rows),
        'inserted_count': inserted_count,
        'error_count': error_count,
        'report_file_path': report_file_path,
        'report_data': report_data,
        'dry_run': dry_run,
    }


def print_summary(result: Dict[str, Any]) -> None:
    """
    Print a summary of the insertion process.

    Args:
        result: Result dictionary from read_excel_and_insert_students.
    """
    print("\n" + "=" * 50)
    print("QUICK SUMMARY")
    print("=" * 50)
    print(f"Excel File Rows: {result['total_rows']}")
    print(f"Valid Rows: {result.get('valid_rows', result['total_rows'])}")
    action = "Processed" if result.get('dry_run') else "Inserted"
    print(f"Successfully {action}: {result['inserted_count']}")
    print(f"Errors: {result['error_count']}")
    if result['total_rows'] > 0:
        print(f"Success Rate: {(result['inserted_count'] / result['total_rows']) * 100:.1f}%")
    print(f"Report File: {result['report_file_path']}")

    if result.get('capacity_error'):
        print(f"\n⚠️ CAPACITY ERROR: {result['capacity_error']}")

    errors = [r for r in result['report_data'] if r['status'] == 'Error']
    if errors:
        print(f"\nFirst 5 errors:")
        for i, error in enumerate(errors[:5], 1):
            print(f"  {i}. {error['first_name']} {error['last_name']}: {error.get('error_message', 'Unknown error')}")


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Insert students from Excel file into database with capacity validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
              # Basic usage with default file
              python insert_student_with_excel.py
            
              # Specify custom file
              python insert_student_with_excel.py --file students.xlsx
            
              # Dry run (test without inserting)
              python insert_student_with_excel.py --dry-run
            
              # Custom institution and consultant IDs
              python insert_student_with_excel.py --ins-id 7017 --con-id 11359
        """
    )

    parser.add_argument(
        '--file',
        type=str,
        default='insert_file.xlsx',
        help='Path to Excel file (default: insert_file.xlsx)',
    )
    parser.add_argument(
        '--ins-id',
        type=int,
        default=None,
        help=f'Institution ID (default: {REPORT_DEFAULT_INS_ID})',
    )
    parser.add_argument(
        '--con-id',
        type=int,
        default=None,
        help=f'Consultant ID (default: {REPORT_DEFAULT_CON_ID})',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Process without inserting into database',
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"✗ Error: Excel file '{args.file}' not found!")
        sys.exit(1)

    try:
        result = read_excel_and_insert_students(
            excel_file_path=args.file,
            ins_id=args.ins_id,
            con_id=args.con_id,
            dry_run=args.dry_run,
        )
        print_summary(result)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
