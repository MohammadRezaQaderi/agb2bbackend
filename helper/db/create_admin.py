"""
Create or rotate an admin API token without storing the raw token.

Usage:
    python helper/db/create_admin.py --name admin_1 --token "raw-admin-token"
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if sys.path and sys.path[0] == SCRIPT_DIR:
    sys.path.pop(0)
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.models import Admin


def admin_token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def upsert_admin(name: str, token: str, status: str) -> str:
    with session_scope() as session:
        admin = session.execute(
            select(Admin).where(Admin.admin_name == name).limit(1)
        ).scalars().first()

        if admin:
            admin.token_hash = admin_token_hash(token)
            admin.status = status
            admin.edited_time = datetime.now()
            return "updated"

        session.add(
            Admin(
                admin_name=name,
                token_hash=admin_token_hash(token),
                status=status,
                created_by="create_admin.py",
            )
        )
        return "created"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or rotate an admin API token.")
    parser.add_argument("--name", required=True, help="Admin display/name key, for example admin_1.")
    parser.add_argument("--token", required=True, help="Raw token to hash and store.")
    parser.add_argument("--status", default="active", choices=["active", "disabled"], help="Admin status.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = upsert_admin(name=args.name, token=args.token, status=args.status)
    print(f"Admin '{args.name}' {result}; raw token was not stored.")


if __name__ == "__main__":
    main()
