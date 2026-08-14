import os
from pathlib import Path

"""
Central configuration for paths and tokens used across the backend.

Values can be overridden via environment variables to adapt to different
deployment environments without changing code.
"""

# Base path for all file storage
BASE_PATH = os.getenv("AG_BASE_PATH", "D:/WebSites/AGB2B")

# Media / file storage directories
INS_PIC_DIR = os.getenv("AG_INS_PIC_DIR", os.path.join(BASE_PATH, "Media", "InsPic"))
VOICES_DIR = os.getenv("AG_VOICES_DIR", os.path.join(BASE_PATH, "Voices"))
REPORTS_DIR = os.getenv("AG_REPORTS_DIR", os.path.join(BASE_PATH, "Reports"))

PICS_INFO_DIR = os.getenv("AG_PICS_INFO_DIR", os.path.join(BASE_PATH, "Pics", "Info"))
PICS_REPORT_DIR = os.getenv("AG_PICS_REPORT_DIR", os.path.join(BASE_PATH, "Pics", "Report"))
PICS_QUIZ_DIR = os.getenv("AG_PICS_QUIZ_DIR", os.path.join(BASE_PATH, "Pics", "Quiz"))
PICS_FIELD_DIR = os.getenv("AG_PICS_FIELD_DIR", os.path.join(BASE_PATH, "Pics", "Field"))
PICS_WORD_SCL_DIR = os.getenv("AG_PICS_WORD_SCL_DIR", os.path.join(BASE_PATH, "Pics", "Word"))


QUIZ_PIC_DIR = os.getenv("AG_QUIZ_PIC_DIR", os.path.join(BASE_PATH, "Quiz"))

# Default reports
DEFAULT_REPORT_PATH = os.getenv(
    "AG_DEFAULT_REPORT_PATH",
    os.path.join(REPORTS_DIR, "default"),
)
DEFAULT_REPORT2_PATH = os.getenv(
    "AG_DEFAULT_REPORT2_PATH",
    os.path.join(REPORTS_DIR, "default", "Report2.pdf"),
)

# Report templates used by the background scheduler.
REPORT1_TEMPLATE_PATH = Path(
    os.getenv("AG_REPORT1_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report1.docx"))
)
REPORT2_TEMPLATE_PATH = Path(
    os.getenv("AG_REPORT2_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report2.docx"))
)
REPORT3_TEMPLATE_PATH = Path(
    os.getenv("AG_REPORT3_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report3.docx"))
)
REPORT5_TEMPLATE_PATH = Path(
    os.getenv("AG_REPORT5_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "Report5.docx"))
)
OCD_TEMPLATE_PATH = Path(
    os.getenv("AG_OCD_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "ocd.docx"))
)
ANX_TEMPLATE_PATH = Path(
    os.getenv("AG_ANX_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "anx.docx"))
)
DEP_TEMPLATE_PATH = Path(
    os.getenv("AG_DEP_TEMPLATE_PATH", str(Path(BASE_PATH) / "FileAG" / "dep.docx"))
)
BRAIN_EXCEL_PATH = Path(
    os.getenv("AG_BRAIN_EXCEL_PATH", str(Path(BASE_PATH) / "FileAG" / "Brain.xlsx"))
)

# Developer token (for internal/testing use)
DEVELOP_TOKEN = os.getenv(
    "AG_DEVELOP_TOKEN",
    "eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoiQWRtaW4iLCJJc3N1ZXIiOiIwMUZhcmRha2hlaWxpc2FieiIsIlVzZXJuYW1lIjoiTXJxMjciLCJleHAiOjE3NTMwODc5NzcsImlhdCI6MTc1MzA4Nzk3N30.mlcxgBMXIjmw04DPeMkSL5Ijqlg-ifZXQnw_d889qvM",
)

#! Security-sensitive configuration

# Kavenegar SMS API configuration
KAVENEGAR_API_KEY = os.getenv(
    "AG_KAVENEGAR_API_KEY",
    "5345574F44473868686938596E4744536C4E335232506B72687A376C6C743949666335584E727A653938343D",
)
KAVENEGAR_OTP_TEMPLATE = os.getenv("AG_KAVENEGAR_OTP_TEMPLATE", "AGOTP")

# Symmetric key used to encrypt/decrypt stored passwords.
# IMPORTANT: In production, override this with a strong, random 32-byte base64 key via env:
#   AG_PASSWORD_SECRET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
PASSWORD_SECRET_KEY = os.getenv(
    "AG_PASSWORD_SECRET_KEY",
    "8q2F8J7x1a6F1C5B8L3q6N2v9R4s7W0yF1z3X6C8q2M=",  # default dev key, override in prod
)

# Report generation configuration
REPORT_OUTPUT_DIR = os.getenv("AG_REPORT_OUTPUT_DIR", os.path.join(BASE_PATH, "Reports", "exports"))
REPORT_DEFAULT_INS_ID = int(os.getenv("AG_REPORT_DEFAULT_INS_ID", "7017"))
REPORT_DEFAULT_CON_ID = int(os.getenv("AG_REPORT_DEFAULT_CON_ID", "11359"))


# Redis Configuration
REDIS_HOST = os.getenv("AG_REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("AG_REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("AG_REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("AG_REDIS_DB", "1"))
REDIS_CACHE_OTP = str(os.getenv("AG_REDIS_CACHE_OTP", "verify_cache_AG"))
REDIS_QUEUE_NAME = os.getenv("AG_REDIS_QUEUE_NAME", "userAGB2BReport")

# Database Configuration
DB_DRIVER = os.getenv("AG_DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_SERVER = os.getenv("AG_DB_SERVER", "localhost,1433")
DB_DATABASE = os.getenv("AG_DB_DATABASE", "AGB2B")
DB_UID = os.getenv("AG_DB_UID", "mgh27")
DB_PWD = os.getenv("AG_DB_PWD", "m2711gH9985")
DB_TRUST_CERT = os.getenv("AG_DB_TRUST_CERT", "yes")

# Database Connection String
DB_CONN_STRING = (
    f'DRIVER={{{DB_DRIVER}}};'
    f'SERVER={DB_SERVER};'
    f'DATABASE={DB_DATABASE};'
    f'UID={DB_UID};'
    f'PWD={DB_PWD};'
    f'TrustServerCertificate={DB_TRUST_CERT}'
)
