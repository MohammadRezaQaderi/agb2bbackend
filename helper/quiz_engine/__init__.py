"""Package-independent quiz content access."""

from helper.quiz_engine.contracts import QuizPackageProvider
from helper.quiz_engine.registry import QuizPackageRegistry, quiz_package_registry
from helper.quiz_engine.static_provider import StaticQuizPackageProvider

__all__ = [
    "QuizPackageProvider",
    "QuizPackageRegistry",
    "StaticQuizPackageProvider",
    "quiz_package_registry",
]
