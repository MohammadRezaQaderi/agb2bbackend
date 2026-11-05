"""Published AG legacy-v1 content."""

from helper.quiz_engine import StaticQuizPackageProvider
from quiz_packages.ag.legacy_v1.catalog import quiz_summaries
from quiz_packages.ag.legacy_v1.questions import ag_quiz_info

PACKAGE_NAME = "AG"
DEFINITION_VERSION = "legacy-v1"


def create_provider():
    return StaticQuizPackageProvider(
        package_name=PACKAGE_NAME,
        definition_version=DEFINITION_VERSION,
        quizzes=ag_quiz_info,
        quiz_summaries=quiz_summaries,
    )
