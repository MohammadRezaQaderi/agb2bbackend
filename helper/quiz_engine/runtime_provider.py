"""Runtime provider for versioned scoring and report generation."""

from dataclasses import dataclass
from typing import Any, Callable

from helper.quiz_engine.registry import normalize_package_name, normalize_version


@dataclass(frozen=True)
class StaticQuizRuntimeProvider:
    package_name: str
    scoring_version: str
    definition_versions: tuple[str, ...]
    required_quiz_count: int
    scorer: Callable[[int], Any]
    report_handler: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_name", normalize_package_name(self.package_name))
        object.__setattr__(self, "scoring_version", normalize_version(self.scoring_version))
        object.__setattr__(
            self,
            "definition_versions",
            tuple(normalize_version(version) for version in self.definition_versions),
        )
        if not self.definition_versions:
            raise ValueError("definition_versions is required")
        if self.required_quiz_count <= 0:
            raise ValueError("required_quiz_count must be positive")
        if not callable(self.scorer):
            raise TypeError("scorer must be callable")
        if not str(self.report_handler or "").strip():
            raise ValueError("report_handler is required")

    def score_user(self, user_id: int) -> Any:
        return self.scorer(int(user_id))

    def generate_report(self, report_service: Any, user_id: str) -> None:
        try:
            handler = getattr(report_service, self.report_handler)
        except AttributeError as exc:
            raise RuntimeError(
                f"report handler is not available: {self.report_handler}"
            ) from exc
        handler(str(user_id), self)
