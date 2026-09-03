import os
from pathlib import Path

"""
Central configuration for paths and tokens used across the backend.

Values can be overridden via environment variables to adapt to different
deployment environments without changing code.
"""

APP_ENV = os.getenv("AG_ENV", os.getenv("ENV", os.getenv("NODE_ENV", "development"))).strip().lower()
IS_PRODUCTION = APP_ENV in {"prod", "production"}


def _env(name: str, default: str = "", *, required_in_prod: bool = False) -> str:
    value = os.getenv(name)
    if value is not None:
        return value
    if required_in_prod and IS_PRODUCTION:
        raise RuntimeError(f"{name} must be set when AG_ENV={APP_ENV}")
    return default


def _env_int(name: str, default: int, *, required_in_prod: bool = False) -> int:
    return int(_env(name, str(default), required_in_prod=required_in_prod))


# Base path for all file storage
BASE_PATH = _env("AG_BASE_PATH", "D:/WebSites/TestProjects")

# Media / file storage directories
INS_PIC_DIR = _env("AG_INS_PIC_DIR", os.path.join(BASE_PATH, "Media", "InsPic"))
VOICES_DIR = _env("AG_VOICES_DIR", os.path.join(BASE_PATH, "Voices"))
REPORTS_DIR = _env("AG_REPORTS_DIR", os.path.join(BASE_PATH, "Reports"))

PICS_INFO_DIR = _env("AG_PICS_INFO_DIR", os.path.join(BASE_PATH, "Pics", "Info"))
PICS_REPORT_DIR = _env("AG_PICS_REPORT_DIR", os.path.join(BASE_PATH, "Pics", "Report"))
PICS_QUIZ_DIR = _env("AG_PICS_QUIZ_DIR", os.path.join(BASE_PATH, "Pics", "Quiz"))
PICS_FIELD_DIR = _env("AG_PICS_FIELD_DIR", os.path.join(BASE_PATH, "Pics", "Field"))
PICS_WORD_SCL_DIR = _env("AG_PICS_WORD_SCL_DIR", os.path.join(BASE_PATH, "Pics", "Word"))


QUIZ_PIC_DIR = _env("AG_QUIZ_PIC_DIR", os.path.join(BASE_PATH, "Quiz"))

# Default reports
DEFAULT_REPORT_PATH = _env(
    "AG_DEFAULT_REPORT_PATH",
    os.path.join(REPORTS_DIR, "default"),
)
DEFAULT_REPORT2_PATH = _env(
    "AG_DEFAULT_REPORT2_PATH",
    os.path.join(REPORTS_DIR, "default", "Report2.pdf"),
)

# Report templates used by the background scheduler.
REPORT1_TEMPLATE_PATH = Path(
    _env("AG_REPORT1_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report1.docx"))
)
REPORT2_TEMPLATE_PATH = Path(
    _env("AG_REPORT2_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report2.docx"))
)
REPORT3_TEMPLATE_PATH = Path(
    _env("AG_REPORT3_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report3.docx"))
)
REPORT5_TEMPLATE_PATH = Path(
    _env("AG_REPORT5_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report5.docx"))
)
OCD_TEMPLATE_PATH = Path(
    _env("AG_OCD_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "ocd.docx"))
)
ANX_TEMPLATE_PATH = Path(
    _env("AG_ANX_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "anx.docx"))
)
DEP_TEMPLATE_PATH = Path(
    _env("AG_DEP_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "dep.docx"))
)
BRAIN_EXCEL_PATH = Path(
    _env("AG_BRAIN_EXCEL_PATH", str(Path(BASE_PATH) / "FileAG" / "Brain.xlsx"))
)

#! Security-sensitive configuration

# Kavenegar SMS API configuration
KAVENEGAR_API_KEY = _env(
    "AG_KAVENEGAR_API_KEY",
    "",
    required_in_prod=True,
)
KAVENEGAR_OTP_TEMPLATE = _env("AG_KAVENEGAR_OTP_TEMPLATE", "AGOTP")

# Symmetric key used to encrypt/decrypt stored passwords.
# IMPORTANT: In production, override this with a strong, random 32-byte base64 key via env:
#   AG_PASSWORD_SECRET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
PASSWORD_SECRET_KEY = _env(
    "AG_PASSWORD_SECRET_KEY",
    "",
    required_in_prod=True,
)

# Report generation configuration
REPORT_OUTPUT_DIR = _env("AG_REPORT_OUTPUT_DIR", os.path.join(BASE_PATH, "Reports", "exports"))
REPORT_DEFAULT_INS_ID = _env_int("AG_REPORT_DEFAULT_INS_ID", 7017)
REPORT_DEFAULT_CON_ID = _env_int("AG_REPORT_DEFAULT_CON_ID", 11359)


# Redis Configuration
REDIS_HOST = _env("AG_REDIS_HOST", "127.0.0.1")
REDIS_PORT = _env_int("AG_REDIS_PORT", 6379)
REDIS_PASSWORD = _env("AG_REDIS_PASSWORD", "")
REDIS_DB = _env_int("AG_REDIS_DB", 1)
REDIS_CACHE_OTP = str(_env("AG_REDIS_CACHE_OTP", "verify_cache_AG"))
REDIS_QUEUE_NAME = _env("AG_REDIS_QUEUE_NAME", "userAGB2BReport")

# Database Configuration
DB_DRIVER = _env("AG_DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_SERVER = _env("AG_DB_SERVER", "localhost,1433")
DB_DATABASE = _env("AG_DB_DATABASE", "AGB2B_COPY")
DB_UID = _env("AG_DB_UID", "", required_in_prod=True)
DB_PWD = _env("AG_DB_PWD", "", required_in_prod=True)
DB_TRUST_CERT = _env("AG_DB_TRUST_CERT", "yes")

# Database Connection String
DB_CONN_STRING = (
    f'DRIVER={{{DB_DRIVER}}};'
    f'SERVER={DB_SERVER};'
    f'DATABASE={DB_DATABASE};'
    f'UID={DB_UID};'
    f'PWD={DB_PWD};'
    f'TrustServerCertificate={DB_TRUST_CERT}'
)
