"""Provider for versioned quiz definitions stored in Python modules."""

from collections.abc import Sequence
from typing import Any

from helper.quiz_engine.registry import normalize_package_name


QuizData = dict[str, Any]


class StaticQuizPackageProvider:
    def __init__(
        self,
        *,
        package_name: str,
        definition_version: str,
        quizzes: Sequence[QuizData],
        quiz_summaries: Sequence[QuizData],
    ) -> None:
        self._package_name = normalize_package_name(package_name)
        self._definition_version = str(definition_version or "").strip()
        if not self._definition_version:
            raise ValueError("definition_version is required")

        self._quizzes = quizzes
        self._quiz_summaries = quiz_summaries
        self._quiz_by_id = self._index_by_id(quizzes, "quiz_id", "quiz")
        self._summary_by_id = self._index_by_id(quiz_summaries, "id", "quiz summary")
        if set(self._quiz_by_id) != set(self._summary_by_id):
            raise ValueError(f"quiz and summary IDs do not match for {self._package_name}")

    @staticmethod
    def _index_by_id(items: Sequence[QuizData], id_field: str, item_name: str) -> dict[int, QuizData]:
        indexed: dict[int, QuizData] = {}
        for item in items:
            item_id = item.get(id_field)
            if not isinstance(item_id, int) or item_id <= 0:
                raise ValueError(f"{item_name} has an invalid {id_field}: {item_id!r}")
            if item_id in indexed:
                raise ValueError(f"duplicate {item_name} {id_field}: {item_id}")
            indexed[item_id] = item
        return indexed

    @property
    def package_name(self) -> str:
        return self._package_name

    @property
    def definition_version(self) -> str:
        return self._definition_version

    def list_quizzes(self) -> Sequence[QuizData]:
        return self._quizzes

    def list_quiz_summaries(self) -> Sequence[QuizData]:
        return self._quiz_summaries

    def get_quiz(self, quiz_id: int) -> QuizData | None:
        return self._quiz_by_id.get(quiz_id)

    def get_quiz_name(self, quiz_id: int) -> str | None:
        summary = self._summary_by_id.get(quiz_id)
        return summary.get("quizName") if summary else None

    def get_last_question_id(self) -> int | None:
        question_ids = (
            question.get("question_id")
            for quiz in self._quizzes
            for section in quiz.get("sections", [])
            for question in section.get("questions", [])
        )
        valid_ids = [question_id for question_id in question_ids if isinstance(question_id, int)]
        return max(valid_ids, default=None)
