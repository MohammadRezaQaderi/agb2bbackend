"""AG legacy-v1 scoring and report runtime."""

from helper.quiz_engine.runtime_provider import StaticQuizRuntimeProvider
from quiz_packages.ag.legacy_v1 import DEFINITION_VERSION, PACKAGE_NAME, SCORING_VERSION


def score_user(user_id: int):
    from helper.quiz.check_score import ag_score_computation

    return ag_score_computation(user_id, user_age=14)


def create_runtime_provider():
    return StaticQuizRuntimeProvider(
        package_name=PACKAGE_NAME,
        scoring_version=SCORING_VERSION,
        definition_versions=(DEFINITION_VERSION,),
        required_quiz_count=7,
        scorer=score_user,
        report_handler="_handle_ag_report",
    )
