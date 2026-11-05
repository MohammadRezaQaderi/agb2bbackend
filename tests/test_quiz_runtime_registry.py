from unittest.mock import Mock

import pytest

from helper.quiz.runtime_provider import get_runtime_provider, resolve_attempt_runtime
from helper.quiz_engine import QuizRuntimeRegistry, StaticQuizRuntimeProvider


def _runtime(package_name="TEST", scoring_version="v1"):
    return StaticQuizRuntimeProvider(
        package_name=package_name,
        scoring_version=scoring_version,
        definition_versions=("definition-v1",),
        required_quiz_count=2,
        scorer=lambda user_id: {"user_id": user_id},
        report_handler="handle_report",
    )


def test_runtime_registry_is_keyed_by_package_and_scoring_version():
    registry = QuizRuntimeRegistry()
    first = _runtime(scoring_version="v1")
    second = _runtime(scoring_version="v2")

    registry.register(first)
    registry.register(second)

    assert registry.get("test", "v1") is first
    assert registry.get("TEST", "v2") is second
    with pytest.raises(ValueError, match="already registered"):
        registry.register(first)


def test_runtime_provider_scores_and_dispatches_reports():
    runtime = _runtime()
    report_service = Mock()
    report_service.handle_report = Mock()

    assert runtime.score_user(42) == {"user_id": 42}
    runtime.generate_report(report_service, "42")

    report_service.handle_report.assert_called_once_with("42", runtime)


def test_builtin_legacy_runtimes_are_registered():
    ag_runtime = get_runtime_provider("AG", "legacy-v1")
    scl_runtime = get_runtime_provider("SCL", "legacy-v1")

    assert ag_runtime.required_quiz_count == 7
    assert scl_runtime.required_quiz_count == 4
    assert ag_runtime.definition_versions == ("legacy-v1",)
    assert scl_runtime.definition_versions == ("legacy-v1",)


def test_attempt_runtime_rejects_mixed_versions():
    with pytest.raises(ValueError, match="Mixed quiz versions"):
        resolve_attempt_runtime(
            "AG",
            [
                {
                    "definition_version": "legacy-v1",
                    "scoring_version": "legacy-v1",
                    "attempt_count": 6,
                },
                {
                    "definition_version": "v2",
                    "scoring_version": "v2",
                    "attempt_count": 1,
                },
            ],
        )


def test_attempt_runtime_resolves_recorded_legacy_version():
    runtime = resolve_attempt_runtime(
        "AG",
        [
            {
                "definition_version": "legacy-v1",
                "scoring_version": "legacy-v1",
                "attempt_count": 7,
            }
        ],
    )

    assert runtime is get_runtime_provider("AG", "legacy-v1")


def test_attempt_runtime_requires_complete_supported_definition():
    with pytest.raises(ValueError, match="Insufficient quiz data"):
        resolve_attempt_runtime(
            "AG",
            [
                {
                    "definition_version": "legacy-v1",
                    "scoring_version": "legacy-v1",
                    "attempt_count": 6,
                }
            ],
        )

    with pytest.raises(ValueError, match="definition version is not supported"):
        resolve_attempt_runtime(
            "AG",
            [
                {
                    "definition_version": "unknown",
                    "scoring_version": "legacy-v1",
                    "attempt_count": 7,
                }
            ],
        )
