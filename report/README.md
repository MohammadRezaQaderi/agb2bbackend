# Report Module

This module provides utilities for handling student data imports, exports, and reporting operations.

## Overview

The Report module includes scripts for:
- **Importing students** from Excel files into the database
- **Exporting student information** to Excel files
- **Updating consultant assignments** for students
- **Generating capacity reports** for institutions and schools

## Structure

```
Report/
├── __init__.py                    # Module initialization
├── README.md                      # This file
├── db_helper.py                   # Database connection utilities
├── excel_helper.py                # Excel file utilities
├── insert_student_with_excel.py   # Student import from Excel
├── select_student_info.py         # Student export to Excel
├── update_consultant_assignment.py # Update consultant assignments
└── capacity_report.py             # Generate capacity reports
```

## Configuration

All scripts use configuration from `config.py` and environment variables:

- `REPORT_OUTPUT_DIR`: Directory for generated reports (default: `{BASE_PATH}/Reports/exports`)
- `REPORT_DEFAULT_INS_ID`: Default institution ID (default: `7017`)
- `REPORT_DEFAULT_CON_ID`: Default consultant ID (default: `11359`)

Database configuration uses environment variables:
- `KS_DB_DRIVER`: Database driver (default: `{ODBC Driver 17 for SQL Server}`)
- `KS_DB_HOST`: Database host (default: `localhost,1433`)
- `KS_DB_NAME`: Database name (default: `AGB2B`)
- `KS_DB_USER`: Database username
- `KS_DB_PASSWORD`: Database password
- `KS_DB_TRUST_CERT`: Trust server certificate (default: `yes`)

## Scripts

### 1. insert_student_with_excel.py

Imports students from an Excel file into the database.

**Required Excel columns:**
- `نام` (First Name)
- `نام خانوادگی` (Last Name)
- `جنسیت` (Gender: پسر/دختر)
- `استان` (Province)
- `سال تولد` (Birth Year)

**Usage:**
```bash
# Basic usage
python insert_student_with_excel.py --file students.xlsx

# Dry run (test without inserting)
python insert_student_with_excel.py --file students.xlsx --dry-run

# Custom institution and consultant IDs
python insert_student_with_excel.py --file students.xlsx --ins-id 7017 --con-id 11359
```

**Output:**
- Generates a detailed report Excel file with insertion results
- Includes success/failure status, generated phone numbers, passwords, and error messages

### 2. select_student_info.py

Exports student information from the database to Excel.

**Available columns:**
- `first_name`, `last_name`, `phone`, `password`
- `gender`, `birth_date`, `city`
- `user_id`, `stu_id`, `created_date`

**Usage:**
```bash
# Basic export with default settings
python select_student_info.py

# Custom institution ID
python select_student_info.py --ins-id 7017

# Export specific columns
python select_student_info.py --columns first_name last_name phone password

# Interactive mode
python select_student_info.py --interactive
```

**Output:**
- Excel file with selected student information

### 3. update_consultant_assignment.py

Updates consultant assignments for students based on Excel file data.

**Required Excel columns:**
- `نام` (First Name)
- `نام خانوادگی` (Last Name)
- `مشاور` (Advisor Name)

**Usage:**
```bash
# Basic usage
python update_consultant_assignment.py --file stu_update.xlsx

# Dry run (test without updating)
python update_consultant_assignment.py --file stu_update.xlsx --dry-run

# Custom user_id range
python update_consultant_assignment.py --file stu_update.xlsx --user-id-min 9000 --user-id-max 11000
```

**Output:**
- Generates a detailed report Excel file with update results
- Includes previous and new consultant IDs, phone numbers, passwords, and error messages

### 4. capacity_report.py

Generates capacity reports for institutions and schools.

**Usage:**
```bash
# Basic usage with auto-generated filename
python report/capacity_report.py

# Date range for all report sheets
python report/capacity_report.py --from-date 2026-08-01 --to-date 2026-08-05

# Custom output file
python report/capacity_report.py --output my_capacity_report.xlsx
```

**Output:**
- Excel file with three sheets:
  - اطلاعات موسسات
  - اطلاعات مشاوران
  - تغییر ظرفیت‌ها
- Includes capacity information such as:
  - Institution/School name and phone
  - Total capacity
  - Used capacity
  - Remaining capacity

## Helper Modules

### db_helper.py

Provides synchronous database connection functions for standalone scripts:
- `get_db_connection()`: Get database connection and cursor
- `close_db_connection()`: Safely close connection and cursor

### excel_helper.py

Provides Excel file utilities:
- `read_excel_file()`: Read Excel file into DataFrame
- `write_excel_file()`: Write DataFrame to Excel file
- `validate_excel_columns()`: Validate required columns exist

## Error Handling

All scripts include comprehensive error handling:
- Database connection errors
- File I/O errors
- Data validation errors
- Transaction rollback on errors

## Best Practices

1. **Always use dry-run first**: Test scripts with `--dry-run` before making actual changes
2. **Backup data**: Always backup your database before running import/update scripts
3. **Check reports**: Review generated report files for errors before proceeding
4. **Environment variables**: Use environment variables for sensitive configuration
5. **Logging**: All scripts provide detailed console output and report files

## Dependencies

- `pandas`: Excel file handling
- `pyodbc`: Database connectivity
- `openpyxl`: Excel file engine
- `Helper.func_helper`: Shared utilities (PROVINCES, password generation, etc.)

## Notes

- All scripts are designed to be run standalone with `__main__` blocks
- Report files are automatically timestamped
- All scripts support command-line arguments for flexibility
- Database transactions are used to ensure data consistency
