"""Provider for versioned quiz definitions stored in Python modules."""

from copy import deepcopy
from collections.abc import Sequence
from typing import Any

from helper.quiz_engine.registry import normalize_package_name


QuizData = dict[str, Any]
PRIVATE_QUESTION_FIELDS = frozenset({"question_answer"})


class StaticQuizPackageProvider:
    def __init__(
        self,
        *,
        package_name: str,
        definition_version: str,
        scoring_version: str | None = None,
        quizzes: Sequence[QuizData],
        quiz_summaries: Sequence[QuizData],
    ) -> None:
        self._package_name = normalize_package_name(package_name)
        self._definition_version = str(definition_version or "").strip()
        if not self._definition_version:
            raise ValueError("definition_version is required")
        self._scoring_version = str(scoring_version or self._definition_version).strip()
        if not self._scoring_version:
            raise ValueError("scoring_version is required")

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

    @property
    def scoring_version(self) -> str:
        return self._scoring_version

    def list_quizzes(self) -> Sequence[QuizData]:
        return self._quizzes

    def list_quiz_summaries(self) -> Sequence[QuizData]:
        return self._quiz_summaries

    def get_quiz(self, quiz_id: int) -> QuizData | None:
        return self._quiz_by_id.get(quiz_id)

    def get_public_quiz(self, quiz_id: int) -> QuizData | None:
        private_quiz = self.get_quiz(quiz_id)
        if private_quiz is None:
            return None

        public_quiz = deepcopy(private_quiz)
        for section in public_quiz.get("sections", []):
            for question in section.get("questions", []):
                example_answer = question.get("question_answer")
                if isinstance(example_answer, list) and example_answer:
                    question["is_example"] = True
                    question["example_answer"] = list(example_answer)
                for field in PRIVATE_QUESTION_FIELDS:
                    question.pop(field, None)
        return public_quiz

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
