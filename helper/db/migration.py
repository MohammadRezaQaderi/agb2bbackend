import pyodbc
import json
import os
from cryptography.fernet import Fernet, InvalidToken
from typing import Optional, Sequence

try:
    from config import (
        DB_DRIVER,
        DB_SERVER,
        DB_DATABASE,
        DB_UID,
        DB_PWD,
        DB_TRUST_CERT,
        PASSWORD_SECRET_KEY,
    )
except ImportError:
    DB_DRIVER = "ODBC Driver 17 for SQL Server"
    DB_SERVER = "localhost,1433"
    DB_DATABASE = "AGB2B_COPY"
    DB_UID = os.getenv("AG_DB_UID", "")
    DB_PWD = os.getenv("AG_DB_PWD", "")
    DB_TRUST_CERT = "yes"
    PASSWORD_SECRET_KEY = os.getenv("AG_PASSWORD_SECRET_KEY", "")

TABLE_DEFINITIONS = {
    "users": """
        CREATE TABLE users (
            user_id INT IDENTITY(1, 1) PRIMARY KEY,
            phone NVARCHAR(12),
            password NVARCHAR(255),
            role NVARCHAR(100) NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "ins": """
        CREATE TABLE ins (
            ins_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            name NVARCHAR(100),
            logo VARCHAR(MAX),
            verify INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "sch": """
        CREATE TABLE sch (
            sch_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            name NVARCHAR(100),
            logo VARCHAR(MAX),
            verify INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "ocon": """
        CREATE TABLE ocon (
            ocon_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            logo VARCHAR(MAX),
            sex INT DEFAULT 1,
            verify INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "con": """
        CREATE TABLE con (
            con_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            sex INT DEFAULT 1,
            owner_user_id INT,
            editor_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "stu": """
        CREATE TABLE stu (
            stu_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            sex INT,
            city NVARCHAR(100),
            access VARCHAR(MAX) DEFAULT '{}',
            comment NVARCHAR(MAX),
            birth_date NVARCHAR(4),
            owner_user_id INT,
            consultant_user_id INT,
            adder_id INT,
            editor_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "setting": """
        CREATE TABLE setting (
            setting_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            description NVARCHAR(MAX),
            voice NVARCHAR(MAX),
            quiz_id INT,
            editor_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "capacity": """
        CREATE TABLE capacity (
            capacity_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "capacity_package": """
        CREATE TABLE capacity_package (
            capacity_package_id INT IDENTITY(1, 1) PRIMARY KEY,
            capacity_id INT FOREIGN KEY REFERENCES capacity(capacity_id),
            package_name NVARCHAR(50),
            user_id INT,
            allowed INT DEFAULT 0,
            used INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "capacity_logs": """
        CREATE TABLE capacity_logs (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            user_id INT,
            capacity_id INT,
            capacity_package_id INT,
            package_name NVARCHAR(50),
            allowed INT DEFAULT 0,
            used INT DEFAULT 0,
            change INT DEFAULT 0,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "quiz_attempt": """
        CREATE TABLE quiz_attempt (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT NOT NULL,
            quiz_kind VARCHAR(25) NOT NULL,
            quiz_id INT NOT NULL,
            state INT NOT NULL DEFAULT 1,
            remain_time INT NULL,
            owner_user_id INT NULL,
            consultant_user_id INT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "quiz_question_answer": """
        CREATE TABLE quiz_question_answer (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            attempt_id INT NOT NULL,
            user_id INT NOT NULL,
            quiz_kind VARCHAR(25) NOT NULL,
            quiz_id INT NOT NULL,
            question_id INT NOT NULL,
            answer_value NVARCHAR(MAX) NOT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "scores": """
        CREATE TABLE scores (
            scores_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            quiz_score NVARCHAR(MAX),
            brain_fields NVARCHAR(MAX),
            brain_categories NVARCHAR(MAX),
            brain_branches NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "scl_scores": """
        CREATE TABLE scl_scores (
            scores_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            scl_date NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "result_state": """
        CREATE TABLE result_state (
            result_state_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            t_state NVARCHAR(100),
            r_state NVARCHAR(100),
            e_state NVARCHAR(100),
            a_state NVARCHAR(100),
            m_state NVARCHAR(100),
            f_state NVARCHAR(100),
            i_state NVARCHAR(100),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "hedayat_fields": """
        CREATE TABLE hedayat_fields (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            suggested NVARCHAR(MAX),
            other NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "notifications": """
        CREATE TABLE notifications (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            roles NCHAR(100),
            user_id INT,
            title NVARCHAR(MAX),
            description NVARCHAR(MAX),
            added_by NVARCHAR(MAX),         
            priority NCHAR(100),   
            persian_date NVARCHAR(50),
            fullText NVARCHAR(MAX),      
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
    "payment": """
        CREATE TABLE payment (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            payment_id INT NOT NULL,
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            state NVARCHAR(100),
            status NVARCHAR(100),
            price INT,
            discount_price INT,
            track_id NVARCHAR(100),
            discount_id INT DEFAULT NULL,
            result NVARCHAR(100) NULL,
            saleReferenceId NVARCHAR(50) NULL,
            message TEXT,
            token NVARCHAR(MAX),
            product_data NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "payment_log": """
        CREATE TABLE payment_log (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            payment_id INT NOT NULL,
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            state NVARCHAR(100),
            status NVARCHAR(100),
            price INT,
            discount_price INT,
            track_id NVARCHAR(100),
            result NVARCHAR(100) NULL,
            discount_id INT DEFAULT NULL,
            saleReferenceId NVARCHAR(50) NULL,
            message TEXT,
            token NVARCHAR(MAX),
            product_data NVARCHAR(MAX),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "discounts": """
        CREATE TABLE discounts (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            code VARCHAR(10),
            status NVARCHAR(100),
            discount_percentage FLOAT,
            used INT DEFAULT 0,
            count INT DEFAULT 100,
            used_apply INT DEFAULT 0,
            count_apply INT DEFAULT 0,
            expire_time DATETIME DEFAULT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "using_discount": """
        CREATE TABLE using_discount (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            code VARCHAR(10),
            status NVARCHAR(100),
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "tokens": """
        CREATE TABLE tokens (
            token_id INT IDENTITY(1, 1) PRIMARY KEY,
            token VARCHAR(MAX),
            user_id INT UNIQUE,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "comments": """
        CREATE TABLE comments (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            name NVARCHAR(400),      
            comment NVARCHAR(MAX),
            rating FLOAT DEFAULT 5.0,
            persian_date NVARCHAR(MAX),
            user_id INT NOT NULL,
            phone NVARCHAR(12) NOT NULL,
            role NVARCHAR(100) NULL,
            db_name NVARCHAR(400) NOT NULL,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
    "redis_logs": """
        CREATE TABLE redis_logs (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            kind NVARCHAR(20),
            result VARCHAR(MAX),
            status INT DEFAULT 0,
            phone NVARCHAR(12),
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "quiz_missing_answers": """
        CREATE TABLE quiz_missing_answers (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            question_id INT,
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE()
        )
    """,
    "api_logs": """
        CREATE TABLE api_logs (
            id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            end_point NCHAR(100),
            func_name NCHAR(100),
            data NVARCHAR(MAX),         
            error_p NVARCHAR(MAX),         
            created_time DATETIME DEFAULT GETDATE(),
            edited_time DATETIME DEFAULT GETDATE(),
        )
    """,
}

DEFAULT_TABLES: Sequence[str] = (
    'users', 'ins', 'sch', 'ocon', 'con', 'stu', 'setting', 'capacity', 'capacity_package', 'capacity_logs',
    'quiz_attempt', 'quiz_question_answer', 'scores', 'scl_scores', 'result_state', 'hedayat_fields', 'notifications', 'payment',
    'payment_log', 'discounts', 'using_discount', 'tokens', 'redis_logs', 'quiz_missing_answers', 'api_logs'
)

_PASSWORD_FERNET: Optional[Fernet] = None


def _get_password_fernet() -> Fernet:
    """Return a singleton Fernet instance configured with PASSWORD_SECRET_KEY."""
    global _PASSWORD_FERNET
    if _PASSWORD_FERNET is None:
        if not PASSWORD_SECRET_KEY:
            raise RuntimeError("AG_PASSWORD_SECRET_KEY must be set before password encryption/decryption")
        key = PASSWORD_SECRET_KEY.encode("utf-8")
        _PASSWORD_FERNET = Fernet(key)
    return _PASSWORD_FERNET


def format_phone(phone: Optional[str]) -> Optional[str]:
    """
    Standardizes phone numbers:
    - Removes '98' prefix if it exists (e.g., 98991... -> 991...)
    - Adds leading '0' if missing (e.g., 912... -> 0912...)
    """
    if not phone:
        return phone

    phone_str = str(phone).strip()

    # Remove 98 prefix if it's there (International format)
    if phone_str.startswith("98") and len(phone_str) > 10:
        phone_str = phone_str[2:]

    # Ensure it starts with 0
    if not phone_str.startswith("0"):
        phone_str = "0" + phone_str

    return phone_str


def encrypt_password(plain_password: str) -> str:
    """
    Encrypt a plain-text password for storage.

    Args:
        plain_password: The user-facing password in plain text.

    Returns:
        Encrypted string suitable for storing in the database.
    """
    if plain_password is None:
        return ""
    fernet = _get_password_fernet()
    token = fernet.encrypt(str(plain_password).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(stored_password: str) -> Optional[str]:
    """
    Decrypt a stored password back to plain text.

    If decryption fails (e.g., value is already plain text or corrupted),
    returns the original value as a fallback, or None on fatal error.
    """
    if not stored_password:
        return None
    fernet = _get_password_fernet()
    try:
        return fernet.decrypt(stored_password.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Probably already plain text or from a previous scheme
        return stored_password
    except Exception as e:
        print(f"[Password] Error decrypting password: {e}")
        return None


# Database configuration
DB_CONFIG = {
    "driver": f"{{{DB_DRIVER.strip('{}')}}}",
    "host": DB_SERVER,
    "database": DB_DATABASE,
    "UID": DB_UID,
    "PWD": DB_PWD,
    "TrustServerCertificate": DB_TRUST_CERT,
}


def get_connection():
    dsn = (f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['host']};"
           f"DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['UID']};"
           f"PWD={DB_CONFIG['PWD']};TrustServerCertificate={DB_CONFIG['TrustServerCertificate']}")
    return pyodbc.connect(dsn)


def migrate():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Rename existing tables to _old to make room for the new schema
    # print("Renaming old tables...")
    # for table in DEFAULT_TABLES:
    #     try:
    #         cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL EXEC sp_rename '{table}', '{table}_old'")
    #     except pyodbc.Error as e:
    #         print(f"Error renaming {table}: {e}")
    # conn.commit()

    # 1. Clean Up: Remove any partially migrated new tables to start fresh
    # We do NOT drop the _old tables.
    print("Dropping existing new tables for a clean start...")
    for table in reversed(DEFAULT_TABLES):  # Reversed to handle potential FK constraints
        try:
            cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
        except pyodbc.Error as e:
            print(f"Error dropping {table}: {e}")
    conn.commit()

    # 2. Recreate the new tables from schema
    print("Creating new tables...")
    for table in DEFAULT_TABLES:
        cursor.execute(TABLE_DEFINITIONS[table])
    conn.commit()

    # 3. Migrate Users - PRESERVING EXACT USER_ID
    print("Migrating users table with Identity Preservation...")
    cursor.execute("SET IDENTITY_INSERT users ON")
    cursor.execute("SELECT * FROM users_old")
    for row in cursor.fetchall():
        formatted_phone = row.phone
        if row.role in ["ins", "sch", "ocon", "con"]:
            formatted_phone = format_phone(row.phone)
        raw_pwd = decrypt_password(row.password) or row.password
        new_pwd = encrypt_password(raw_pwd)
        cursor.execute("""
            INSERT INTO users (user_id, phone, password, role, created_time, edited_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (row.user_id, formatted_phone, new_pwd, row.role, row.DC_Created_Time, row.DC_Edited_Time))
    cursor.execute("SET IDENTITY_INSERT users OFF")
    conn.commit()

    # 4. Migrate Role Tables (ins, sch, ocon)
    # Since these tables in db_creator use user_id as a PRIMARY KEY (not identity),
    # we just insert the value directly.
    for role_table in ['ins', 'sch', 'ocon']:
        print(f"Migrating {role_table} table...")
        cursor.execute(f"SELECT * FROM {role_table}_old")
        columns = [column[0] for column in cursor.description]
        migrated_user_ids = set()

        for row in cursor.fetchall():
            data = dict(zip(columns, row))
            u_id = data['user_id']
            formatted_phone = format_phone(data['phone'])
            if u_id in migrated_user_ids:
                continue

            # verify = 1 for existing users
            fields = ['user_id', 'verify', 'created_time', 'edited_time']
            values = [u_id, 1, data['DC_Created_Time'], data['DC_Edited_Time']]

            if role_table in ['ins', 'sch']:
                fields.extend(['name', 'logo'])
                values.extend([data['name'], data['logo']])
            else:  # ocon
                fields.extend(['first_name', 'last_name', 'logo'])
                values.extend([data['first_name'], data['last_name'], data.get('logo')])

            placeholders = ", ".join(["?"] * len(values))
            try:
                cursor.execute(f"INSERT INTO {role_table} ({', '.join(fields)}) VALUES ({placeholders})", values)
                migrated_user_ids.add(u_id)
            except pyodbc.Error as e:
                print(f"Error migrating {role_table} user {u_id}: {e}")
    conn.commit()

    # 5. Migrate Students (stu) - user_id is PK
    print("Migrating stu table...")
    cursor.execute("SELECT * FROM stu_old")
    for row in cursor.fetchall():
        access_json = json.dumps({"AG": {"permission": 1, "limit": 1}}) if row.permission == 1 else json.dumps(
            {"AG": {"permission": 1, "limit": 0}})

        cursor.execute("""
            INSERT INTO stu (user_id, first_name, last_name, sex, city, access,
                             comment, birth_date, owner_user_id, consultant_user_id, adder_id, editor_id,
                             created_time, edited_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (row.user_id, row.first_name, row.last_name, row.sex, row.city, access_json,
              row.comment, row.birth_date, row.ins_id, row.con_id,
              row.adder_id, row.editor_id, row.DC_Created_Time, row.DC_Edited_Time))
    conn.commit()

    # 6. Migrate Consultants (con) - user_id is PK
    print("Migrating con table...")
    cursor.execute("SELECT * FROM con_old")
    columns = [column[0] for column in cursor.description]
    for row in cursor.fetchall():
        data = dict(zip(columns, row))
        sex_value = data.get('sex', 1)

        cursor.execute("""
            INSERT INTO con (user_id, first_name, last_name, sex,
                             owner_user_id, editor_id,
                             created_time, edited_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['user_id'], data['first_name'], data['last_name'], sex_value,
              data['ins_id'], data['editor_id'],
              data['DC_Created_Time'], data['DC_Edited_Time']))
    conn.commit()

    # 7. Migrate Tokens
    print("Migrating tokens...")
    cursor.execute("SET IDENTITY_INSERT tokens ON")
    cursor.execute("""
        SELECT t.* FROM tokens_old t
    """)
    migrated_token_user_ids = set()
    for row in cursor.fetchall():
        if row.user_id in migrated_token_user_ids: continue
        cursor.execute("""
            INSERT INTO tokens (token_id, token, user_id, created_time, edited_time)
            VALUES (?, ?, ?, ?, ?)
        """, (row.token_id, row.token, row.user_id, row.DC_Created_Time, row.DC_Edited_Time))
        migrated_token_user_ids.add(row.user_id)
    cursor.execute("SET IDENTITY_INSERT tokens OFF")
    conn.commit()

    # 8. Capacity & Packages
    print("Migrating capacity with Identity...")
    cursor.execute("SET IDENTITY_INSERT capacity ON")
    cursor.execute("SELECT c.*, u.phone FROM capacity_old c LEFT JOIN users_old u ON c.user_id = u.user_id")
    for row in cursor.fetchall():
        cursor.execute("""
            INSERT INTO capacity (capacity_id, user_id, created_time, edited_time)
            VALUES (?, ?, ?, ?)
        """, (row.capacity_id, row.user_id, row.DC_Created_Time, row.DC_Edited_Time))

        # capacity_package uses identity for PK, so we don't need SET IDENTITY_INSERT here
        cursor.execute("""
            INSERT INTO capacity_package (capacity_id, package_name, user_id, allowed, used, created_time, edited_time)
            VALUES (?, 'AG', ?, ?, ?, ?, ?)
        """, (row.capacity_id, row.user_id, row.allowed_student, row.used_student,
              row.DC_Created_Time, row.DC_Edited_Time))
        cursor.execute("""
                    INSERT INTO capacity_package (capacity_id, package_name, user_id, allowed, used, created_time, edited_time)
                    VALUES (?, 'SCL', ?, ?, ?, ?, ?)
                """, (row.capacity_id, row.user_id, 0, 0,
                      row.DC_Created_Time, row.DC_Edited_Time))
    cursor.execute("SET IDENTITY_INSERT capacity OFF")
    conn.commit()

    print("Migrating quiz_attempt and quiz_question_answer...")
    cursor.execute("SELECT * FROM quiz_answer_old")
    for row in cursor.fetchall():
        quiz_kind = getattr(row, "quiz_kind", None) or "AG"
        cursor.execute("""
                INSERT INTO quiz_attempt (user_id, quiz_id, quiz_kind, state, owner_user_id, consultant_user_id, created_time, edited_time)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (row.user_id, row.quiz_id, quiz_kind, row.state, row.ins_id, row.con_id,
                  row.DC_Created_Time, row.DC_Edited_Time))
        attempt_id = cursor.fetchone()[0]
        try:
            answers = json.loads(row.answers) if row.answers else {}
        except (TypeError, json.JSONDecodeError):
            answers = {}
        for question_id, answer_value in answers.items():
            try:
                question_id = int(question_id)
            except (TypeError, ValueError):
                continue
            cursor.execute("""
                    INSERT INTO quiz_question_answer
                        (attempt_id, user_id, quiz_kind, quiz_id, question_id, answer_value, created_time, edited_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (attempt_id, row.user_id, quiz_kind, row.quiz_id, question_id,
                      json.dumps(answer_value, ensure_ascii=False), row.DC_Created_Time, row.DC_Edited_Time))
    conn.commit()

    # 9. Migrate remaining tables (scores, result_state, redis_logs, quiz_missing_answers, setting)
    # Note: result_state uses user_id as PK, so no identity insert needed.
    # setting, scores, redis_logs, quiz_missing_answers use Identity for their own IDs.

    identity_tables = {
        "setting": ("setting_id", "setting_old"),
        "scores": ("scores_id", "scores_old"),
        "redis_logs": ("id", "redis_log_old"),
        "quiz_missing_answers": ("id", "error_log_old"),
    }

    for table, (id_col, source_table) in identity_tables.items():
        print(f"Migrating {table} with Identity...")
        cursor.execute(f"SET IDENTITY_INSERT {table} ON")
        cursor.execute(f"SELECT * FROM {source_table}")
        cols = [c[0] for c in cursor.description]
        for row in cursor.fetchall():
            data = dict(zip(cols, row))
            # Map old date names to new date names
            c_time = data.get('DC_Created_Time') or data.get('created_time')
            e_time = data.get('DC_Edited_Time') or data.get('edited_time')

            if table == "setting":
                cursor.execute(
                    f"INSERT INTO {table} ({id_col}, user_id, description, voice, quiz_id, editor_id, created_time, edited_time) VALUES (?,?,?,?,?,?,?,?)",
                    (data[id_col], data['user_id'], data['description'], data['voice'], data['quiz_id'],
                     data['editor_id'], c_time, e_time))
            elif table == "scores":
                cursor.execute(
                    f"INSERT INTO {table} ({id_col}, user_id, quiz_score, brain_fields, brain_categories, brain_branches, created_time, edited_time) VALUES (?,?,?,?,?,?,?,?)",
                    (data[id_col], data['user_id'], data['quiz_score'], data['brain_fields'],
                     data['brain_categories'], data['brain_branches'], c_time, e_time))
            elif table == "redis_logs":
                cursor.execute(
                    f"INSERT INTO {table} ({id_col}, user_id, kind, result, status, phone, created_time, edited_time) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        data[id_col], data['user_id'], "AG", data['result'], data['status'], data['phone'], c_time,
                        e_time))
            elif table == "quiz_missing_answers":
                cursor.execute(
                    f"INSERT INTO {table} ({id_col}, user_id, question_id, created_time, edited_time) VALUES (?,?,?,?,?)",
                    (data[id_col], data['user_id'], data.get('question_id') or data.get('q_id'), c_time, e_time))
        cursor.execute(f"SET IDENTITY_INSERT {table} OFF")

    print("Migrating result_state...")
    cursor.execute("SELECT * FROM result_state_old")
    for row in cursor.fetchall():
        try:
            cursor.execute("""
                INSERT INTO result_state (user_id, t_state, r_state, e_state, a_state, m_state, f_state, i_state, created_time, edited_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (row.user_id, row.t_state, row.r_state, row.e_state, row.a_state, row.m_state, row.f_state,
                  row.i_state, row.DC_Created_Time, row.DC_Edited_Time))
        except:
            pass

    conn.commit()
    print("Migration finished successfully with ID preservation.")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    migrate()
