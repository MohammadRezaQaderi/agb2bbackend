"""Package-independent access to versioned scoring and report runtimes."""

from helper.quiz_engine.registry import quiz_runtime_registry
from quiz_packages.builtin import BUILTIN_RUNTIME_FACTORIES


def _register_builtin_runtimes() -> None:
    for create_provider in BUILTIN_RUNTIME_FACTORIES:
        provider = create_provider()
        if quiz_runtime_registry.get_optional(
            provider.package_name,
            provider.scoring_version,
        ) is None:
            quiz_runtime_registry.register(provider)


_register_builtin_runtimes()


def get_runtime_provider(package_name: str, scoring_version: str):
    return quiz_runtime_registry.get(package_name, scoring_version)


def resolve_attempt_runtime(package_name: str, attempt_versions: list[dict]):
    if not attempt_versions:
        raise ValueError("Insufficient quiz data for report generation")
    if len(attempt_versions) != 1:
        versions = [
            f"{row['definition_version']}/{row['scoring_version']}"
            for row in attempt_versions
        ]
        raise ValueError(f"Mixed quiz versions cannot be scored together: {versions}")

    attempt_version = attempt_versions[0]
    runtime_provider = get_runtime_provider(
        package_name,
        attempt_version["scoring_version"],
    )
    if attempt_version["definition_version"] not in runtime_provider.definition_versions:
        raise ValueError(
            "Quiz definition version is not supported by the scoring runtime: "
            f"{package_name}@{attempt_version['definition_version']}"
        )
    if attempt_version["attempt_count"] < runtime_provider.required_quiz_count:
        raise ValueError("Insufficient quiz data for report generation")
    return runtime_provider
