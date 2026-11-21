import math

import pytest

from helper.office.brain_formula_runtime import INPUT_CELLS
from quiz_packages.ag.legacy_v1.generated_brain import WORKBOOK_SHA256, calculate

WORKBOOK_INPUT = {
    "IQ_Number": 138,
    "SES": 109,
    "Visual_spatial": 30,
    "Linguistic_verbal": 31,
    "Logical_mathematical": 38,
    "Body_kinesthetic": 32,
    "Intrapersonal": 33,
    "Interpersonal": 31,
    "Naturalistic": 29,
    "Musical": 25,
    "Imigration": 6,
    "Money": 10,
    "Social_place": 3,
    "Job": 7,
    "Field": 5,
    "Speed": 5,
    "Analytical": 31,
    "Futuristic": 23,
    "Ideation": 13,
    "Input": 9,
    "Strategic": 11,
    "Connectedness": 20,
    "Empathy": 18,
    "Individualization": 19,
    "Activator": 14,
    "Command": 20,
    "Competition": 8,
    "Self_assurance": 29,
    "Arranger": 22,
    "Consistency": 10,
    "Focus": 18,
    "Adaptability": 12,
    "Harmony": 13,
    "Neuroticism": 31,
    "Extraversion": 29,
    "Conscientiousness": 17,
    "Openness": 31,
    "Agreeableness": 31,
    "Artistic": 15,
    "Enterprising": 11,
    "Conventional": 19,
    "Social": 26,
    "Investigative": 32,
    "Realistic": 16,
}


def test_generated_brain_matches_workbook_snapshot():
    result = calculate(WORKBOOK_INPUT)

    assert len(WORKBOOK_SHA256) == 64
    assert len(result["fields"]) == 201
    assert len(result["branches"]) == 7
    assert len(result["categories"]) == 18
    assert result["fields"][0]["Field"] == "علوم تربیتی"
    assert math.isclose(result["fields"][0]["Capabilities"], 3.4357705098255775)
    assert result["fields"][0]["IQStars"] == "*****"
    assert result["fields"][0]["Scatter"] == "#008000"
    assert result["branches"][0]["Branch"] == "علوم تجربی"
    assert math.isclose(result["branches"][0]["Value"], 53.74149659863946)
    assert result["categories"][-1]["Category"] == "تکنسین کامپیوتر"


def test_generated_brain_rejects_missing_score():
    inputs = dict(WORKBOOK_INPUT)
    inputs.pop("IQ_Number")

    with pytest.raises(ValueError, match="IQ_Number"):
        calculate(inputs)


def test_input_contract_matches_snapshot():
    assert set(INPUT_CELLS) == set(WORKBOOK_INPUT)
