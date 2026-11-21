"""Shared data-driven scoring for compiled PSY packages."""

from collections.abc import Mapping
from typing import Any

from helper.quiz_engine.registry import normalize_package_name
from quiz_packages.psy.provider import load_packages


def _selected_answers(value: Any) -> list[int]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    selected = []
    for item in values:
        try:
            selected.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid answer ID: {item!r}") from exc
    return selected


def score_answers(
    package_name: str,
    answers: Mapping[str | int, Any],
    *,
    generated_module: str | None = None,
) -> tuple[dict[str, int | float], list[int]]:
    generated = load_packages(generated_module) if generated_module else load_packages()
    normalized_name = normalize_package_name(package_name)
    try:
        package = generated.PACKAGES[normalized_name]
    except KeyError as exc:
        raise ValueError(f"unknown PSY package: {normalized_name}") from exc

    scores = {scale: 0 for scale in package["subscale_labels"]}
    normalized_answers = {str(question_id): value for question_id, value in answers.items()}
    missing_questions = []

    for question in package["scoring_questions"]:
        question_id = question["question_id"]
        selected = _selected_answers(normalized_answers.get(str(question_id)))
        if not selected:
            missing_questions.append(question_id)
            continue
        for answer_id in selected:
            try:
                contributions = question["answers"][answer_id]
            except KeyError as exc:
                raise ValueError(f"question {question_id} has no answer {answer_id}") from exc
            for scale, value in contributions:
                scores[scale] += value

    return scores, missing_questions
