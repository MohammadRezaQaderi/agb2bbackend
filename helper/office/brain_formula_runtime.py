"""Runtime for Python modules generated from the Brain workbook."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


BrainValue = str | int | float | bool | None
FormulaNode = tuple[Any, ...] | BrainValue


INPUT_CELLS = {
    "IQ_Number": "K2",
    "SES": "M2",
    "Visual_spatial": "O2",
    "Linguistic_verbal": "Q2",
    "Logical_mathematical": "S2",
    "Body_kinesthetic": "U2",
    "Intrapersonal": "W2",
    "Interpersonal": "Y2",
    "Naturalistic": "AA2",
    "Musical": "AB2",
    "Imigration": "AD2",
    "Money": "AE2",
    "Social_place": "AF2",
    "Job": "AG2",
    "Field": "AH2",
    "Speed": "AI2",
    "Analytical": "AJ2",
    "Futuristic": "AK2",
    "Ideation": "AM2",
    "Input": "AN2",
    "Strategic": "AO2",
    "Connectedness": "AQ2",
    "Empathy": "AS2",
    "Individualization": "AU2",
    "Activator": "AV2",
    "Command": "AX2",
    "Competition": "AY2",
    "Self_assurance": "AZ2",
    "Arranger": "BB2",
    "Consistency": "BC2",
    "Focus": "BE2",
    "Adaptability": "BF2",
    "Harmony": "BH2",
    "Neuroticism": "BJ2",
    "Extraversion": "BL2",
    "Conscientiousness": "BM2",
    "Openness": "BN2",
    "Agreeableness": "BO2",
    "Artistic": "BQ2",
    "Enterprising": "BS2",
    "Conventional": "BU2",
    "Social": "BW2",
    "Investigative": "BY2",
    "Realistic": "CA2",
}


def _number(value: BrainValue) -> float | int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    raise TypeError(f"Expected a numeric Excel value, got {value!r}")


def _numeric_values(values: Sequence[BrainValue]) -> list[float | int]:
    return [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]


def _flatten(values: Sequence[Any]) -> list[BrainValue]:
    flattened: list[BrainValue] = []
    for value in values:
        if isinstance(value, list):
            flattened.extend(value)
        else:
            flattened.append(value)
    return flattened


def _excel_correl(first: Sequence[BrainValue], second: Sequence[BrainValue]) -> float:
    pairs = [
        (float(left), float(right))
        for left, right in zip(first, second)
        if isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ]
    if len(pairs) < 2:
        raise ValueError("CORREL requires at least two numeric pairs")

    left_mean = sum(left for left, _ in pairs) / len(pairs)
    right_mean = sum(right for _, right in pairs) / len(pairs)
    numerator = sum((left - left_mean) * (right - right_mean) for left, right in pairs)
    left_variance = sum((left - left_mean) ** 2 for left, _ in pairs)
    right_variance = sum((right - right_mean) ** 2 for _, right in pairs)
    denominator = math.sqrt(left_variance * right_variance)
    if denominator == 0:
        raise ValueError("CORREL cannot calculate a constant data series")
    return numerator / denominator


def _excel_rank(number: BrainValue, values: Sequence[BrainValue], order: BrainValue = 0) -> int:
    target = _number(number)
    numeric = _numeric_values(values)
    if _number(order) == 0:
        return 1 + sum(value > target for value in numeric)
    return 1 + sum(value < target for value in numeric)


def _evaluate_function(name: str, args: list[Any]) -> BrainValue:
    flattened = _flatten(args)
    numeric = _numeric_values(flattened)

    if name == "SUM":
        return sum(numeric)
    if name == "MIN":
        return min(numeric)
    if name == "MAX":
        return max(numeric)
    if name == "AVERAGE":
        if not numeric:
            raise ValueError("AVERAGE requires at least one numeric value")
        return sum(numeric) / len(numeric)
    if name == "CORREL":
        return _excel_correl(args[0], args[1])
    if name == "RANK":
        order = args[2] if len(args) > 2 else 0
        return _excel_rank(args[0], args[1], order)
    if name == "REPT":
        count = int(_number(args[1]))
        if count < 0:
            raise ValueError("REPT count cannot be negative")
        return str(args[0]) * count
    raise ValueError(f"Unsupported compiled Excel function: {name}")


def _evaluate(node: FormulaNode, cells: Mapping[str, BrainValue]) -> Any:
    if not isinstance(node, tuple):
        return node

    kind = node[0]
    if kind == "cell":
        return cells.get(node[1])
    if kind == "range":
        return [cells.get(coordinate) for coordinate in node[1]]
    if kind == "unary":
        value = _number(_evaluate(node[2], cells))
        return value if node[1] == "+" else -value
    if kind == "binary":
        operator = node[1]
        left = _evaluate(node[2], cells)
        right = _evaluate(node[3], cells)
        if operator == "=":
            return left == right
        if operator == "<>":
            return left != right
        if operator == ">":
            return _number(left) > _number(right)
        if operator == "<":
            return _number(left) < _number(right)
        if operator == ">=":
            return _number(left) >= _number(right)
        if operator == "<=":
            return _number(left) <= _number(right)
        if operator == "&":
            return f"{'' if left is None else left}{'' if right is None else right}"

        left_number = _number(left)
        right_number = _number(right)
        if operator == "+":
            return left_number + right_number
        if operator == "-":
            return left_number - right_number
        if operator == "*":
            return left_number * right_number
        if operator == "/":
            return left_number / right_number
        if operator == "^":
            return left_number**right_number
        raise ValueError(f"Unsupported compiled Excel operator: {operator}")
    if kind == "func":
        name = node[1]
        arguments = node[2]
        if name == "IF":
            branch = arguments[1] if _evaluate(arguments[0], cells) else arguments[2]
            return _evaluate(branch, cells)
        if name == "IFS":
            for index in range(0, len(arguments), 2):
                if _evaluate(arguments[index], cells):
                    return _evaluate(arguments[index + 1], cells)
            raise ValueError("IFS had no matching condition")
        return _evaluate_function(name, [_evaluate(argument, cells) for argument in arguments])
    raise ValueError(f"Unsupported compiled formula node: {kind}")


def evaluate_cells(
    static_cells: Mapping[str, BrainValue],
    formulas: Sequence[tuple[str, FormulaNode]],
    inputs: Mapping[str, BrainValue],
) -> dict[str, BrainValue]:
    """Evaluate a compiled workbook for one set of scoring inputs."""
    missing = sorted(set(INPUT_CELLS) - set(inputs))
    if missing:
        raise ValueError(f"Brain input is missing fields: {', '.join(missing)}")

    cells = dict(static_cells)
    cells.update({coordinate: inputs[name] for name, coordinate in INPUT_CELLS.items()})
    for coordinate, formula in formulas:
        cells[coordinate] = _evaluate(formula, cells)
    return cells


def build_brain_output(cells: Mapping[str, BrainValue], field_rows: Sequence[int]) -> dict[str, list[dict]]:
    """Build the historical report payload from evaluated workbook cells."""
    fields = []
    for row in field_rows:
        c1 = cells.get(f"CE{row}")
        c2 = cells.get(f"CF{row}")
        fields.append(
            {
                "Branch": cells.get(f"B{row}"),
                "BranchId": int(_number(cells.get(f"C{row}"))),
                "Field": cells.get(f"D{row}"),
                "Women": cells.get(f"E{row}"),
                "Man": cells.get(f"F{row}"),
                "Theme": cells.get(f"G{row}"),
                "ThemeId": cells.get(f"H{row}"),
                "Ratio": int(_number(cells.get(f"I{row}"))),
                "Capabilities": cells.get(f"CC{row}"),
                "Personality": cells.get(f"CD{row}"),
                "C1": None if c1 in (None, "") else c1,
                "C2": None if c2 in (None, "") else c2,
                "IQStars": cells.get(f"CI{row}"),
                "PersonalityStars": cells.get(f"CJ{row}"),
                "Color": cells.get(f"CK{row}"),
                "Scatter": cells.get(f"CL{row}"),
            }
        )

    branches = [
        {"Branch": cells.get(f"CM{row}"), "Value": cells.get(f"CN{row}")}
        for row in range(1, 8)
    ]
    categories = [
        {"Category": cells.get(f"CM{row}"), "Value": cells.get(f"CN{row}")}
        for row in range(10, 28)
    ]
    return {"fields": fields, "branches": branches, "categories": categories}


def calculate_brain(
    static_cells: Mapping[str, BrainValue],
    formulas: Sequence[tuple[str, FormulaNode]],
    field_rows: Sequence[int],
    inputs: Mapping[str, BrainValue],
) -> dict[str, list[dict]]:
    cells = evaluate_cells(static_cells, formulas, inputs)
    return build_brain_output(cells, field_rows)
