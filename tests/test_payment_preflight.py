from contextlib import nullcontext
from unittest.mock import Mock

import pytest

import services.other.other_service as other_service
from helper.payments import get_price_payment


def test_payment_quote_uses_server_prices_not_client_price():
    quote = get_price_payment({"AG": 10, "SCL": "10", "price": 1}, discount_percentage=10)

    assert quote == (32_000_000, 28_800_000, 10, 10)


@pytest.mark.parametrize(
    "payload",
    [
        {"AG": 0, "SCL": 0},
        {"AG": 7},
        {"AG": -10},
        {"AG": 10.5},
        {"AG": True},
        {"AG": "invalid"},
    ],
)
def test_payment_quote_rejects_invalid_package_counts(payload):
    with pytest.raises(ValueError):
        get_price_payment(payload, discount_percentage=None)


@pytest.mark.parametrize("percentage", [-1, 101, "invalid", float("nan"), float("inf")])
def test_payment_quote_rejects_invalid_discount(percentage):
    with pytest.raises(ValueError):
        get_price_payment({"AG": 10}, discount_percentage=percentage)


def test_disabled_payment_does_not_record_discount_usage(monkeypatch):
    discount_lookup = Mock(
        return_value={
            "id": 1,
            "discount_percentage": 10,
            "count": 1,
            "status": "ACTIVE",
            "expire_time": None,
        }
    )
    write_usage = Mock(side_effect=AssertionError("disabled payment wrote discount usage"))
    monkeypatch.setattr(other_service, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(other_service, "get_discount_by_code", discount_lookup)
    monkeypatch.setattr(other_service, "record_discount_usage", write_usage)

    token, data, message = other_service.order_payment(
        {"AG": 10, "SCL": 0, "discount_code": "TEST", "price": 1},
        {"user_id": 1, "phone": "09123456789"},
    )

    assert token is None and data is None
    assert "درگاه پرداخت در دسترس نیست" in message
    discount_lookup.assert_called_once()
    write_usage.assert_not_called()


def test_disabled_payment_rejects_invalid_package_without_writes(monkeypatch):
    session_scope = Mock(side_effect=AssertionError("invalid payment opened a database transaction"))
    monkeypatch.setattr(other_service, "session_scope", session_scope)

    token, data, message = other_service.order_payment(
        {"AG": 7, "SCL": 0},
        {"user_id": 1, "phone": "09123456789"},
    )

    assert token is None and data is None
    assert "تعداد بسته‌ها" in message
    session_scope.assert_not_called()


@pytest.mark.parametrize(
    ("status", "count"),
    [("expired", 1), ("EXPIRED", 1), ("ACTIVE", 0), ("ACTIVE", -1)],
)
def test_discount_rejection_is_consistent_for_preview_and_order(monkeypatch, status, count):
    monkeypatch.setattr(other_service, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(
        other_service,
        "get_discount_by_code",
        Mock(
            return_value={
                "id": 1,
                "discount_percentage": 0.1,
                "count": count,
                "status": status,
                "expire_time": None,
            }
        ),
    )
    write_usage = Mock(side_effect=AssertionError("rejected discount wrote usage"))
    monkeypatch.setattr(other_service, "record_discount_usage", write_usage)
    user_info = {"user_id": 1, "phone": "09123456789"}

    preview = other_service.apply_discount({"discount_code": "TEST", "total_value": 1000}, user_info)
    order = other_service.order_payment({"AG": 10, "discount_code": "TEST"}, user_info)

    assert preview[0] is None and preview[1] is None
    assert order[0] is None and order[1] is None
    assert preview[2] == order[2]
    write_usage.assert_not_called()
