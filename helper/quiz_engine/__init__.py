"""Package-independent quiz content access."""

from helper.quiz_engine.contracts import QuizPackageProvider, QuizRuntimeProvider
from helper.quiz_engine.registry import (
    QuizPackageRegistry,
    QuizRuntimeRegistry,
    quiz_package_registry,
    quiz_runtime_registry,
)
from helper.quiz_engine.runtime_provider import StaticQuizRuntimeProvider
from helper.quiz_engine.static_provider import StaticQuizPackageProvider

__all__ = [
    "QuizPackageProvider",
    "QuizPackageRegistry",
    "QuizRuntimeProvider",
    "QuizRuntimeRegistry",
    "StaticQuizPackageProvider",
    "StaticQuizRuntimeProvider",
    "quiz_package_registry",
    "quiz_runtime_registry",
]
