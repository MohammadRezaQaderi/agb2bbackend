import pytest

from helper.quiz import (
    ag_answer_info,
    ag_quiz_data_info,
    bookmarks_info,
    report_info,
    scl_answer_info,
    scl_quiz_data_info,
    scl_report_info,
)
from helper.quiz.quiz_data_extractor import (
    get_definition_version,
    get_last_question_id,
    get_private_quiz_info,
    get_quiz_info,
    get_quiz_name,
    get_quiz_table_info,
    get_scoring_version,
)
from helper.quiz_engine import QuizPackageRegistry, StaticQuizPackageProvider
from quiz_packages.ag.legacy_v1 import questions as ag_questions
from quiz_packages.ag.legacy_v1 import reports as ag_reports
from quiz_packages.ag.legacy_v1 import scoring as ag_scoring
from quiz_packages.scl.legacy_v1 import questions as scl_questions
from quiz_packages.scl.legacy_v1 import report_bookmarks as scl_report_bookmarks
from quiz_packages.scl.legacy_v1 import reports as scl_reports
from quiz_packages.scl.legacy_v1 import scoring as scl_scoring


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
    assert provider.scoring_version == "v1"
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
    assert public_quiz["sections"][0]["questions"][0]["is_example"] is True
    assert public_quiz["sections"][0]["questions"][0]["example_answer"] == [2]
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
    assert get_scoring_version("AG") == "legacy-v1"
    assert get_scoring_version("SCL") == "legacy-v1"


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


def test_cattell_examples_expose_only_their_demonstrated_answers():
    public_quiz = get_quiz_info(1, "AG")
    private_quiz = get_private_quiz_info(1, "AG")

    public_questions = {
        question["question_id"]: question for section in public_quiz["sections"] for question in section["questions"]
    }
    private_examples = {
        question["question_id"]: question["question_answer"]
        for section in private_quiz["sections"]
        for question in section["questions"]
        if isinstance(question.get("question_answer"), list) and question["question_answer"]
    }

    assert private_examples
    for question_id, example_answer in private_examples.items():
        assert public_questions[question_id]["is_example"] is True
        assert public_questions[question_id]["example_answer"] == example_answer

    assert all(
        "example_answer" not in question
        for question_id, question in public_questions.items()
        if question_id not in private_examples
    )


def test_unknown_package_does_not_expose_full_quiz_content():
    assert get_quiz_info(1, "UNKNOWN") is None
    assert get_quiz_name(1, "UNKNOWN") is None
    assert get_last_question_id("UNKNOWN") is None
    assert get_definition_version("UNKNOWN") is None
    assert get_scoring_version("UNKNOWN") is None


def test_legacy_quiz_module_paths_reexport_versioned_package_content():
    assert ag_quiz_data_info.ag_quiz_info is ag_questions.ag_quiz_info
    assert ag_answer_info.quiz_questions_answer_schema is ag_scoring.quiz_questions_answer_schema
    assert report_info.catel_info is ag_reports.catel_info
    assert scl_quiz_data_info.scl_quiz_info is scl_questions.scl_quiz_info
    assert scl_answer_info.quiz_questions_answer_schema is scl_scoring.quiz_questions_answer_schema
    assert scl_report_info.get_report_text is scl_reports.get_report_text
    assert bookmarks_info.CALC_DATA is scl_report_bookmarks.CALC_DATA
