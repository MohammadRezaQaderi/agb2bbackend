"""Contracts implemented by static content today and API content in the future."""

from typing import Any, Protocol, Sequence


QuizData = dict[str, Any]


class QuizPackageProvider(Protocol):
    """Read-only source for one version of a quiz package."""

    @property
    def package_name(self) -> str:
        """Return the canonical package identifier, such as ``AG``."""

    @property
    def definition_version(self) -> str:
        """Return the immutable content version exposed by this provider."""

    @property
    def scoring_version(self) -> str:
        """Return the immutable scoring version used by this provider."""

    def list_quizzes(self) -> Sequence[QuizData]:
        """Return complete private quiz definitions for backend processing."""

    def list_quiz_summaries(self) -> Sequence[QuizData]:
        """Return quiz list metadata used by the product UI."""

    def get_quiz(self, quiz_id: int) -> QuizData | None:
        """Return one complete private quiz definition."""

    def get_public_quiz(self, quiz_id: int) -> QuizData | None:
        """Return an isolated quiz definition safe for an API response."""

    def get_quiz_name(self, quiz_id: int) -> str | None:
        """Return the display name of one quiz."""

    def get_last_question_id(self) -> int | None:
        """Return the final global question ID used to complete the package."""
