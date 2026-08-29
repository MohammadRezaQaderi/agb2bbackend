from __future__ import annotations

import json
from typing import Any


def _safe_product_data(raw_product_data: Any) -> dict[str, Any]:
    try:
        product_data = json.loads(raw_product_data) if raw_product_data else {}
    except (json.JSONDecodeError, TypeError):
        product_data = {}

    return {
        "packages": product_data.get("packages", {}),
        "product_name": product_data.get("product_name", ""),
        "discount_price": product_data.get("discount_price", 0),
        "price": product_data.get("price", 0),
    }


def build_transaction_list_response(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": transaction.get("id"),
            "state": transaction.get("state"),
            "status": transaction.get("status"),
            "product_data": _safe_product_data(transaction.get("product_data")),
            "result": transaction.get("result"),
            "date": transaction.get("date"),
        }
        for transaction in transactions
    ]
