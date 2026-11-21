"""Static providers backed by compiled PSY workbook data."""

from functools import partial
from importlib import import_module

from helper.quiz_engine import StaticQuizPackageProvider, StaticQuizRuntimeProvider
from quiz_packages.psy.generated_manifest import LATEST_MODULE, PACKAGE_NAMES


def load_packages(module_name: str = LATEST_MODULE):
    return import_module(module_name)


def create_provider(package_name: str):
    generated = load_packages()
    package = generated.PACKAGES[package_name]
    return StaticQuizPackageProvider(
        package_name=package_name,
        definition_version=generated.DEFINITION_VERSION,
        scoring_version=generated.SCORING_VERSION,
        quizzes=package["quizzes"],
        quiz_summaries=package["quiz_summaries"],
    )


def create_provider_factories():
    return tuple(partial(create_provider, package_name) for package_name in PACKAGE_NAMES)


def _score_user(package_name: str, user_id: int):
    from helper.quiz import answer_store
    from quiz_packages.psy.scoring import score_answers

    answers = answer_store.get_answers_for_user_kind(user_id, package_name)
    return score_answers(package_name, answers)


def create_runtime_provider(package_name: str):
    generated = load_packages()
    package = generated.PACKAGES[package_name]
    return StaticQuizRuntimeProvider(
        package_name=package_name,
        scoring_version=generated.SCORING_VERSION,
        definition_versions=(generated.DEFINITION_VERSION,),
        required_quiz_count=len(package["quizzes"]),
        scorer=partial(_score_user, package_name),
        report_handler="_handle_psy_labels",
    )


def create_runtime_provider_factories():
    return tuple(
        partial(create_runtime_provider, package_name)
        for package_name in PACKAGE_NAMES
    )
