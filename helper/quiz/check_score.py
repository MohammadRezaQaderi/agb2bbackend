import time
from typing import Any, Dict, List, Tuple

import helper.db.db_helper as db_helper
from helper.quiz import answer_store
from helper.quiz.ag_answer_info import quiz_labels, quiz_questions_answer_schema
from helper.quiz.scl_answer_info import (
    quiz_labels as scl_quiz_labels,
    quiz_questions_answer_schema as scl_quiz_questions_answer_schema,
)

iq_scores_ages = {
    13: {3: [50, -1], 4: [56, -1], 5: [56, -1], 6: [62, -1], 7: [65, -1], 8: [65, -1], 9: [68, -1], 10: [68, -1],
         11: [71, -1], 12: [73, -1], 13: [76, -1], 14: [80, -1], 15: [80, -1], 16: [88, 0], 17: [94, 0], 18: [100, 1],
         19: [105, 1], 20: [110, 2], 21: [115, 2], 22: [120, 3], 23: [124, 3], 24: [128, 3], 25: [132, 4], 26: [136, 4],
         27: [140, 4], 28: [144, 4], 29: [148, 4], 30: [152, 4], 31: [152, 4], 32: [156, 4], 33: [160, 4], 34: [170, 4],
         35: [170, 4], 36: [180, 4], 37: [200, 4], 38: [200, 4], 39: [200, 4], 40: [200, 4], 41: [200, 4], 42: [200, 4],
         43: [200, 4]},
    14: {3: [50, -1], 4: [50, -1], 5: [50, -1], 6: [56, -1], 7: [61, -1], 8: [61, -1], 9: [65, -1], 10: [65, -1],
         11: [68, -1], 12: [71, -1], 13: [73, -1], 14: [76, -1], 15: [76, -1], 16: [80, -1], 17: [86, 0], 18: [91, 0],
         19: [96, 0], 20: [100, 1], 21: [104, 1], 22: [109, 1], 23: [114, 2], 24: [119, 2], 25: [124, 3], 26: [128, 3],
         27: [133, 4], 28: [138, 4], 29: [143, 4], 30: [148, 4], 31: [148, 4], 32: [153, 4], 33: [157, 4], 34: [161, 4],
         35: [161, 4], 36: [170, 4], 37: [180, 4], 38: [180, 4], 39: [200, 4], 40: [200, 4], 41: [200, 4], 42: [200, 4],
         43: [200, 4]},
    15: {3: [50, -1], 4: [50, -1], 5: [50, -1], 6: [50, -1], 7: [56, -1], 8: [56, -1], 9: [61, -1], 10: [61, -1],
         11: [63, -1], 12: [68, -1], 13: [71, -1], 14: [73, -1], 15: [73, -1], 16: [76, -1], 17: [80, -1], 18: [84, -1],
         19: [88, 0], 20: [92, 0], 21: [96, 0], 22: [100, 1], 23: [104, 1], 24: [109, 1], 25: [114, 2], 26: [119, 2],
         27: [124, 3], 28: [128, 3], 29: [133, 4], 30: [138, 4], 31: [138, 4], 32: [143, 4], 33: [147, 4], 34: [155, 4],
         35: [155, 4], 36: [162, 4], 37: [170, 4], 38: [170, 4], 39: [180, 4], 40: [180, 4], 41: [180, 4], 42: [200, 4],
         43: [20, 4]},
    16: {3: [50, -1], 4: [50, -1], 5: [50, -1], 6: [50, -1], 7: [50, -1], 8: [50, -1], 9: [56, -1], 10: [56, -1],
         11: [61, -1], 12: [65, -1], 13: [68, -1], 14: [71, -1], 15: [71, -1], 16: [73, -1], 17: [76, -1], 18: [80, -1],
         19: [84, -1], 20: [88, 0], 21: [92, 0], 22: [96, 0], 23: [100, 1], 24: [104, 1], 25: [109, 1], 26: [114, 2],
         27: [119, 2], 28: [124, 3], 29: [128, 3], 30: [133, 4], 31: [133, 4], 32: [138, 4], 33: [143, 4], 34: [148, 4],
         35: [148, 4], 36: [155, 4], 37: [162, 4], 38: [162, 4], 39: [170, 4], 40: [170, 4], 41: [170, 4], 42: [180, 4],
         43: [200, 4]}}


