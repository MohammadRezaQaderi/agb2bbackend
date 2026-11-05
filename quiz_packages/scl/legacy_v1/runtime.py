"""SCL legacy-v1 scoring and report runtime."""

from helper.quiz_engine.runtime_provider import StaticQuizRuntimeProvider
from quiz_packages.scl.legacy_v1 import DEFINITION_VERSION, PACKAGE_NAME, SCORING_VERSION


def score_user(user_id: int):
    from helper.quiz import answer_store
    from helper.quiz.check_score import score_computation_scl

    user_answers = answer_store.get_answers_for_user_kind(user_id, PACKAGE_NAME)
    return score_computation_scl(user_answers)


def create_runtime_provider():
    return StaticQuizRuntimeProvider(
        package_name=PACKAGE_NAME,
        scoring_version=SCORING_VERSION,
        definition_versions=(DEFINITION_VERSION,),
        required_quiz_count=4,
        scorer=score_user,
        report_handler="_handle_scl_report",
    )
