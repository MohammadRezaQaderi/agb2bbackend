"""Compile PSY exam workbooks into versioned Python package data.

Example:
    python scripts/compile_psy_workbooks.py \
        /path/to/finalexams/exams \
        --version v1 \
        --assets-output /path/to/runtime/Quiz

The application never reads the Excel files at runtime. Recompile changed source
files under a new version so attempts already tied to an older version remain
reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import pprint
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "quiz_packages" / "psy" / "versions"
DEFAULT_MANIFEST = ROOT / "quiz_packages" / "psy" / "generated_manifest.py"

SLUG_ALIASES = {
    "motivatiom": "motivation",
    "coping_strategies": "coping_strategies",
    "eq_iq": "eq_iq",
    "scl90": "scl90",
    "study_skills": "study_skills",
}
TYPE_NAMES = {"متنی": "text", "تصویری": "pic", "text": "text", "pic": "pic"}
MBTI_ANSWER_IDS = {"الف": 1, "ب": 2}


class WorkbookValidationError(ValueError):
    pass


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ").strip()


def _scale(value: Any) -> str:
    return " ".join(_text(value).split())


def _integer(value: Any, field: str, row_number: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise WorkbookValidationError(f"row {row_number}: {field} must be an integer") from exc
    return number


def _score(value: Any) -> int | float:
    if value in (None, ""):
        return 0
    number = float(value)
    return int(number) if number.is_integer() else number


def _slug(folder_name: str) -> str:
    source_name = folder_name.split(".", 1)[-1]
    normalized = re.sub(r"[^a-z0-9]+", "_", source_name.lower()).strip("_")
    normalized = SLUG_ALIASES.get(normalized, normalized)
    if not normalized:
        raise WorkbookValidationError(f"cannot derive package name from {folder_name!r}")
    return normalized


def _module_version(version: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", version.strip())
    if not normalized or normalized[0].isdigit():
        normalized = f"v_{normalized}"
    return normalized


def _source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_index(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        return {}
    indexed: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        key = path.stem.casefold()
        if key in indexed:
            raise WorkbookValidationError(f"duplicate asset stem in {directory}: {path.stem}")
        indexed[key] = path
    return indexed


def _register_asset(
    jobs: dict[str, Path],
    source_index: dict[str, Path],
    source_name: str,
    output_stem: str,
) -> str:
    source = source_index.get(source_name.casefold())
    if source is None:
        raise WorkbookValidationError(f"referenced image is missing: {source_name}")
    output_name = f"{output_stem}.JPG"
    previous = jobs.setdefault(output_name, source)
    if previous != source:
        raise WorkbookValidationError(f"asset output collision: {output_name}")
    return output_stem


def _convert_asset(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.load()
        if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        image.save(destination, format="JPEG", quality=92, optimize=True)


def _common_question(
    row: tuple[Any, ...],
    row_number: int,
    subscale_index: int,
    answer_width: int,
    package_name: str,
    question_assets: dict[str, Path],
    answer_assets: dict[str, Path],
    asset_jobs: dict[str, Path],
) -> tuple[dict[str, Any], dict[str, Any]]:
    question_id = _integer(row[3], "questionnumber", row_number)
    answer_count = _integer(row[6], "answersnumber", row_number)
    if answer_count < 1 or answer_count > answer_width:
        raise WorkbookValidationError(f"row {row_number}: invalid answersnumber {answer_count}")

    question_type = TYPE_NAMES.get(_text(row[5]))
    answer_type = TYPE_NAMES.get(_text(row[9]))
    if not question_type or not answer_type:
        raise WorkbookValidationError(f"row {row_number}: unsupported question or answer type")

    question_text = _text(row[4])
    if question_type == "pic":
        question_text = _register_asset(
            asset_jobs,
            question_assets,
            question_text,
            f"{package_name.lower()}_q_{question_text.lower()}",
        )

    score_start = subscale_index + 1
    scale_name = _scale(row[subscale_index])
    if not scale_name:
        raise WorkbookValidationError(f"row {row_number}: subscale is required")

    answers = []
    answer_scores: dict[int, tuple[tuple[str, int | float], ...]] = {}
    for offset in range(answer_count):
        answer_id = offset + 1
        answer_text = _text(row[10 + offset])
        if not answer_text:
            raise WorkbookValidationError(f"row {row_number}: answer {answer_id} is empty")
        if answer_type == "pic":
            answer_text = _register_asset(
                asset_jobs,
                answer_assets,
                answer_text,
                f"{package_name.lower()}_a_{answer_text.lower()}",
            )
        answers.append({"answer_id": answer_id, "answer_text": answer_text})
        answer_scores[answer_id] = ((scale_name, _score(row[score_start + offset])),)

    question = {
        "question_id": question_id,
        "question_answer": "",
        "first_question": question_text,
        "second_question": "",
        "first_q_type": question_type,
        "second_q_type": question_type,
        "answers_num": answer_count,
        "max_answer_select": _integer(row[8], "max", row_number),
        "min_answer_select": _integer(row[7], "min", row_number),
        "answers_type": answer_type,
        "answers": answers,
    }
    scoring = {"question_id": question_id, "answers": answer_scores}
    return question, scoring


def _compile_common(package_name: str, workbook_path: Path) -> dict[str, Any]:
    worksheet = load_workbook(workbook_path, read_only=True, data_only=True)["exams"]
    headers = [cell.value for cell in worksheet[1]]
    try:
        subscale_index = next(i for i, value in enumerate(headers) if _text(value).lower() == "subscale")
    except StopIteration as exc:
        raise WorkbookValidationError(f"{workbook_path}: subscale header is missing") from exc

    answer_width = subscale_index - 10
    if answer_width < 1:
        raise WorkbookValidationError(f"{workbook_path}: answer columns are invalid")
    label_index = subscale_index + answer_width + 1

    question_assets = _asset_index(workbook_path.parent / "qu")
    answer_assets = _asset_index(workbook_path.parent / "asn") or _asset_index(workbook_path.parent / "ans")
    asset_jobs: dict[str, Path] = {}
    quizzes: OrderedDict[int, dict[str, Any]] = OrderedDict()
    scoring_questions: list[dict[str, Any]] = []
    scale_labels: OrderedDict[str, str] = OrderedDict()
    seen_question_ids: set[int] = set()

    for row_number, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), 2):
        if row[4] is None:
            continue
        quiz_id = _integer(row[1], "examcode", row_number)
        section_id = _integer(row[2], "sectionnumber", row_number)
        quiz_name = _text(row[0])
        if not quiz_name:
            raise WorkbookValidationError(f"row {row_number}: examname is required")

        question, scoring = _common_question(
            row,
            row_number,
            subscale_index,
            answer_width,
            package_name,
            question_assets,
            answer_assets,
            asset_jobs,
        )
        question_id = question["question_id"]
        if question_id in seen_question_ids:
            raise WorkbookValidationError(f"row {row_number}: duplicate question ID {question_id}")
        seen_question_ids.add(question_id)
        scoring_questions.append(scoring)

        scale_name = next(iter(scoring["answers"].values()))[0][0]
        label = _text(row[label_index]) if label_index < len(row) else ""
        scale_labels.setdefault(scale_name, label or scale_name)

        quiz = quizzes.setdefault(quiz_id, {"name": quiz_name, "sections": OrderedDict()})
        if quiz["name"] != quiz_name:
            raise WorkbookValidationError(f"row {row_number}: exam {quiz_id} has inconsistent names")
        quiz["sections"].setdefault(section_id, []).append(question)

    expected_ids = list(range(1, len(seen_question_ids) + 1))
    if sorted(seen_question_ids) != expected_ids:
        raise WorkbookValidationError(f"{workbook_path}: question IDs must be sequential from 1")

    return _finish_package(package_name, quizzes, scoring_questions, scale_labels, asset_jobs)


def _compile_mbti(package_name: str, workbook_path: Path) -> dict[str, Any]:
    worksheet = load_workbook(workbook_path, read_only=True, data_only=True)["exams"]
    questions = []
    scoring_questions = []
    scale_labels: OrderedDict[str, str] = OrderedDict()

    for question_id, row in enumerate(
        (row for row in worksheet.iter_rows(min_row=2, values_only=True) if any(value is not None for value in row)),
        1,
    ):
        prompt = _text(row[0])
        option_texts = (_text(row[1]), _text(row[2]))
        if not prompt or not all(option_texts):
            raise WorkbookValidationError(f"MBTI row {question_id + 1}: question and both answers are required")

        contributions: dict[int, list[tuple[str, int | float]]] = {1: [], 2: []}
        for score_index, answer_index, scale_index in ((3, 4, 7), (5, 6, 9)):
            answer_id = MBTI_ANSWER_IDS.get(_text(row[answer_index]))
            scale_name = _scale(row[scale_index])
            if answer_id is None or not scale_name:
                raise WorkbookValidationError(f"MBTI row {question_id + 1}: invalid scoring mapping")
            contributions[answer_id].append((scale_name, _score(row[score_index])))
            scale_labels.setdefault(scale_name, scale_name)

        questions.append(
            {
                "question_id": question_id,
                "question_answer": "",
                "first_question": prompt,
                "second_question": "",
                "first_q_type": "text",
                "second_q_type": "text",
                "answers_num": 2,
                "max_answer_select": 1,
                "min_answer_select": 1,
                "answers_type": "text",
                "answers": [
                    {"answer_id": 1, "answer_text": option_texts[0]},
                    {"answer_id": 2, "answer_text": option_texts[1]},
                ],
            }
        )
        scoring_questions.append(
            {"question_id": question_id, "answers": {key: tuple(value) for key, value in contributions.items()}}
        )

    quizzes = OrderedDict({1: {"name": "MBTI", "sections": OrderedDict({1: questions})}})
    return _finish_package(package_name, quizzes, scoring_questions, scale_labels, {})


def _finish_package(
    package_name: str,
    quizzes: OrderedDict[int, dict[str, Any]],
    scoring_questions: list[dict[str, Any]],
    scale_labels: OrderedDict[str, str],
    asset_jobs: dict[str, Path],
) -> dict[str, Any]:
    quiz_data = []
    summaries = []
    for quiz_id, source_quiz in quizzes.items():
        sections = []
        for section_id, questions in source_quiz["sections"].items():
            sections.append(
                {
                    "section_id": section_id,
                    "time": "",
                    "name": source_quiz["name"],
                    "description": "",
                    "voice": "default_voice.ogg",
                    "question_num": len(questions),
                    "questions": questions,
                }
            )
        quiz_data.append(
            {
                "quiz_id": quiz_id,
                "name": source_quiz["name"],
                "voice": None,
                "description": "",
                "have_time": "",
                "section_num": len(sections),
                "sections": sections,
            }
        )
        summaries.append(
            {
                "id": quiz_id,
                "quizName": source_quiz["name"],
                "voice": None,
                "description": "",
                "pic": "default.png",
                "ImageURL": "default.png",
            }
        )
    return {
        "package_name": package_name,
        "quizzes": quiz_data,
        "quiz_summaries": summaries,
        "scoring_questions": scoring_questions,
        "subscale_labels": dict(scale_labels),
        "assets": asset_jobs,
    }


def compile_source(source_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    workbook_paths = sorted(
        source_root.glob("*/exams.xlsx"),
        key=lambda path: int(path.parent.name.split(".", 1)[0]),
    )
    if not workbook_paths:
        raise WorkbookValidationError(f"no exams.xlsx files found below {source_root}")

    packages: OrderedDict[str, dict[str, Any]] = OrderedDict()
    assets: dict[str, Path] = {}
    for workbook_path in workbook_paths:
        slug = _slug(workbook_path.parent.name)
        package_name = f"PSY_{slug.upper()}"
        worksheet = load_workbook(workbook_path, read_only=True, data_only=True)["exams"]
        first_header = _text(worksheet.cell(1, 1).value).lower()
        package = (
            _compile_mbti(package_name, workbook_path)
            if first_header == "questions"
            else _compile_common(package_name, workbook_path)
        )
        package["source_sha256"] = _source_digest(workbook_path)
        if package_name in packages:
            raise WorkbookValidationError(f"duplicate package name: {package_name}")
        packages[package_name] = package
        for output_name, source in package.pop("assets").items():
            previous = assets.setdefault(output_name, source)
            if previous != source:
                raise WorkbookValidationError(f"asset output collision: {output_name}")
    return dict(packages), assets


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_generated_data(
    packages: dict[str, dict[str, Any]],
    version: str,
    output_root: Path,
    manifest_path: Path,
) -> Path:
    module_version = _module_version(version)
    output_path = output_root / module_version / "data.py"
    _write_text(output_path.parent / "__init__.py", '"""Generated PSY package version."""\n')
    content = (
        '"""Generated by scripts/compile_psy_workbooks.py; do not edit manually."""\n\n'
        f"DEFINITION_VERSION = {version!r}\n"
        f"SCORING_VERSION = {version!r}\n\n"
        f"PACKAGES = {pprint.pformat(packages, width=120, sort_dicts=False)}\n"
    )
    _write_text(output_path, content)
    manifest = (
        '"""Active generated PSY package version; updated by the compiler."""\n\n'
        f"LATEST_VERSION = {version!r}\n"
        f"LATEST_MODULE = {f'quiz_packages.psy.versions.{module_version}.data'!r}\n"
        f"PACKAGE_NAMES = {tuple(packages)!r}\n"
    )
    _write_text(manifest_path, manifest)
    return output_path


def install_assets(assets: dict[str, Path], output_directory: Path) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    for output_name, source in sorted(assets.items()):
        _convert_asset(source, output_directory / output_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Directory containing numbered package folders")
    parser.add_argument("--version", default="v1", help="Immutable definition/scoring version")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--assets-output",
        type=Path,
        help="Runtime Quiz directory. If omitted, assets are validated but not copied.",
    )
    args = parser.parse_args(argv)

    packages, assets = compile_source(args.source.resolve())
    output_path = write_generated_data(packages, args.version, args.output_root, args.manifest)
    if args.assets_output:
        install_assets(assets, args.assets_output.resolve())

    quiz_count = sum(len(package["quizzes"]) for package in packages.values())
    question_count = sum(len(package["scoring_questions"]) for package in packages.values())
    print(f"Compiled {len(packages)} packages, {quiz_count} quizzes, and {question_count} questions")
    print(f"Generated Python: {output_path}")
    if args.assets_output:
        print(f"Installed {len(assets)} assets in {args.assets_output.resolve()}")
    elif assets:
        print(f"Validated {len(assets)} assets; pass --assets-output to install them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
