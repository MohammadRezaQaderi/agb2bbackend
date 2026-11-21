import json
from unittest.mock import Mock, patch

import pytest

from scheduler import adder


def test_phone_candidates_supports_iranian_formats():
    assert adder.phone_candidates("۰۹۱۲-۳۴۵-۶۷۸۹") == ("09123456789",)
    assert adder.phone_candidates("+98 912 345 6789") == ("+989123456789", "09123456789")
    assert adder.phone_candidates("9123456789") == ("9123456789", "09123456789")


def test_queue_payload_matches_scheduler_contract():
    assert json.loads(adder.build_queue_payload(42, "ag")) == {
        "user_id": "42",
        "kind": "AG",
    }


def test_enqueue_report_validates_and_creates_log():
    student = {
        "user_id": 42,
        "phone": "09123456789",
        "first_name": "Test",
        "last_name": "Student",
    }
    runtime = Mock(scoring_version="legacy-v1")
    redis_client = Mock()
    redis_client.rpush.return_value = 3
    session = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=session)
    context.__exit__ = Mock(return_value=False)

    with patch.object(adder, "session_scope", side_effect=[context, context]):
        with patch.object(adder, "get_scheduler_student_context", return_value=student):
            with patch.object(adder, "list_completed_attempt_versions", return_value=[{"attempt_count": 7}]):
                with patch.object(adder, "resolve_attempt_runtime", return_value=runtime):
                    with patch.object(adder, "create_redis_log") as create_log:
                        result = adder.enqueue_report(user_id=42, kind="AG", redis_client=redis_client)

    payload = json.loads(redis_client.rpush.call_args.args[1])
    assert payload == {"user_id": "42", "kind": "AG"}
    assert result["queue_length"] == 3
    create_log.assert_called_once_with(
        session=session,
        user_id=42,
        kind="AG",
        result="user manually added to queue to create report",
        phone="09123456789",
    )


def test_enqueue_report_dry_run_does_not_touch_redis():
    student = {
        "user_id": 42,
        "phone": "09123456789",
        "first_name": "Test",
        "last_name": "Student",
    }
    runtime = Mock(scoring_version="legacy-v1")
    context = Mock()
    context.__enter__ = Mock(return_value=Mock())
    context.__exit__ = Mock(return_value=False)

    with patch.object(adder, "session_scope", return_value=context):
        with patch.object(adder, "get_scheduler_student_context", return_value=student):
            with patch.object(adder, "list_completed_attempt_versions", return_value=[{"attempt_count": 7}]):
                with patch.object(adder, "resolve_attempt_runtime", return_value=runtime):
                    result = adder.enqueue_report(user_id=42, kind="AG", dry_run=True)

    assert result["dry_run"] is True
    assert "queue_length" not in result


@pytest.mark.parametrize(
    ("user_id", "phone"),
    [(None, None), (42, "09123456789")],
)
def test_enqueue_report_requires_one_identifier(user_id, phone):
    with pytest.raises(ValueError, match="exactly one"):
        adder.enqueue_report(user_id=user_id, phone=phone)
