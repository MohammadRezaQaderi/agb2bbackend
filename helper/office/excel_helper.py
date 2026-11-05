"""AG brain calculation backed by the generated Brain workbook module."""

import time
from collections.abc import Callable
from typing import Any

from helper.quiz.check_score import ag_score_computation


def compute_brain_info(
    user_id,
    phone=None,
    master_file=None,
    master_sheet=None,
    scorer: Callable[[int], Any] | None = None,
    calculator: Callable[[dict[str, Any]], dict[str, list[dict]]] | None = None,
):
    """Score a student and calculate report data without opening Excel."""
    del phone, master_file, master_sheet
    started_at = time.perf_counter()
    if scorer is None:
        data, correct, wrong, unanswered = ag_score_computation(user_id, user_age=14)
    else:
        data, correct, wrong, unanswered = scorer(int(user_id))

    if calculator is None:
        from quiz_packages.ag.legacy_v1.generated_brain import calculate

        calculator = calculate
    output = calculator(data)
    print(f"time to execute the brain: {time.perf_counter() - started_at:.2f}s")
    return (
        data,
        output["fields"],
        output["categories"],
        output["branches"],
        correct,
        wrong,
        unanswered,
    )
