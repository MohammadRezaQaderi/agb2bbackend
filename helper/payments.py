from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from random import randint
from typing import Mapping, Tuple

from helper.constants import PACKAGES_DATA
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.other import payment_id_exists


def get_payment_id() -> int:
    """Generate a unique payment ID that doesn't exist in the database."""
    while True:
        payment_id = randint(1, 999999)
        with session_scope() as session:
            exists = payment_id_exists(session=session, payment_id=payment_id)
        if not exists:
            return payment_id


def get_price_payment(request_data: Mapping[str, int], discount_percentage: float | None) -> Tuple[int, int, int, int]:
    """
    Calculate total price for AG / SCL packages.

    Args:
        request_data: Dictionary containing package counts, e.g. {"AG": 20, "SCL": 10}
        discount_percentage: Optional discount percentage (0.0 to 100.0).

    Returns:
        Tuple of (total_price, discounted_price, ag_count, scl_count) in Rials.
    """
    counts = {}
    for package_name in ("AG", "SCL"):
        raw_count = request_data.get(package_name, 0)
        if raw_count in (None, ""):
            raw_count = 0
        if type(raw_count) is int:
            count = raw_count
        elif isinstance(raw_count, str) and raw_count.isdecimal():
            count = int(raw_count)
        else:
            raise ValueError(f"Invalid {package_name} package count")
        if count != 0 and count not in PACKAGES_DATA[package_name]:
            raise ValueError(f"Unsupported {package_name} package count")
        counts[package_name] = count

    total = sum(PACKAGES_DATA[name].get(count, 0) for name, count in counts.items()) * 10
    if total <= 0:
        raise ValueError("No valid package selected")

    try:
        percentage = Decimal(str(discount_percentage)) if discount_percentage is not None else Decimal(0)
    except InvalidOperation as exc:
        raise ValueError("Invalid discount percentage") from exc
    if not percentage.is_finite() or not 0 <= percentage <= 100:
        raise ValueError("Invalid discount percentage")

    discounted_total = int((Decimal(total) * (100 - percentage) / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return total, discounted_total, counts["AG"], counts["SCL"]
