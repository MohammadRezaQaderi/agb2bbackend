"""
User capacity report generation.

This script generates Excel reports showing capacity information for institutions
and schools, including total capacity, used capacity, and remaining capacity.
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report.db_helper import get_db_connection, close_db_connection
import pandas as pd
from datetime import datetime, time, timedelta

REGISTRATIONS_SHEET_NAME = 'ثبت‌نامی‌ها'
CAPACITY_LOGS_SHEET_NAME = 'تغییر ظرفیت‌ها'

CAPACITY_COLUMNS = [
    'ذره‌بین - مجاز',
    'ذره‌بین - استفاده شده',
    'دوپامین - مجاز',
    'دوپامین - استفاده شده',
]


def parse_datetime(value):
    if not value:
        return None

    normalized_value = value.strip()
    try:
        parsed = datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError("فرمت تاریخ باید به صورت YYYY-MM-DD یا YYYY-MM-DD HH:MM:SS باشد.") from exc

    return parsed


def parse_to_datetime(value):
    if not value:
        return None, False

    normalized_value = value.strip()
    parsed = parse_datetime(normalized_value)
    if len(normalized_value) == 10:
        return datetime.combine(parsed.date() + timedelta(days=1), time.min), True

    return parsed, False


def build_date_filter(column_name, from_date=None, to_date=None, to_date_is_exclusive=False):
    filters = []
    params = []

    if from_date:
        filters.append(f"{column_name} >= ?")
        params.append(from_date)

    if to_date:
        operator = "<" if to_date_is_exclusive else "<="
        filters.append(f"{column_name} {operator} ?")
        params.append(to_date)

    if not filters:
        return "", params

    return " AND " + " AND ".join(filters), params


def generate_capacity_report(conn, from_date=None, to_date=None, to_date_is_exclusive=False):
    date_filter, params = build_date_filter("u.created_time", from_date, to_date, to_date_is_exclusive)
    query = """
    SELECT 
        u.phone AS [شماره تماس],
        CASE 
            WHEN u.role = 'ins' THEN N'موسسه'
            WHEN u.role = 'sch' THEN N'مدرسه'
            WHEN u.role = 'wCon' THEN N'مشاور'
            ELSE u.role 
        END AS [نقش],
        u.created_time AS [تاریخ ایجاد],
        
        CASE 
            WHEN u.role = 'ins' THEN i.name
            WHEN u.role = 'sch' THEN s.name
            WHEN u.role = 'wCon' THEN CONCAT(w.first_name, N' ', w.last_name)
            ELSE N''
        END AS [نام],

        (SELECT COUNT(*) FROM con WHERE con.ins_id = u.user_id) AS [تعداد مشاور],
        (SELECT COUNT(*) FROM stu WHERE stu.ins_id = u.user_id) AS [تعداد دانش آموز],

        MAX(CASE WHEN cp.package_name = 'AG' THEN cp.allowed END) AS [ذره‌بین - مجاز],
        MAX(CASE WHEN cp.package_name = 'AG' THEN cp.used END) AS [ذره‌بین - استفاده شده],

        MAX(CASE WHEN cp.package_name = 'SCL' THEN cp.allowed END) AS [دوپامین - مجاز],
        MAX(CASE WHEN cp.package_name = 'SCL' THEN cp.used END) AS [دوپامین - استفاده شده]

    FROM users u
    LEFT JOIN ins i ON u.user_id = i.user_id AND u.role = 'ins'
    LEFT JOIN sch s ON u.user_id = s.user_id AND u.role = 'sch'
    LEFT JOIN wCon w ON u.user_id = w.user_id AND u.role = 'wCon'
    LEFT JOIN capacity c ON u.user_id = c.user_id
    LEFT JOIN capacity_package cp ON c.capacity_id = cp.capacity_id

    WHERE u.role IN ('ins', 'sch', 'wCon')
    {date_filter}
    GROUP BY 
        u.user_id, 
        u.phone, 
        u.role, 
        u.created_time, 
        i.name, 
        s.name,
        w.first_name,
        w.last_name
    ORDER BY [نقش], [نام];
    """.format(date_filter=date_filter)

    df = pd.read_sql(query, conn, params=params)
    return df


def generate_capacity_logs_report(conn, from_date=None, to_date=None, to_date_is_exclusive=False):
    date_filter, params = build_date_filter("cl.created_time", from_date, to_date, to_date_is_exclusive)
    query = """
    SELECT
        u.phone AS [شماره تماس],
        CASE
            WHEN u.role = 'ins' THEN N'موسسه'
            WHEN u.role = 'sch' THEN N'مدرسه'
            WHEN u.role = 'wCon' THEN N'مشاور'
            ELSE u.role
        END AS [نقش],
        cl.created_time AS [تاریخ تغییر ظرفیت],
        CASE
            WHEN u.role = 'ins' THEN i.name
            WHEN u.role = 'sch' THEN s.name
            WHEN u.role = 'wCon' THEN CONCAT(w.first_name, N' ', w.last_name)
            ELSE N''
        END AS [نام],
        CASE
            WHEN cl.package_name = 'AG' THEN N'AG ذره‌بین'
            WHEN cl.package_name = 'SCL' THEN N'SCL دوپامین'
            ELSE cl.package_name
        END AS [نام محصول],
        cl.[used] AS [ظرفیت استفاده شده (used)],
        cl.allowed AS [ظرفیت باقی مانده (allowed)],
        cl.[change] AS [ظرفیت اضافه شده (change)]
    FROM capacity_logs cl
    INNER JOIN users u ON cl.user_id = u.user_id
    LEFT JOIN ins i ON u.user_id = i.user_id AND u.role = 'ins'
    LEFT JOIN sch s ON u.user_id = s.user_id AND u.role = 'sch'
    LEFT JOIN wCon w ON u.user_id = w.user_id AND u.role = 'wCon'
    WHERE u.role IN ('ins', 'sch', 'wCon')
    {date_filter}
    ORDER BY cl.created_time, [نقش], [نام];
    """.format(date_filter=date_filter)

    df = pd.read_sql(query, conn, params=params)
    return df


def prepare_capacity_report(df):
    for col in CAPACITY_COLUMNS:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    df['نام'] = df['نام'].fillna('')
    df['تعداد مشاور'] = df['تعداد مشاور'].fillna(0).astype(int)
    df['تعداد دانش آموز'] = df['تعداد دانش آموز'].fillna(0).astype(int)
    return df


def prepare_capacity_logs_report(df):
    numeric_columns = [
        'ظرفیت استفاده شده (used)',
        'ظرفیت باقی مانده (allowed)',
        'ظرفیت اضافه شده (change)',
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    df['نام'] = df['نام'].fillna('')
    df['نام محصول'] = df['نام محصول'].fillna('')
    return df


def adjust_worksheet(worksheet):
    worksheet.sheet_view.rightToLeft = True
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except TypeError:
                pass
        adjusted_width = min(max_length + 2, 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width


def write_capacity_workbook(capacity_df, logs_df, output_file_path):
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
        capacity_df.to_excel(writer, sheet_name=REGISTRATIONS_SHEET_NAME, index=False)
        logs_df.to_excel(writer, sheet_name=CAPACITY_LOGS_SHEET_NAME, index=False)

        adjust_worksheet(writer.sheets[REGISTRATIONS_SHEET_NAME])
        adjust_worksheet(writer.sheets[CAPACITY_LOGS_SHEET_NAME])


def export_capacity_report(conn, from_date=None, to_date=None, to_date_is_exclusive=False, output_file_path=None):
    print("در حال دریافت اطلاعات و تولید گزارش...")
    capacity_df = prepare_capacity_report(
        generate_capacity_report(conn, from_date, to_date, to_date_is_exclusive)
    )
    logs_df = prepare_capacity_logs_report(
        generate_capacity_logs_report(conn, from_date, to_date, to_date_is_exclusive)
    )

    if not output_file_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file_path = f"capacity_report_{timestamp}.xlsx"

    try:
        write_capacity_workbook(capacity_df, logs_df, output_file_path)
    except Exception as e:
        raise ValueError(f"خطا در ذخیره فایل اکسل: {e}") from e

    print(f"گزارش با موفقیت در فایل {output_file_path} ذخیره شد.")
    print(f"\nتعداد رکوردهای شیت {REGISTRATIONS_SHEET_NAME}: {len(capacity_df)}")
    print(f"تعداد رکوردهای شیت {CAPACITY_LOGS_SHEET_NAME}: {len(logs_df)}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate capacity Excel report.")
    parser.add_argument("--from-date", dest="from_date", help="Start date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--to-date", dest="to_date", help="End date: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--output", dest="output", help="Output Excel file path")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        args = parse_args()
        from_date = parse_datetime(args.from_date)
        to_date, to_date_is_exclusive = parse_to_datetime(args.to_date)

        if from_date and to_date and from_date > to_date:
            raise ValueError("تاریخ from-date نباید بعد از to-date باشد.")

        conn, cursor = get_db_connection()
        if conn:
            export_capacity_report(
                conn,
                from_date=from_date,
                to_date=to_date,
                to_date_is_exclusive=to_date_is_exclusive,
                output_file_path=args.output,
            )
            close_db_connection(conn, cursor)
        else:
            print("خطا در اتصال به پایگاه داده")
    except Exception as e:
        print(f"خطا در اجرای گزارش: {str(e)}")
        import traceback

        traceback.print_exc()
