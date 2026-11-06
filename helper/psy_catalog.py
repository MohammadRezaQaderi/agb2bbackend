from __future__ import annotations

from typing import Any

from helper.constants import (
    PSY_PACKAGE_DESCRIPTIONS,
    PSY_PACKAGE_NAMES,
    PSY_PACKAGE_TITLES,
)
from helper.quiz.quiz_data_extractor import (
    get_definition_version,
    get_quiz_table_info,
    get_scoring_version,
)


def build_psy_catalog(dashboard_info: dict[str, Any] | None) -> dict[str, Any]:
    dashboard_info = dashboard_info or {}
    capacities = dashboard_info.get("capacity") or {}
    access_counts = dashboard_info.get("stu") or {}
    quiz_reports = dashboard_info.get("quiz_report") or {}
    packages = []

    for package_name in PSY_PACKAGE_NAMES:
        quizzes = get_quiz_table_info(package_name)
        capacity = capacities.get(package_name) or {}
        report = quiz_reports.get(package_name) or {}
        allowed = int(capacity.get("allowed") or 0)
        used = int(capacity.get("used") or 0)

        packages.append(
            {
                "package_name": package_name,
                "title": PSY_PACKAGE_TITLES.get(package_name, package_name),
                "description": PSY_PACKAGE_DESCRIPTIONS.get(package_name, ""),
                "definition_version": get_definition_version(package_name),
                "scoring_version": get_scoring_version(package_name),
                "quiz_count": len(quizzes),
                "quizzes": [
                    {
                        "quiz_id": quiz.get("id"),
                        "name": quiz.get("quizName") or "",
                    }
                    for quiz in quizzes
                ],
                "capacity": {
                    "allowed": allowed,
                    "used": used,
                    "total": allowed + used,
                },
                "access_count": int(access_counts.get(package_name) or 0),
                "report_summary": {
                    "started_students": int(report.get("started_quiz") or 0),
                    "completed_students": int(report.get("finish_quiz") or 0),
                    "completed_quizzes": int(report.get("completed_attempts") or 0),
                    "in_progress_quizzes": int(report.get("in_progress_attempts") or 0),
                    "download_available": False,
                },
            }
        )

    return {"packages": packages}
