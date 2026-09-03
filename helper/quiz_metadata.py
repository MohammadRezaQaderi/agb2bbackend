from helper.constants import AG_QUIZ_NAME_TITLE, SCL_QUIZ_NAME_TITLE


def get_quiz_name(kind, quiz_id) -> str | None:
    if quiz_id == 0:
        return None
    if kind == "AG":
        return AG_QUIZ_NAME_TITLE[quiz_id - 1]
    if kind == "SCL":
        return SCL_QUIZ_NAME_TITLE[quiz_id - 1]
    return None
