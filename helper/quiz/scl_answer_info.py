"""Compatibility import for the versioned SCL scoring definitions."""

from quiz_packages.scl.legacy_v1.scoring import (
    bookmark_scl_object,
    quiz_labels,
    quiz_questions_answer_schema,
)

__all__ = ["bookmark_scl_object", "quiz_labels", "quiz_questions_answer_schema"]