def compute_answer_stats(
        user_catel: Dict[str, List[int]],
        quiz_answer: List[Dict[str, Any]],
) -> Tuple[int, int, int]:
    """
    Compute CATEL-related answer statistics.

    Returns:
        (correct_answers, wrong_answers, unanswered)
    """
    correct_answers = 0
    wrong_answers = 0
    unanswered = 0

    for key, user_value in user_catel.items():
        if not user_value:
            unanswered += 1
            continue

        first_field_values = quiz_answer[int(key) - 1]['first_field_values']
        keys_with_value_one = [
            option_key
            for option_key, option_value in first_field_values.items()
            if option_value == 1
        ]

        if user_value == keys_with_value_one:
            correct_answers += 1
        else:
            wrong_answers += 1

    return correct_answers, wrong_answers, unanswered


def ca_format_compute(
        label: str,
        labels: Dict[str, int],
        value: Dict[Any, int],
        user_answers: List[Any],
) -> Dict[str, int]:
    """Update labels for 'ca' style questions."""
    keys_with_value_one = [k for k, v in value.items() if v == 1]
    if keys_with_value_one == user_answers:
        labels[label] = labels[label] + 1
    return labels


def ws_format_compute(
        labels: Dict[str, int],
        first_field_values: Dict[Any, int],
        first_label: str,
        second_field_values: Dict[Any, int],
        second_label: str,
        user_answers: List[Any],
) -> Dict[str, int]:
    """
    Update labels for 'ws' style questions (weighted single choice).
    """
    selected_key = user_answers[0]
    labels[first_label] = labels[first_label] + first_field_values[selected_key]

    if second_label != '':
        labels[second_label] = labels[second_label] + second_field_values[selected_key]

    return labels


def ocd_format_compute(labels, first_field_values, user_answers):
    """
    Increment OCD buckets based on the selected option.

    The SCL OCD questions store an array of tags (e.g., ['ocd', 'ocd1'])
    for each answer option. We count each tag occurrence.
    """
    selected_option = user_answers[0]
    tags = first_field_values.get(selected_option, [])
    if not isinstance(labels.get('OCD'), dict):
        labels['OCD'] = {'ocd': 0, 'ocd1': 0, 'ocd2': 0, 'ocd3': 0, 'ocd4': 0}

    for tag in tags:
        labels['OCD'][tag] = labels['OCD'].get(tag, 0) + 1

    return labels


def sw_format_compute(
        label: str,
        labels: Dict[str, int],
        user_answers: List[Any],
) -> Dict[str, int]:
    """Update labels for 'sw' style questions (multi-select, weight = 1 per selection)."""
    labels[label] = labels[label] + len(user_answers)
    return labels


def sw1_format_compute(
        label: str,
        labels: Dict[str, int],
        value: Dict[Any, int],
        user_answers: List[Any],
) -> Dict[str, int]:
    """Update labels for 'sw1' style questions (single-choice with custom weight)."""
    labels[label] = labels[label] + value[user_answers[0]]
    return labels


def get_iq_score(catel_score: int, age: int):
    if catel_score < 3:
        return [50, -1]
        # raise "error from catel score"
    if catel_score > 43:
        return [200, 4]
    if age < 13:
        age = 13
        # raise "error of the age info"
    if age > 16:
        age = 16
    return iq_scores_ages[age][catel_score]


def _insert_missing_answer(conn, cursor, user_id, question_id) -> None:
    """
    Insert a row into quiz_missing_answers for a missing answer.
    """
    field = '([user_id], [question_id])'
    values = (user_id, question_id)
    db_helper.insert_value(
        conn=conn,
        cursor=cursor,
        table_name="quiz_missing_answers",
        fields=field,
        values=values,
    )


