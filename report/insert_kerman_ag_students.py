"""
Insert Kerman AG students from the two 0405 grade Excel files.

Default mode is dry-run: it parses Excel, validates rows, checks AG capacity,
and writes a report without changing the database. Use --commit to insert.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import struct
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import helper.func_helper as func_helper
from report.db_helper import close_db_connection, get_db_connection


DEFAULT_FILES = [
    "/home/mrq/Downloads/7.xls",
    "/home/mrq/Downloads/8.xls",
]
DEFAULT_INS_ID = 16070
DEFAULT_CON_ID = 16349
DEFAULT_CITY = "کرمان,21"
DEFAULT_INS_ROLE = "ins"
DEFAULT_ACCESS = {"AG": {"permission": 1, "limit": 0}}
REQUIRED_COLUMNS = ["نام", "نام خانوادگی", "تاریخ تولد"]
OPTIONAL_COLUMNS = ["شماره ملی", "نام پدر", "پایه تحصیلی", "کلاس درس"]


@dataclass
class Student:
    source_file: str
    row_number: int
    first_name: str
    last_name: str
    birth_raw: str
    birth_year: str
    national_id: str = ""
    father_name: str = ""
    grade: str = ""
    classroom: str = ""


@dataclass
class CapacityPackage:
    capacity_package_id: int
    allowed: int
    used: int


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def extract_birth_year(value: str) -> str:
    cleaned = normalize_cell(value).replace("-", "/")
    year = cleaned[:4]
    if len(year) == 4 and year.isdigit() and 1300 <= int(year) <= 1405:
        return year
    raise ValueError(f"invalid birth date: {value!r}")


def read_excel_rows(path: Path) -> list[dict[str, str]]:
    try:
        import pandas as pd

        df = pd.read_excel(path)
        rows = []
        for _, row in df.iterrows():
            rows.append({normalize_cell(k): normalize_cell(v) for k, v in row.items()})
        return rows
    except Exception as pandas_error:
        if path.suffix.lower() != ".xls":
            raise RuntimeError(f"cannot read {path}: {pandas_error}") from pandas_error
        return read_legacy_xls_rows(path)


def parse_students(files: Iterable[str], limit: int | None = None) -> tuple[list[Student], list[dict[str, str]]]:
    students: list[Student] = []
    errors: list[dict[str, str]] = []

    for file_path in files:
        path = Path(file_path)
        rows = read_excel_rows(path)
        for idx, row in enumerate(rows, start=2):
            if limit is not None and len(students) >= limit:
                return students, errors

            if not any(normalize_cell(v) for v in row.values()):
                continue

            missing = [col for col in REQUIRED_COLUMNS if not normalize_cell(row.get(col))]
            if missing:
                errors.append({
                    "source_file": path.name,
                    "row_number": str(idx),
                    "status": "Error",
                    "error": f"missing required columns: {', '.join(missing)}",
                })
                continue

            try:
                students.append(Student(
                    source_file=path.name,
                    row_number=idx,
                    first_name=normalize_cell(row.get("نام")),
                    last_name=normalize_cell(row.get("نام خانوادگی")),
                    birth_raw=normalize_cell(row.get("تاریخ تولد")),
                    birth_year=extract_birth_year(row.get("تاریخ تولد", "")),
                    national_id=normalize_cell(row.get("شماره ملی")),
                    father_name=normalize_cell(row.get("نام پدر")),
                    grade=normalize_cell(row.get("پایه تحصیلی")),
                    classroom=normalize_cell(row.get("کلاس درس")),
                ))
            except Exception as exc:
                errors.append({
                    "source_file": path.name,
                    "row_number": str(idx),
                    "status": "Error",
                    "error": str(exc),
                })

    return students, errors


def generate_unique_phone(cursor) -> str:
    while True:
        phone = "009" + str(random.randint(10_000_000, 99_999_999))
        cursor.execute("SELECT 1 FROM users WHERE phone = ?", phone)
        if cursor.fetchone() is None:
            return phone


def get_capacity_packages(cursor, ins_id: int) -> list[CapacityPackage]:
    cursor.execute(
        """
        SELECT capacity_package_id, ISNULL(allowed, 0) AS allowed, ISNULL([used], 0) AS used
        FROM capacity_package
        WHERE user_id = ? AND package_name = 'AG'
        ORDER BY capacity_package_id
        """,
        ins_id,
    )
    packages = [
        CapacityPackage(
            capacity_package_id=int(row.capacity_package_id),
            allowed=int(row.allowed or 0),
            used=int(row.used or 0),
        )
        for row in cursor.fetchall()
    ]
    if packages:
        return packages

    cursor.execute("SELECT capacity_id FROM capacity WHERE user_id = ?", ins_id)
    capacity = cursor.fetchone()
    if capacity is None:
        return []

    cursor.execute(
        """
        SELECT capacity_package_id, ISNULL(allowed, 0) AS allowed, ISNULL([used], 0) AS used
        FROM capacity_package
        WHERE capacity_id = ? AND package_name = 'AG'
        ORDER BY capacity_package_id
        """,
        int(capacity.capacity_id),
    )
    return [
        CapacityPackage(
            capacity_package_id=int(row.capacity_package_id),
            allowed=int(row.allowed or 0),
            used=int(row.used or 0),
        )
        for row in cursor.fetchall()
    ]


def find_existing_student(cursor, student: Student, ins_id: int, con_id: int):
    cursor.execute(
        """
        SELECT TOP 1 user_id, phone
        FROM stu
        WHERE first_name = ? AND last_name = ? AND birth_date = ? AND ins_id = ? AND con_id = ?
        """,
        student.first_name,
        student.last_name,
        student.birth_year,
        ins_id,
        con_id,
    )
    return cursor.fetchone()


def insert_student(cursor, student: Student, args) -> dict[str, Any]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plain_password = func_helper.random_generate_password()
    encrypted_password = func_helper.encrypt_password(plain_password)
    phone = generate_unique_phone(cursor)
    access_json = json.dumps(DEFAULT_ACCESS, ensure_ascii=False)

    cursor.execute(
        """
        INSERT INTO users (phone, password, role, created_time, edited_time)
        OUTPUT INSERTED.user_id
        VALUES (?, ?, 'stu', ?, ?)
        """,
        phone,
        encrypted_password,
        now,
        now,
    )
    user_id = int(cursor.fetchone()[0])

    cursor.execute(
        """
        INSERT INTO stu (
            user_id, first_name, last_name, sex, city, ins_id, con_id,
            adder_id, editor_id, comment, birth_date, ins_role,
            created_time, edited_time, access
        )
        VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        user_id,
        student.first_name,
        student.last_name,
        args.city,
        args.ins_id,
        args.con_id,
        args.ins_id,
        args.ins_id,
        None,
        student.birth_year,
        args.ins_role,
        now,
        now,
        access_json,
    )

    return {
        "status": "Inserted",
        "user_id": user_id,
        "phone": phone,
        "password": plain_password,
        "encrypted_password": encrypted_password,
    }


