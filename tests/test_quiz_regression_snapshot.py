import ast
import hashlib
import json
from collections import Counter
from contextlib import nullcontext
from pathlib import Path

from helper.quiz import check_score, report_info, scl_report_info
from helper.quiz.ag_answer_info import quiz_labels as ag_labels
from helper.quiz.ag_answer_info import quiz_questions_answer_schema as ag_schema
from helper.quiz.quiz_data_extractor import get_definition_version
from helper.quiz.scl_answer_info import quiz_labels as scl_labels
from helper.quiz.scl_answer_info import quiz_questions_answer_schema as scl_schema
from helper.quiz_engine.registry import quiz_package_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "quiz_regression" / "legacy_v1.json"


def _digest(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _package_snapshot(kind):
    provider = quiz_package_registry.get(kind)
    quizzes = provider.list_quizzes()
    summaries = provider.list_quiz_summaries()
    sections = [section for quiz in quizzes for section in quiz.get("sections", [])]
    questions = [question for section in sections for question in section.get("questions", [])]
    answers = [answer for question in questions for answer in question.get("answers", [])]

    return {
        "definition_version": get_definition_version(kind),
        "quiz_count": len(quizzes),
        "section_count": len(sections),
        "question_count": len(questions),
        "answer_count": len(answers),
        "quiz_ids": [quiz["quiz_id"] for quiz in quizzes],
        "question_id_min": min(question["question_id"] for question in questions),
        "question_id_max": max(question["question_id"] for question in questions),
        "quiz_question_counts": {
            str(quiz["quiz_id"]): sum(
                len(section.get("questions", [])) for section in quiz.get("sections", [])
            )
            for quiz in quizzes
        },
        "definition_sha256": _digest(quizzes),
        "summary_sha256": _digest(summaries),
    }


def _first_valid_answers(schema):
    answers = {}
    for question in schema:
        values = question.get("first_field_values") or {}
        if question.get("kind") == "ca":
            selected = [key for key, value in values.items() if value == 1]
        else:
            selected = [next(iter(values))] if values else []
        answers[str(question["question_id"])] = selected
    return answers


def _ag_scoring_snapshot(monkeypatch):
    answers = _first_valid_answers(ag_schema)
    monkeypatch.setattr(check_score, "session_scope", lambda: nullcontext(object()))
    monkeypatch.setattr(check_score, "get_student_birth_date", lambda **kwargs: None)
    monkeypatch.setattr(check_score.answer_store, "get_completed_count", lambda *args: 7)
    monkeypatch.setattr(check_score.answer_store, "get_answers_for_user_kind", lambda *args: answers)

    result = check_score.ag_score_computation(user_id=1, user_age=14)
    labels = result[0]
    return {
        "label_count": len(ag_labels),
        "schema_count": len(ag_schema),
        "kind_counts": dict(sorted(Counter(question["kind"] for question in ag_schema).items())),
        "labels_sha256": _digest(ag_labels),
        "schema_sha256": _digest(ag_schema),
        "all_first_answers_result_sha256": _digest(result),
        "selected_result": {
            key: labels[key]
            for key in ("CATEL", "IQ_Number", "CATEL_Brain", "Realistic", "Linguistic_verbal")
        },
        "answer_stats": list(result[1:]),
    }


def _scl_scoring_snapshot():
    result = check_score.score_computation_scl(_first_valid_answers(scl_schema))
    labels = result[0]
    return {
        "label_count": len(scl_labels),
        "schema_count": len(scl_schema),
        "kind_counts": dict(sorted(Counter(question["kind"] for question in scl_schema).items())),
        "labels_sha256": _digest(scl_labels),
        "schema_sha256": _digest(scl_schema),
        "all_first_answers_result_sha256": _digest(result),
        "selected_result": {
            key: labels[key] for key in ("generalSE", "aggSCL90", "anSCL90", "OCD")
        },
        "missing_count": len(result[1]),
    }


def _ag_report_snapshot():
    report_path = PROJECT_ROOT / "helper" / "quiz" / "report_info.py"
    report_tree = ast.parse(report_path.read_text())
    function_trees = [
        ast.dump(node, include_attributes=False)
        for node in report_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    iq_boundaries = {
        str(score): report_info.catel_info(score)
        for score in (35, 52, 68, 90, 100, 110, 120, 132, 148, 164)
    }
    return {
        "static_data_sha256": _digest(
            {"catel_data": report_info.catel_data, "holland_color": report_info.holland_color}
        ),
        "function_ast_sha256": _digest(function_trees),
        "iq_boundaries_sha256": _digest(iq_boundaries),
    }


def _scl_report_snapshot():
    range_results = {}
    for label, ranges in scl_report_info._REPORT_DATA.items():
        for range_text in ranges:
            low, high = (float(part) for part in range_text.split("-", 1))
            range_results[f"{label}:{range_text}"] = scl_report_info.get_report_text(
                label, (low + high) / 2
            )
    return {
        "report_data_count": len(scl_report_info._REPORT_DATA),
        "report_data_sha256": _digest(scl_report_info._REPORT_DATA),
        "range_results_sha256": _digest(range_results),
    }


def test_published_legacy_v1_quiz_behavior_is_unchanged(monkeypatch):
    expected = json.loads(FIXTURE_PATH.read_text())
    actual = {
        "format_version": 1,
        "packages": {kind: _package_snapshot(kind) for kind in ("AG", "SCL")},
        "scoring": {
            "AG": _ag_scoring_snapshot(monkeypatch),
            "SCL": _scl_scoring_snapshot(),
        },
        "reports": {
            "AG": _ag_report_snapshot(),
            "SCL": _scl_report_snapshot(),
        },
    }

    assert actual["packages"] == expected["packages"]
    assert actual["scoring"] == expected["scoring"]
    assert actual["reports"] == expected["reports"]