def ag_score_computation(conn, cursor, user_id, user_age=9):
    start = time.time()
    query = 'SELECT birth_date FROM stu WHERE user_id = ?'
    res_stu = db_helper.search_table(
        conn=conn,
        cursor=cursor,
        query=query,
        field=user_id,
    )
    if res_stu:
        user_age = 1400 - int(res_stu[0]) - 1
    completed_count = answer_store.get_completed_count(conn, cursor, user_id, "AG")
    if completed_count < 7:
        raise ValueError("Insufficient AG quiz data")
    user_answers = answer_store.get_answers_for_user_kind(conn, cursor, user_id, "AG")
    labels = quiz_labels.copy()
    catel_answer = {str(i): user_answers.get(str(i), []) for i in range(1, 62)}
    for _, question in enumerate(quiz_questions_answer_schema):
        if not question['have_answer']:
            qid = str(question['question_id'])

            if qid not in user_answers:
                _insert_missing_answer(conn, cursor, user_id, question['question_id'])
                continue

            question_answers = user_answers[qid]

            if question['kind'] == 'ca':
                labels = ca_format_compute(
                    "CATEL",
                    labels,
                    question['first_field_values'],
                    question_answers,
                )
            elif question['kind'] == 'ws':
                labels = ws_format_compute(
                    labels=labels,
                    first_field_values=question['first_field_values'],
                    first_label=question['first_scale'],
                    second_field_values=question['second_field_values'],
                    second_label=question['second_scale'],
                    user_answers=question_answers,
                )
            elif question['kind'] == 'sw':
                labels = sw_format_compute(
                    label=question['first_scale'],
                    labels=labels,
                    user_answers=question_answers,
                )
            elif question['kind'] == 'sw1':
                labels = sw1_format_compute(
                    label=question['first_scale'],
                    labels=labels,
                    value=question['first_field_values'],
                    user_answers=question_answers,
                )
    c, w, n = compute_answer_stats(user_catel=catel_answer, quiz_answer=quiz_questions_answer_schema)
    iq_info = get_iq_score(labels["CATEL"], age=user_age)
    if isinstance(iq_info[0], int):
        labels['IQ_Number'] = int(iq_info[0])
    else:
        labels['IQ_Number'] = ''
    if isinstance(iq_info[1], int):
        labels['CATEL_Brain'] = int(iq_info[1])
    else:
        labels['CATEL_Brain'] = ''
    end = time.time()
    print("time to compute the score of the user : ", end - start)
    return labels, c, w, n


def score_computation_scl(user_answers):
    """
    Compute SCL scores based on provided answers.

    Args:
        user_answers: dict[str, list[int]] mapping question_id to selected options.

    Returns:
        Tuple of (labels, missing_questions)
    """
    start = time.time()
    labels = scl_quiz_labels.copy()
    labels['OCD'] = {'ocd': 0, 'ocd1': 0, 'ocd2': 0, 'ocd3': 0, 'ocd4': 0}
    missing_questions = []

    for question in scl_quiz_questions_answer_schema:
        if question['have_answer']:
            continue

        qid = str(question['question_id'])
        if qid not in user_answers:
            missing_questions.append(question['question_id'])
            continue

        answers = user_answers[qid]
        if question['kind'] == 'ws':
            labels = ws_format_compute(
                labels=labels,
                first_field_values=question['first_field_values'],
                first_label=question['first_scale'],
                second_field_values=question['second_field_values'],
                second_label=question['second_scale'],
                user_answers=answers
            )
        elif question['kind'] == 'ocd':
            labels = ocd_format_compute(
                labels=labels,
                first_field_values=question['first_field_values'],
                user_answers=answers
            )

    end = time.time()
    print("time to compute the SCL score of the user : ", end - start)
    return labels, missing_questions