def update_capacity_usage(cursor, packages: list[CapacityPackage], used_count: int) -> None:
    remaining = used_count
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for package in packages:
        if remaining <= 0:
            break
        take = min(remaining, max(package.allowed, 0))
        if take <= 0:
            continue

        cursor.execute(
            """
            UPDATE capacity_package
            SET allowed = allowed - ?,
                [used] = ISNULL([used], 0) + ?,
                edited_time = ?
            WHERE capacity_package_id = ? AND allowed >= ?
            """,
            take,
            take,
            now,
            package.capacity_package_id,
            take,
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"capacity package changed during update: {package.capacity_package_id}")
        remaining -= take

    if remaining:
        raise RuntimeError(f"not enough AG capacity while updating; missing {remaining}")


def build_report_row(student: Student, status: str, **extra: Any) -> dict[str, Any]:
    row = {
        "source_file": student.source_file,
        "row_number": student.row_number,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "national_id": student.national_id,
        "birth_raw": student.birth_raw,
        "birth_year": student.birth_year,
        "sex": 1,
        "city": extra.pop("city", DEFAULT_CITY),
        "access": json.dumps(DEFAULT_ACCESS, ensure_ascii=False),
        "grade": student.grade,
        "classroom": student.classroom,
        "status": status,
    }
    row.update(extra)
    return row


