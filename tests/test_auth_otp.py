import json
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from redis.exceptions import WatchError

import services.auth.auth_service as auth_service
from helper.otp.otp_cache import consume_otp, store_otp


class FakePipeline:
    def __init__(self, cache):
        self.cache = cache

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def watch(self, _key):
        self.version = self.cache.version

    def multi(self):
        pass

    def delete(self, _key):
        pass

    def execute(self):
        if self.version != self.cache.version:
            raise WatchError("key changed")
        self.cache.record = None
        self.cache.version += 1


class FakeCache:
    def __init__(self):
        self.database = self
        self.record = None
        self.timeout = None
        self.version = 0

    def make_key(self, phone):
        return f"otp:{phone}"

    def get(self, _phone):
        return self.record

    def set(self, _phone, value, timeout):
        self.record = value
        self.timeout = timeout
        self.version += 1

    def pipeline(self):
        return FakePipeline(self)


@pytest.fixture
def otp_cache():
    return FakeCache()


def test_otp_is_typed_short_lived_and_consumed_only_once(otp_cache):
    store_otp(otp_cache, "09123456789", 12345, "verify", 300)

    assert otp_cache.timeout == 300
    assert json.loads(otp_cache.record) == {"code": 12345, "type": "verify"}
    assert consume_otp(otp_cache, "09123456789", "12345", "otp") == "invalid"
    assert consume_otp(otp_cache, "09123456789", "11111", "verify") == "invalid"
    assert consume_otp(otp_cache, "09123456789", "12345", "verify") == "consumed"
    assert consume_otp(otp_cache, "09123456789", "12345", "verify") == "missing"


def test_legacy_otp_requires_resend(otp_cache):
    otp_cache.record = json.dumps({"code": 12345})

    assert consume_otp(otp_cache, "09123456789", "12345", "verify") == "missing"


def test_concurrent_change_cannot_consume_newer_otp(otp_cache, monkeypatch):
    store_otp(otp_cache, "09123456789", 12345, "otp", 300)
    original_get = otp_cache.get

    def changed_get(phone):
        old_record = original_get(phone)
        store_otp(otp_cache, phone, 99999, "otp", 300)
        return old_record

    monkeypatch.setattr(otp_cache, "get", changed_get)

    assert consume_otp(otp_cache, "09123456789", "12345", "otp") == "missing"
    assert json.loads(otp_cache.record)["code"] == 99999


def test_send_otp_provider_failure_keeps_previous_code(monkeypatch, otp_cache):
    store_otp(otp_cache, "09123456789", 12345, "verify", 300)
    redis_db = Mock()
    redis_db.cache.return_value = otp_cache
    monkeypatch.setattr(auth_service, "is_valid_mobile", Mock(return_value=True))
    monkeypatch.setattr(auth_service, "check_security_code", Mock(return_value=True))
    monkeypatch.setattr(auth_service, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(
        auth_service,
        "get_user_identity_by_phone",
        Mock(return_value={"user_id": 1, "phone": "09123456789", "role": "ins"}),
    )
    monkeypatch.setattr(auth_service, "get_role_verify_status", Mock(return_value=0))
    monkeypatch.setattr(auth_service.otp_helper, "send_otp_message", Mock(return_value=None))
    monkeypatch.setattr(auth_service, "random_generate_otp_code", Mock(return_value=99999))

    token, data, message = auth_service.send_otp(
        redis_db,
        {"phone": "09123456789", "code": "x", "check": "x", "type": "verify"},
    )

    assert token is None and data is None
    assert "پیامک ارسال نشد" in message
    assert json.loads(otp_cache.record)["code"] == 12345
    assert otp_cache.timeout == 300


def test_send_otp_success_replaces_code_with_short_expiry(monkeypatch, otp_cache):
    store_otp(otp_cache, "09123456789", 12345, "verify", 300)
    redis_db = Mock()
    redis_db.cache.return_value = otp_cache
    monkeypatch.setattr(auth_service, "is_valid_mobile", Mock(return_value=True))
    monkeypatch.setattr(auth_service, "check_security_code", Mock(return_value=True))
    monkeypatch.setattr(auth_service, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(
        auth_service,
        "get_user_identity_by_phone",
        Mock(return_value={"user_id": 1, "phone": "09123456789", "role": "ins"}),
    )
    send_message = Mock(return_value={"status": "sent"})
    monkeypatch.setattr(auth_service.otp_helper, "send_otp_message", send_message)
    monkeypatch.setattr(auth_service, "random_generate_otp_code", Mock(return_value=99999))
    monkeypatch.setattr(auth_service, "get_tracking_code", Mock(return_value="tracking"))

    token, data, message = auth_service.send_otp(
        redis_db,
        {"phone": "09123456789", "code": "x", "check": "x", "type": "otp"},
    )

    assert (token, data, message) == ("tracking", {"phone": "09123456789"}, "")
    assert json.loads(otp_cache.record) == {"code": 99999, "type": "otp"}
    assert otp_cache.timeout == auth_service.OTP_TTL_SECONDS
    send_message.assert_called_once_with(code=99999, phone="09123456789", type="OTP")


def test_signup_provider_failure_keeps_unverified_account_for_resend(monkeypatch, otp_cache):
    redis_db = Mock()
    redis_db.cache.return_value = otp_cache
    create_account = Mock()
    monkeypatch.setattr(auth_service, "is_valid_mobile", Mock(return_value=True))
    monkeypatch.setattr(auth_service, "password_format_check", Mock(return_value=(True, "")))
    monkeypatch.setattr(auth_service, "user_phone_exists", Mock(return_value=False))
    monkeypatch.setattr(auth_service, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(auth_service, "encrypt_password", Mock(return_value="encrypted"))
    monkeypatch.setattr(auth_service, "create_signup_account", create_account)
    monkeypatch.setattr(auth_service, "random_generate_otp_code", Mock(return_value=12345))
    monkeypatch.setattr(auth_service.otp_helper, "send_otp_message", Mock(return_value=None))

    token, data, message = auth_service.sign_up(
        redis_db,
        {"phone": "09123456789", "password": "password", "re_password": "password", "role": "ins"},
    )

    assert token is None and data is None
    assert "حساب ثبت شد" in message
    create_account.assert_called_once()
    assert otp_cache.record is None


def test_check_otp_success_cannot_issue_second_token(monkeypatch, otp_cache):
    store_otp(otp_cache, "09123456789", 12345, "otp", 300)
    redis_db = Mock()
    redis_db.cache.return_value = otp_cache
    monkeypatch.setattr(auth_service, "session_scope", lambda: nullcontext(Mock()))
    monkeypatch.setattr(
        auth_service,
        "get_user_auth_by_phone",
        Mock(return_value={"user_id": 1, "phone": "09123456789", "role": "ins"}),
    )
    create_token = Mock(return_value="token")
    monkeypatch.setattr(auth_service, "_create_token", create_token)
    monkeypatch.setattr(
        auth_service.institute_service,
        "get_info",
        Mock(return_value=("tracking", {"user_id": 1}, "")),
    )
    payload = {"phone": "09123456789", "code": "12345", "type": "otp"}

    assert auth_service.check_otp(redis_db, payload) == ("token", {"user_id": 1}, "")
    second_token, _, message = auth_service.check_otp(redis_db, payload)

    assert second_token is None and "منقضی" in message
    create_token.assert_called_once()
