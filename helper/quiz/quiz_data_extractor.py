from helper.quiz_engine import quiz_package_registry
from quiz_packages.ag.legacy_v1.catalog import quiz_summaries as ag_quiz_table_info
from quiz_packages.builtin import BUILTIN_PACKAGE_FACTORIES
from quiz_packages.scl.legacy_v1.catalog import quiz_summaries as scl_quiz_table_info


def get_ag_quiz_table_info():
    return ag_quiz_table_info


def get_scl_quiz_table_info():
    return scl_quiz_table_info


# Backward compatibility - keep old variable and function names pointing to AG pack
# quiz_info = ag_quiz_info
quiz_table_info = ag_quiz_table_info


def _register_static_packages():
    for create_provider in BUILTIN_PACKAGE_FACTORIES:
        provider = create_provider()
        if quiz_package_registry.get_optional(provider.package_name) is None:
            quiz_package_registry.register(provider)


_register_static_packages()


def get_quiz_info(quiz_id, kind="AG"):
    """
    Return API-safe quiz data for the given quiz_id and kind.
    Data is loaded from:
      - AG:  quiz_packages.ag.legacy_v1.questions.ag_quiz_info
      - SCL: quiz_packages.scl.legacy_v1.questions.scl_quiz_info
    """
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_public_quiz(quiz_id) if provider else None


def get_private_quiz_info(quiz_id, kind="AG"):
    """Return the complete static definition for trusted backend processing."""
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_quiz(quiz_id) if provider else None


def get_quiz_table_info(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    if provider:
        return provider.list_quiz_summaries()
    # Preserve the legacy fallback until all callers validate package names.
    return quiz_package_registry.get("AG").list_quiz_summaries()


def get_quiz_name(quiz_id, kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_quiz_name(quiz_id) if provider else None


def get_last_question_id(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_last_question_id() if provider else None


def get_definition_version(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.definition_version if provider else None


def get_scoring_version(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.scoring_version if provider else None