def write_report(rows: list[dict[str, Any]], output_dir: Path, committed: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    name = "kerman_ag_insert" if committed else "kerman_ag_dry_run"
    path = output_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    fieldnames = [
        "source_file", "row_number", "first_name", "last_name", "national_id",
        "birth_raw", "birth_year", "sex", "city", "access", "grade", "classroom",
        "status", "user_id", "phone", "password", "encrypted_password", "error",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def run(args) -> int:
    students, parse_errors = parse_students(args.files, args.limit)
    duplicate_keys = find_excel_duplicates(students)
    conn = None
    cursor = None
    report_rows: list[dict[str, Any]] = []

    print(f"Parsed students: {len(students)}")
    print(f"Parse errors: {len(parse_errors)}")
    if duplicate_keys:
        print(f"Excel duplicate name/year rows: {len(duplicate_keys)}")

    if args.parse_only:
        for student in students:
            report_rows.append(build_report_row(student, "Parsed", city=args.city))
        report_rows.extend(parse_errors)
        report_path = write_report(report_rows, args.output_dir, committed=False)
        print(f"Parse-only report: {report_path}")
        return 0

    try:
        conn, cursor = get_db_connection()
        packages = get_capacity_packages(cursor, args.ins_id)
        available = sum(max(pkg.allowed, 0) for pkg in packages)
        print_capacity(packages, available)

        if not packages:
            raise RuntimeError(f"No AG capacity package found for ins_id={args.ins_id}")

        existing_count = 0
        insert_candidates: list[Student] = []
        for student in students:
            existing = find_existing_student(cursor, student, args.ins_id, args.con_id)
            if existing and args.skip_existing:
                existing_count += 1
                report_rows.append(build_report_row(
                    student,
                    "SkippedExisting",
                    city=args.city,
                    user_id=int(existing.user_id),
                    phone=existing.phone,
                    error="matched first_name/last_name/birth_year/ins_id/con_id",
                ))
            else:
                insert_candidates.append(student)

        requested_capacity = len(insert_candidates)
        if requested_capacity > available:
            raise RuntimeError(f"Insufficient AG capacity. requested={requested_capacity}, available={available}")

        if args.commit:
            inserted_count = 0
            for student in insert_candidates:
                result = insert_student(cursor, student, args)
                report_rows.append(build_report_row(student, city=args.city, **result))
                inserted_count += 1

            update_capacity_usage(cursor, packages, inserted_count)
            conn.commit()
            print(f"Inserted students: {inserted_count}")
        else:
            for student in insert_candidates:
                report_rows.append(build_report_row(student, "WouldInsert", city=args.city))
            print(f"Dry-run insert candidates: {len(insert_candidates)}")

        report_rows.extend(parse_errors)
        report_path = write_report(report_rows, args.output_dir, committed=args.commit)
        print(f"Existing skipped: {existing_count}")
        print(f"Report: {report_path}")
        print("No database changes were made." if not args.commit else "Database transaction committed.")
        return 0
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        close_db_connection(conn, cursor)


def print_capacity(packages: list[CapacityPackage], available: int) -> None:
    print(f"AG capacity packages: {len(packages)}")
    for package in packages:
        print(
            f"  id={package.capacity_package_id} allowed={package.allowed} used={package.used}"
        )
    print(f"Available AG capacity used by this script: {available}")


def find_excel_duplicates(students: list[Student]) -> set[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    duplicates: set[tuple[str, str, str]] = set()
    for student in students:
        key = (student.first_name, student.last_name, student.birth_year)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


# Minimal BIFF8 .xls reader used when pandas cannot read legacy .xls files.
def read_legacy_xls_rows(path: Path) -> list[dict[str, str]]:
    workbook = extract_cfb_stream(path.read_bytes(), "Workbook")
    sst = parse_sst(workbook)
    sheets = get_sheet_ranges(workbook)
    if not sheets:
        return []

    cells = parse_sheet_cells(workbook, sheets[0][0], sheets[0][1], sst)
    if not cells:
        return []

    max_row = max(row for row, _ in cells)
    max_col = max(col for _, col in cells)
    grid = [
        [normalize_cell(cells.get((row, col))) for col in range(max_col + 1)]
        for row in range(max_row + 1)
    ]
    header_index = next(
        (i for i, row in enumerate(grid) if all(col in row for col in REQUIRED_COLUMNS)),
        None,
    )
    if header_index is None:
        raise RuntimeError(f"could not find header row in {path}")

    headers = grid[header_index]
    rows: list[dict[str, str]] = []
    for values in grid[header_index + 1:]:
        row = {headers[i]: values[i] for i in range(min(len(headers), len(values))) if headers[i]}
        if any(row.get(col, "") for col in REQUIRED_COLUMNS + OPTIONAL_COLUMNS):
            rows.append(row)
    return rows


def extract_cfb_stream(data: bytes, stream_name: str) -> bytes:
    if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise RuntimeError("not an OLE compound document")

    sector_size = 1 << struct.unpack_from("<H", data, 30)[0]
    mini_sector_size = 1 << struct.unpack_from("<H", data, 32)[0]
    first_dir_sector = struct.unpack_from("<I", data, 48)[0]
    first_minifat_sector = struct.unpack_from("<I", data, 60)[0]
    num_minifat_sectors = struct.unpack_from("<I", data, 64)[0]
    first_difat_sector = struct.unpack_from("<I", data, 68)[0]
    num_difat_sectors = struct.unpack_from("<I", data, 72)[0]

    def sector(sec_id: int) -> bytes:
        start = (sec_id + 1) * sector_size
        return data[start:start + sector_size]

    difat = [
        value for value in struct.unpack_from("<109I", data, 76)
        if value not in (0xFFFFFFFF, 0xFFFFFFFE)
    ]
    next_difat = first_difat_sector
    for _ in range(num_difat_sectors):
        raw = sector(next_difat)
        entries = struct.unpack("<" + "I" * (sector_size // 4), raw)
        difat.extend(v for v in entries[:-1] if v not in (0xFFFFFFFF, 0xFFFFFFFE))
        next_difat = entries[-1]
        if next_difat == 0xFFFFFFFE:
            break

    fat: list[int] = []
    for fat_sector in difat:
        raw = sector(fat_sector)
        fat.extend(struct.unpack("<" + "I" * (sector_size // 4), raw))

    def read_chain(start_sector: int, table: list[int], unit_size: int, source: bytes | None = None) -> bytes:
        out = bytearray()
        sec = start_sector
        while sec not in (0xFFFFFFFE, 0xFFFFFFFF):
            if source is None:
                out.extend(sector(sec))
            else:
                offset = sec * unit_size
                out.extend(source[offset:offset + unit_size])
            sec = table[sec]
        return bytes(out)

    directory = read_chain(first_dir_sector, fat, sector_size)
    entries = {}
    root = None
    for offset in range(0, len(directory), 128):
        entry = directory[offset:offset + 128]
        if len(entry) < 128:
            continue
        name_len = struct.unpack_from("<H", entry, 64)[0]
        if name_len < 2:
            continue
        name = entry[:name_len - 2].decode("utf-16le", errors="replace")
        obj_type = entry[66]
        start_sector = struct.unpack_from("<I", entry, 116)[0]
        size = struct.unpack_from("<Q", entry, 120)[0]
        entries[name] = (obj_type, start_sector, size)
        if obj_type == 5:
            root = (start_sector, size)

    if stream_name not in entries:
        raise RuntimeError(f"stream not found: {stream_name}")

    obj_type, start_sector, size = entries[stream_name]
    if obj_type != 2:
        raise RuntimeError(f"not a stream: {stream_name}")

    if size >= 4096:
        return read_chain(start_sector, fat, sector_size)[:size]

    if root is None:
        raise RuntimeError("mini stream root not found")
    mini_stream = read_chain(root[0], fat, sector_size)[:root[1]]
    minifat = []
    if num_minifat_sectors:
        minifat_bytes = read_chain(first_minifat_sector, fat, sector_size)
        minifat = list(struct.unpack("<" + "I" * (len(minifat_bytes) // 4), minifat_bytes))
    return read_chain(start_sector, minifat, mini_sector_size, mini_stream)[:size]


def iter_biff_records(workbook: bytes):
    pos = 0
    while pos + 4 <= len(workbook):
        record_id, size = struct.unpack_from("<HH", workbook, pos)
        pos += 4
        payload = workbook[pos:pos + size]
        pos += size
        yield record_id, payload, pos - size - 4


class ChunkStream:
    def __init__(self, chunks: list[bytes]):
        self.chunks = chunks
        self.index = 0
        self.pos = 0

    def read(self, size: int) -> bytes:
        out = bytearray()
        while size:
            if self.index >= len(self.chunks):
                raise EOFError("unexpected end of BIFF CONTINUE stream")
            chunk = self.chunks[self.index]
            if self.pos >= len(chunk):
                self.index += 1
                self.pos = 0
                continue
            take = min(size, len(chunk) - self.pos)
            out.extend(chunk[self.pos:self.pos + take])
            self.pos += take
            size -= take
        return bytes(out)

    def remaining_in_chunk(self) -> int:
        if self.index >= len(self.chunks):
            return 0
        return len(self.chunks[self.index]) - self.pos

    def read_current(self, size: int) -> bytes:
        chunk = self.chunks[self.index]
        out = chunk[self.pos:self.pos + size]
        self.pos += len(out)
        return bytes(out)

    def next_chunk(self) -> None:
        self.index += 1
        self.pos = 0


def read_biff_string(stream: ChunkStream) -> str:
    length = struct.unpack("<H", stream.read(2))[0]
    flags = stream.read(1)[0]
    high_byte = bool(flags & 0x01)
    rich_text = bool(flags & 0x08)
    extended = bool(flags & 0x04)
    rich_runs = struct.unpack("<H", stream.read(2))[0] if rich_text else 0
    ext_size = struct.unpack("<I", stream.read(4))[0] if extended else 0

    parts: list[str] = []
    remaining = length
    while remaining:
        bytes_per_char = 2 if high_byte else 1
        chars_here = stream.remaining_in_chunk() // bytes_per_char
        if chars_here:
            take_chars = min(remaining, chars_here)
            raw = stream.read_current(take_chars * bytes_per_char)
            parts.append(raw.decode("utf-16le" if high_byte else "latin1", errors="replace"))
            remaining -= take_chars
        if remaining:
            stream.next_chunk()
            high_byte = bool(stream.read(1)[0] & 0x01)

    if rich_runs:
        stream.read(4 * rich_runs)
    if ext_size:
        stream.read(ext_size)
    return "".join(parts)


def parse_sst(workbook: bytes) -> list[str]:
    chunks: list[bytes] = []
    in_sst = False
    for record_id, payload, _ in iter_biff_records(workbook):
        if record_id == 0x00FC:
            in_sst = True
            chunks = [payload]
        elif in_sst and record_id == 0x003C:
            chunks.append(payload)
        elif in_sst:
            break
    if not chunks:
        return []

    unique_count = struct.unpack_from("<I", chunks[0], 4)[0]
    stream = ChunkStream([chunks[0][8:]] + chunks[1:])
    strings = []
    for _ in range(unique_count):
        strings.append(read_biff_string(stream))
    return strings


def get_sheet_ranges(workbook: bytes) -> list[tuple[int, int, str]]:
    bounds: list[tuple[int, str]] = []
    for record_id, payload, _ in iter_biff_records(workbook):
        if record_id != 0x0085:
            continue
        start = struct.unpack_from("<I", payload, 0)[0]
        name_len = payload[6]
        flags = payload[7]
        raw = payload[8:8 + name_len * (2 if flags & 1 else 1)]
        name = raw.decode("utf-16le" if flags & 1 else "latin1", errors="replace")
        bounds.append((start, name))

    bounds.sort()
    return [
        (start, bounds[i + 1][0] if i + 1 < len(bounds) else len(workbook), name)
        for i, (start, name) in enumerate(bounds)
    ]


def parse_sheet_cells(workbook: bytes, start: int, end: int, sst: list[str]) -> dict[tuple[int, int], Any]:
    cells: dict[tuple[int, int], Any] = {}
    pos = start
    while pos + 4 <= end:
        record_id, size = struct.unpack_from("<HH", workbook, pos)
        pos += 4
        payload = workbook[pos:pos + size]
        pos += size
        if record_id == 0x000A:
            break
        if record_id == 0x00FD:
            row, col, _, sst_index = struct.unpack_from("<HHHI", payload, 0)
            cells[(row, col)] = sst[sst_index] if sst_index < len(sst) else ""
        elif record_id == 0x0203:
            row, col, _ = struct.unpack_from("<HHH", payload, 0)
            cells[(row, col)] = struct.unpack_from("<d", payload, 6)[0]
        elif record_id == 0x027E:
            row, col, _, raw = struct.unpack_from("<HHHI", payload, 0)
            cells[(row, col)] = decode_rk(raw)
        elif record_id == 0x00BD:
            row, first_col = struct.unpack_from("<HH", payload, 0)
            last_col = struct.unpack_from("<H", payload, len(payload) - 2)[0]
            offset = 4
            for col in range(first_col, last_col + 1):
                _, raw = struct.unpack_from("<HI", payload, offset)
                offset += 6
                cells[(row, col)] = decode_rk(raw)
    return cells


def decode_rk(raw: int) -> float | int:
    divided_by_100 = raw & 1
    is_int = raw & 2
    value_raw = raw & 0xFFFFFFFC
    if is_int:
        if value_raw & 0x80000000:
            value_raw -= 0x100000000
        value: float | int = value_raw >> 2
    else:
        value = struct.unpack("<d", struct.pack("<I", value_raw) + b"\x00\x00\x00\x00")[0]
    if divided_by_100:
        value = value / 100
    return value


def parse_args():
    parser = argparse.ArgumentParser(description="Dry-run or insert Kerman AG students from Excel.")
    parser.add_argument("--files", nargs="+", default=DEFAULT_FILES, help="Excel files to import.")
    parser.add_argument("--ins-id", type=int, default=DEFAULT_INS_ID)
    parser.add_argument("--con-id", type=int, default=DEFAULT_CON_ID)
    parser.add_argument("--city", default=DEFAULT_CITY)
    parser.add_argument("--ins-role", default=DEFAULT_INS_ROLE, choices=["ins", "sch", "ocon"])
    parser.add_argument("--output-dir", type=Path, default=Path("report/outputs"))
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N valid rows.")
    parser.add_argument("--parse-only", action="store_true", help="Parse Excel and write report without DB access.")
    parser.add_argument("--dry-run", action="store_true", help="Default mode; kept for explicit safe runs.")
    parser.add_argument("--commit", action="store_true", help="Actually insert rows and update AG capacity.")
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    parser.set_defaults(skip_existing=True)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
