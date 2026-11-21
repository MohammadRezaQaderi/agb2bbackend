"""Published SCL legacy-v1 content."""

from helper.quiz_engine import StaticQuizPackageProvider
from quiz_packages.scl.legacy_v1.catalog import quiz_summaries
from quiz_packages.scl.legacy_v1.questions import scl_quiz_info

PACKAGE_NAME = "SCL"
DEFINITION_VERSION = "legacy-v1"
SCORING_VERSION = "legacy-v1"


def create_provider():
    return StaticQuizPackageProvider(
        package_name=PACKAGE_NAME,
        definition_version=DEFINITION_VERSION,
        scoring_version=SCORING_VERSION,
        quizzes=scl_quiz_info,
        quiz_summaries=quiz_summaries,
    )
