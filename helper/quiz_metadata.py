from helper.quiz.quiz_data_extractor import get_quiz_name as get_registered_quiz_name


def get_quiz_name(kind, quiz_id) -> str | None:
    if quiz_id == 0:
        return None
    return get_registered_quiz_name(quiz_id=quiz_id, kind=kind)
