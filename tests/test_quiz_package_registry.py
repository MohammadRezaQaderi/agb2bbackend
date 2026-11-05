import pytest

from helper.quiz.quiz_data_extractor import (
    get_definition_version,
    get_last_question_id,
    get_private_quiz_info,
    get_quiz_info,
    get_quiz_name,
    get_quiz_table_info,
)
from helper.quiz_engine import QuizPackageRegistry, StaticQuizPackageProvider


def _provider(package_name="TEST"):
    return StaticQuizPackageProvider(
        package_name=package_name,
        definition_version="v1",
        quizzes=[
            {
                "quiz_id": 1,
                "sections": [
                    {"section_id": 1, "questions": [{"question_id": 10}, {"question_id": 11}]},
                ],
            }
        ],
        quiz_summaries=[{"id": 1, "quizName": "Test quiz"}],
    )


def test_static_provider_exposes_versioned_quiz_content():
    provider = _provider("new-package")

    assert provider.package_name == "NEW-PACKAGE"
    assert provider.definition_version == "v1"
    assert provider.get_quiz(1)["quiz_id"] == 1
    assert provider.get_quiz_name(1) == "Test quiz"
    assert provider.get_last_question_id() == 11


def test_public_quiz_is_isolated_and_omits_private_question_fields():
    private_quiz = {
        "quiz_id": 1,
        "description": "Original",
        "sections": [
            {
                "section_id": 1,
                "questions": [
                    {"question_id": 10, "question_answer": [2], "first_question": "Question"},
                ],
            }
        ],
    }
    provider = StaticQuizPackageProvider(
        package_name="TEST",
        definition_version="v1",
        quizzes=[private_quiz],
        quiz_summaries=[{"id": 1, "quizName": "Test quiz"}],
    )

    public_quiz = provider.get_public_quiz(1)
    public_quiz["description"] = "Customized"

    assert "question_answer" not in public_quiz["sections"][0]["questions"][0]
    assert provider.get_quiz(1)["sections"][0]["questions"][0]["question_answer"] == [2]
    assert provider.get_quiz(1)["description"] == "Original"


def test_static_provider_rejects_mismatched_quiz_and_summary_ids():
    with pytest.raises(ValueError, match="IDs do not match"):
        StaticQuizPackageProvider(
            package_name="TEST",
            definition_version="v1",
            quizzes=[{"quiz_id": 1, "sections": []}],
            quiz_summaries=[{"id": 2, "quizName": "Wrong ID"}],
        )


def test_registry_rejects_duplicate_package_registration():
    registry = QuizPackageRegistry()
    registry.register(_provider())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_provider())


def test_legacy_packages_are_available_through_registry_boundary():
    assert len(get_quiz_table_info("AG")) == 7
    assert len(get_quiz_table_info("SCL")) == 4
    assert get_quiz_info(1, "AG")["quiz_id"] == 1
    assert get_quiz_info(1, "SCL")["quiz_id"] == 1
    assert get_quiz_name(1, "AG") == "کتل"
    assert get_quiz_name(1, "SCL") == "زندگی شخصی"
    assert get_last_question_id("AG") is not None
    assert get_last_question_id("SCL") is not None
    assert get_definition_version("AG") == "legacy-v1"
    assert get_definition_version("SCL") == "legacy-v1"


def test_legacy_public_quizzes_do_not_expose_answer_keys():
    for kind in ("AG", "SCL"):
        for summary in get_quiz_table_info(kind):
            quiz_id = summary["id"]
            public_quiz = get_quiz_info(quiz_id, kind)
            private_quiz = get_private_quiz_info(quiz_id, kind)

            assert public_quiz is not private_quiz
            assert any(
                "question_answer" in question
                for section in private_quiz["sections"]
                for question in section["questions"]
            )
            assert all(
                "question_answer" not in question
                for section in public_quiz["sections"]
                for question in section["questions"]
            )


def test_unknown_package_does_not_expose_full_quiz_content():
    assert get_quiz_info(1, "UNKNOWN") is None
    assert get_quiz_name(1, "UNKNOWN") is None
    assert get_last_question_id("UNKNOWN") is None
    assert get_definition_version("UNKNOWN") is None
