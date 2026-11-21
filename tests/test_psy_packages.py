from helper.quiz.quiz_data_extractor import get_private_quiz_info, get_quiz_info, get_quiz_table_info
from helper.quiz_engine import quiz_package_registry
from quiz_packages.psy.generated_manifest import LATEST_VERSION, PACKAGE_NAMES
from quiz_packages.psy.provider import load_packages
from quiz_packages.psy.scoring import score_answers

EXPECTED_PACKAGES = (
    "PSY_ANX",
    "PSY_DEP",
    "PSY_INTERNET",
    "PSY_MBTI",
    "PSY_MOTIVATION",
    "PSY_NEEDS",
    "PSY_SOCIAL",
    "PSY_NEO",
    "PSY_COPING_STRATEGIES",
    "PSY_OCD",
    "PSY_EQ_IQ",
    "PSY_GARDNER",
    "PSY_SCL90",
    "PSY_STUDY_SKILLS",
)


def _questions(package):
    return [
        question for quiz in package["quizzes"] for section in quiz["sections"] for question in section["questions"]
    ]


def test_generated_psy_packages_are_complete_and_registered():
    generated = load_packages()

    assert LATEST_VERSION == "v1"
    assert PACKAGE_NAMES == EXPECTED_PACKAGES
    assert tuple(generated.PACKAGES) == EXPECTED_PACKAGES
    assert sum(len(package["quizzes"]) for package in generated.PACKAGES.values()) == 40
    assert sum(len(_questions(package)) for package in generated.PACKAGES.values()) == 1469

    registered = quiz_package_registry.package_names()
    for package_name in EXPECTED_PACKAGES:
        assert package_name in registered


def test_each_psy_package_has_stable_sequential_question_ids():
    generated = load_packages()

    for package in generated.PACKAGES.values():
        question_ids = [question["question_id"] for question in _questions(package)]
        assert question_ids == list(range(1, len(question_ids) + 1))
        assert len(package["scoring_questions"]) == len(question_ids)


def test_psy_provider_exposes_safe_public_quiz_data():
    assert len(get_quiz_table_info("psy_anx")) == 5
    private_quiz = get_private_quiz_info(1, "psy_anx")
    public_quiz = get_quiz_info(1, "psy_anx")

    assert private_quiz["quiz_id"] == 1
    assert public_quiz["quiz_id"] == 1
    assert "question_answer" in private_quiz["sections"][0]["questions"][0]
    assert "question_answer" not in public_quiz["sections"][0]["questions"][0]


def test_shared_scorer_uses_workbook_answer_weights():
    scores, missing = score_answers("psy_anx", {"1": [1], "2": [5]})

    assert scores["pen.worry"] == 10
    assert 1 not in missing
    assert 2 not in missing
    assert 3 in missing


def test_shared_scorer_supports_mbti_dual_scale_mapping():
    first_option, _ = score_answers("psy_mbti", {1: [1]})
    second_option, _ = score_answers("psy_mbti", {1: [2]})

    assert first_option["E"] == 1
    assert first_option["I"] == 0
    assert second_option["I"] == 2
    assert second_option["E"] == 0


def test_shared_scorer_treats_blank_raven_cells_as_zero():
    correct, _ = score_answers("psy_eq_iq", {91: [4]})
    incorrect, _ = score_answers("psy_eq_iq", {91: [1]})

    assert correct["raven.eqiq"] == 1
    assert incorrect["raven.eqiq"] == 0


def test_raven_media_names_match_flat_frontend_contract():
    raven = get_private_quiz_info(2, "psy_eq_iq")
    first_question = raven["sections"][0]["questions"][0]

    assert first_question["first_question"] == "psy_eq_iq_q_q1"
    assert first_question["answers"][0]["answer_text"] == "psy_eq_iq_a_image1"
