from __future__ import annotations

from typing import Any


def _build_capacity_info(capacity_packages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        package["package_name"]: {
            "allowed": package.get("allowed"),
            "used": package.get("used"),
        }
        for package in capacity_packages
        if package.get("package_name")
    }


def _build_package_counts(package_counts: dict[str, int], packages_data: dict[str, Any]) -> dict[str, int]:
    counts = {package_name: 0 for package_name in packages_data.keys()}
    counts.update({package_name: int(count or 0) for package_name, count in package_counts.items()})
    return counts


def _build_quiz_report(
    quiz_attempts: list[dict[str, Any]],
    packages_data: dict[str, Any],
    package_quiz_count: dict[str, int] | None = None,
) -> dict[str, dict[str, int]]:
    package_quiz_count = package_quiz_count or {"AG": 7, "SCL": 4}
    quiz_report = {}

    for package_name in packages_data.keys():
        attempts = [attempt for attempt in quiz_attempts if attempt.get("quiz_kind") == package_name]
        total_quizzes = package_quiz_count.get(package_name, 0)
        completed_attempts = [attempt for attempt in attempts if attempt.get("state") == 2]

        quiz_report[package_name] = {
            "finish_quiz": len(
                {
                    attempt.get("user_id")
                    for attempt in completed_attempts
                    if attempt.get("quiz_id") == total_quizzes
                }
            ),
            "started_quiz": len({attempt.get("user_id") for attempt in attempts}),
            "c_quiz": len(completed_attempts),
            "nc_quiz": len(attempts) - len(completed_attempts),
        }

    return quiz_report


def build_dashboard_info_response(
    capacity_packages: list[dict[str, Any]],
    student_count: int,
    package_counts: dict[str, int],
    quiz_attempts: list[dict[str, Any]],
    packages_data: dict[str, Any],
    consultant_count: int | None = None,
) -> dict[str, Any]:
    dashboard_info = {
        "capacity": _build_capacity_info(capacity_packages),
        "stu_count": student_count,
        "stu": _build_package_counts(package_counts, packages_data),
        "quiz_report": _build_quiz_report(quiz_attempts, packages_data),
    }

    if consultant_count is not None:
        dashboard_info["con_count"] = consultant_count

    return dashboard_info
