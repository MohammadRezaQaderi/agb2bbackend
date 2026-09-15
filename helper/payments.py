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
    total = 0

    ag_count = int(request_data.get("AG", 0) or 0)
    if ag_count in PACKAGES_DATA.get("AG", {}):
        total += PACKAGES_DATA["AG"][ag_count]

    scl_count = int(request_data.get("SCL", 0) or 0)
    if scl_count in PACKAGES_DATA.get("SCL", {}):
        total += PACKAGES_DATA["SCL"][scl_count]

    total = total * 10

    if discount_percentage:
        new_value = round(total * (100 - float(discount_percentage)) / 100)
    else:
        new_value = total

    return total, new_value, ag_count, scl_count
