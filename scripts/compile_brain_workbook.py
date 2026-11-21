"""Compile Brain.xlsx into a dependency-free Python workbook module.

Usage:
    python scripts/compile_brain_workbook.py /path/to/Brain.xlsx
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.formula import Tokenizer
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.formula import ArrayFormula

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helper.office.brain_formula_runtime import INPUT_CELLS, evaluate_cells  # noqa: E402


DEFAULT_OUTPUT = ROOT / "quiz_packages" / "ag" / "legacy_v1" / "generated_brain.py"
SUPPORTED_FUNCTIONS = {"AVERAGE", "CORREL", "IF", "IFS", "MAX", "MIN", "RANK", "REPT", "SUM"}
PRECEDENCE = {"=": 1, "<>": 1, "<": 1, ">": 1, "<=": 1, ">=": 1, "&": 2, "+": 3, "-": 3, "*": 4, "/": 4, "^": 5}


def _normalize_coordinate(value: str) -> str:
    if "!" in value or "[" in value:
        raise ValueError(f"Cross-sheet and external references are not supported: {value}")
    return value.replace("$", "").upper()


def _range_coordinates(value: str) -> tuple[str, ...]:
    reference = _normalize_coordinate(value)
    if ":" not in reference:
        return (reference,)
    min_col, min_row, max_col, max_row = range_boundaries(reference)
    from openpyxl.utils import get_column_letter

    return tuple(
        f"{get_column_letter(column)}{row}"
        for row in range(min_row, max_row + 1)
        for column in range(min_col, max_col + 1)
    )


class FormulaParser:
    def __init__(self, formula: str):
        self.tokens = [token for token in Tokenizer(formula).items if token.type != "WHITE-SPACE"]
        self.position = 0

    def parse(self):
        node = self._expression()
        if self.position != len(self.tokens):
            raise ValueError(f"Unexpected formula token: {self.tokens[self.position]}")
        return node

    def _peek(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _take(self):
        token = self._peek()
        if token is None:
            raise ValueError("Unexpected end of formula")
        self.position += 1
        return token

    def _expression(self, minimum_precedence: int = 0):
        node = self._primary()
        while True:
            token = self._peek()
            if token is None or token.type != "OPERATOR-INFIX":
                break
            precedence = PRECEDENCE.get(token.value)
            if precedence is None:
                raise ValueError(f"Unsupported Excel operator: {token.value}")
            if precedence < minimum_precedence:
                break
            operator = self._take().value
            next_precedence = precedence if operator == "^" else precedence + 1
            node = ("binary", operator, node, self._expression(next_precedence))
        return node

    def _primary(self):
        token = self._take()
        if token.type == "OPERATOR-PREFIX":
            if token.value not in {"+", "-"}:
                raise ValueError(f"Unsupported Excel prefix operator: {token.value}")
            return ("unary", token.value, self._primary())
        if token.type == "PAREN" and token.subtype == "OPEN":
            node = self._expression()
            closing = self._take()
            if closing.type != "PAREN" or closing.subtype != "CLOSE":
                raise ValueError("Unclosed Excel formula parenthesis")
            return node
        if token.type == "FUNC" and token.subtype == "OPEN":
            name = token.value[:-1].upper().removeprefix("_XLFN.")
            if name not in SUPPORTED_FUNCTIONS:
                raise ValueError(f"Unsupported Excel function: {name}")
            arguments = []
            closing = self._peek()
            if closing is not None and closing.type == "FUNC" and closing.subtype == "CLOSE":
                self._take()
                return ("func", name, tuple(arguments))
            while True:
                arguments.append(self._expression())
                separator = self._take()
                if separator.type == "FUNC" and separator.subtype == "CLOSE":
                    break
                if separator.type != "SEP" or separator.subtype != "ARG":
                    raise ValueError(f"Expected a function argument separator, got {separator}")
            return ("func", name, tuple(arguments))
        if token.type != "OPERAND":
            raise ValueError(f"Unsupported Excel formula token: {token}")
        if token.subtype == "RANGE":
            coordinates = _range_coordinates(token.value)
            if len(coordinates) == 1:
                return ("cell", coordinates[0])
            return ("range", coordinates)
        if token.subtype == "NUMBER":
            value = float(token.value)
            return int(value) if value.is_integer() else value
        if token.subtype == "TEXT":
            return token.value[1:-1].replace('""', '"')
        if token.subtype == "LOGICAL":
            return token.value.upper() == "TRUE"
        raise ValueError(f"Unsupported Excel operand: {token.value} ({token.subtype})")


def _formula_text(value: Any) -> str:
    if isinstance(value, ArrayFormula):
        return value.text
    if isinstance(value, str):
        return value
    raise TypeError(f"Unsupported formula value: {value!r}")


def _dependencies(node: Any) -> set[str]:
    if not isinstance(node, tuple):
        return set()
    if node[0] == "cell":
        return {node[1]}
    if node[0] == "range":
        return set(node[1])
    dependencies = set()
    for child in node[1:]:
        if isinstance(child, tuple) and child and isinstance(child[0], tuple):
            for item in child:
                dependencies.update(_dependencies(item))
        else:
            dependencies.update(_dependencies(child))
    return dependencies


def _required_output_cells(last_field_row: int) -> set[str]:
    cells = set(INPUT_CELLS.values())
    for row in range(5, last_field_row + 1):
        for column in ("B", "C", "D", "E", "F", "G", "H", "I", "CC", "CD", "CE", "CF", "CI", "CJ", "CK", "CL"):
            cells.add(f"{column}{row}")
    for row in range(1, 8):
        cells.update((f"CM{row}", f"CN{row}"))
    for row in range(10, 28):
        cells.update((f"CM{row}", f"CN{row}"))
    return cells


def _select_required_formulas(formulas: dict[str, Any], required: set[str]) -> set[str]:
    selected = set()
    pending = list(required)
    while pending:
        coordinate = pending.pop()
        if coordinate in selected or coordinate not in formulas:
            continue
        selected.add(coordinate)
        pending.extend(_dependencies(formulas[coordinate]))
    return selected


def _topological_order(formulas: dict[str, Any], selected: set[str]) -> list[str]:
    dependencies = {
        coordinate: _dependencies(formulas[coordinate]) & selected
        for coordinate in selected
    }
    dependents: dict[str, set[str]] = defaultdict(set)
    for coordinate, refs in dependencies.items():
        for ref in refs:
            dependents[ref].add(coordinate)

    ready = deque(sorted(coordinate for coordinate, refs in dependencies.items() if not refs))
    ordered = []
    while ready:
        coordinate = ready.popleft()
        ordered.append(coordinate)
        for dependent in sorted(dependents[coordinate]):
            dependencies[dependent].discard(coordinate)
            if not dependencies[dependent]:
                ready.append(dependent)
    if len(ordered) != len(selected):
        unresolved = sorted(selected - set(ordered))
        raise ValueError(f"Workbook formulas contain a dependency cycle: {unresolved[:10]}")
    return ordered


def _same_value(actual: Any, expected: Any) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9)
    return actual == expected


def _render_mapping(values: dict[str, Any]) -> str:
    lines = ["{"]
    lines.extend(f"    {key!r}: {values[key]!r}," for key in sorted(values))
    lines.append("}")
    return "\n".join(lines)


def _render_formulas(formulas: tuple[tuple[str, Any], ...]) -> str:
    lines = ["("]
    lines.extend(f"    ({coordinate!r}, {formula!r})," for coordinate, formula in formulas)
    lines.append(")")
    return "\n".join(lines)


def compile_workbook(source: Path, output: Path) -> dict[str, Any]:
    workbook = load_workbook(source, data_only=False, read_only=False)
    cached_workbook = load_workbook(source, data_only=True, read_only=False)
    if len(workbook.worksheets) != 1:
        raise ValueError("Brain compiler currently requires exactly one worksheet")
    sheet = workbook.worksheets[0]
    cached_sheet = cached_workbook[sheet.title]
    if workbook._external_links:
        raise ValueError("Brain workbook must not contain external links")

    formulas = {}
    static_cells = {}
    for row in sheet.iter_rows():
        for cell in row:
            if cell.data_type == "f":
                formulas[cell.coordinate] = FormulaParser(_formula_text(cell.value)).parse()
            elif cell.value is not None:
                static_cells[cell.coordinate] = cell.value

    populated_field_rows = [row for row in range(5, sheet.max_row + 1) if sheet[f"B{row}"].value is not None]
    if not populated_field_rows:
        raise ValueError("Brain workbook does not contain field rows")
    last_field_row = max(populated_field_rows)
    field_rows = tuple(range(5, last_field_row + 1))
    required = _required_output_cells(last_field_row)
    selected = _select_required_formulas(formulas, required)
    ordered_coordinates = _topological_order(formulas, selected)

    needed_static = required.copy()
    for coordinate in selected:
        needed_static.update(_dependencies(formulas[coordinate]))
    compiled_static = {
        coordinate: value
        for coordinate, value in static_cells.items()
        if coordinate in needed_static
    }
    compiled_formulas = tuple((coordinate, formulas[coordinate]) for coordinate in ordered_coordinates)

    validation_inputs = {name: sheet[coordinate].value for name, coordinate in INPUT_CELLS.items()}
    evaluated = evaluate_cells(compiled_static, compiled_formulas, validation_inputs)
    mismatches = []
    for coordinate in ordered_coordinates:
        expected = cached_sheet[coordinate].value
        actual = evaluated[coordinate]
        if not _same_value(actual, expected):
            mismatches.append((coordinate, actual, expected))
    if mismatches:
        preview = "; ".join(f"{cell}: Python={actual!r}, Excel={expected!r}" for cell, actual, expected in mismatches[:10])
        raise ValueError(
            f"Compiled workbook did not match {len(mismatches)} cached Excel values. "
            f"Recalculate and save the workbook before compiling. {preview}"
        )

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    module = (
        '"""Generated from Brain.xlsx. Do not edit by hand.\n\n'
        f"Source SHA-256: {digest}\n"
        'Regenerate with: python scripts/compile_brain_workbook.py /path/to/Brain.xlsx\n'
        '"""\n\n'
        "# ruff: noqa: E501\n\n"
        "from helper.office.brain_formula_runtime import calculate_brain\n\n"
        f"WORKBOOK_SHA256 = {digest!r}\n"
        f"WORKSHEET_NAME = {sheet.title!r}\n"
        f"STATIC_CELLS = {_render_mapping(compiled_static)}\n\n"
        f"FORMULAS = {_render_formulas(compiled_formulas)}\n\n"
        f"FIELD_ROWS = {field_rows!r}\n\n"
        "def calculate(inputs):\n"
        "    return calculate_brain(STATIC_CELLS, FORMULAS, FIELD_ROWS, inputs)\n"
    )
    output.write_text(module, encoding="utf-8")
    return {
        "source": str(source),
        "output": str(output),
        "sha256": digest,
        "formulas": len(compiled_formulas),
        "static_cells": len(compiled_static),
        "field_rows": len(field_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to Brain.xlsx")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Generated Python module")
    args = parser.parse_args()
    result = compile_workbook(args.source.resolve(), args.output.resolve())
    print(
        "Compiled {formulas} formulas and {static_cells} static cells for "
        "{field_rows} fields to {output} (SHA-256 {sha256})".format(**result)
    )


if __name__ == "__main__":
    main()
