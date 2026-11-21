"""Compatibility import for the versioned SCL report rules."""

from quiz_packages.scl.legacy_v1.reports import *  # noqa: F403
from quiz_packages.scl.legacy_v1.reports import _REPORT_DATA

__all__ = ["_REPORT_DATA", "get_interfast_value", "get_report_text", "get_statefast_value"]
