"""Static providers backed by compiled PSY workbook data."""

from functools import partial
from importlib import import_module

from helper.quiz_engine import StaticQuizPackageProvider
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
