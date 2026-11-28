"""Shared SCL report context, rendering registry, and staged publication."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from helper.diagram import bar
from helper.diagram.scl_report3.report import render_r3_visuals
from helper.office.word_helper import (
    generate_fifth_report_documents,
    generate_forth_report_documents,
    generate_third_report_documents,
)
from helper.office.scl_psshi import (
    PSSHI_OUTPUT_NAME,
    generate_study_skills_report_documents,
)
from quiz_packages.scl.legacy_v1.scoring import bookmark_scl_object


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class SCLStudentIdentity:
    user_id: str
    name: str
    phone: str
    institute_name: str
    consultant_name: str
    logo_path: str | None


@dataclass(frozen=True, slots=True)
class SCLReportContext:
    """Immutable result of one SCL scoring and presentation-data pass."""

    student: SCLStudentIdentity
    labels: Mapping[str, Any]
    factor_scores: Mapping[str, float]
    severity_states: Mapping[str, str]
    priorities: Mapping[str, str]
    selected_advice: Mapping[str, str]
    report3_user_info: Mapping[str, Any]
    report3_text_replacements: Mapping[str, Any]
    report3_layer_order: Mapping[str, tuple[str, ...]]
    report3_needed: tuple[str, ...]
    report3_unneeded: tuple[str, ...]
    report3_color_targets: tuple[str, ...]
    report3_color_values: tuple[str, ...]
    report4_user_info: Mapping[str, Any]
    report4_kind: str | None
    report5_user_info: Mapping[str, Any]
    report5_needed: tuple[str, ...]
    report5_unneeded: tuple[str, ...]
    report5_categories: tuple[str, ...]
    report5_values: tuple[float, ...]
    report5_colors: tuple[str, ...]
    image_selections: Mapping[str, tuple[str, str]]
    active_ocd_subtypes: tuple[str, ...]
    active_ocd_count_asset: str | None


def make_scl_report_context(**values: Any) -> SCLReportContext:
    """Freeze mutable scheduler values at the scoring/rendering boundary."""
    for name in (
        "labels", "factor_scores", "severity_states", "priorities", "selected_advice",
        "report3_user_info", "report3_text_replacements", "report4_user_info",
        "report5_user_info", "image_selections", "report3_layer_order",
    ):
        values[name] = _freeze(values[name])
    for name in (
        "report3_needed", "report3_unneeded", "report5_needed", "report5_unneeded",
        "report3_color_targets", "report3_color_values", "report5_categories", "report5_values",
        "report5_colors", "active_ocd_subtypes",
    ):
        values[name] = tuple(values[name])
    values["student"] = SCLStudentIdentity(**values["student"])
    return SCLReportContext(**values)


# Index order matches the existing SCL renderer: severe, moderate, mild, normal.
# Targets were audited against the supplied Report3 DOCX's actual drawing references.
SCL_REPORT3_IMAGE_MAP: Mapping[str, tuple[tuple[str, str], ...]] = MappingProxyType({
    "drug_addicion": (("image30.png", "drog4.png"), ("image29.png", "drog3.png"),
                       ("image27.png", "drog2.png"), ("image26.png", "drog1.png")),
    "body_problem": (("image36.png", "physical problems4.png"), ("image35.png", "physical problems3.png"),
                      ("image34.png", "physical problems2.png"), ("image33.png", "physical problems1.png")),
    "sleep_problem": (("image42.png", "sleep4.png"), ("image41.png", "sleep3.png"),
                       ("image40.png", "sleep2.png"), ("image39.png", "sleep1.png")),
    "game_addiction": (("image48.png", "game4.png"), ("image47.png", "game3.png"),
                       ("image46.png", "game2.png"), ("image45.png", "game1.png")),
    "wage_future": (("image54.png", "lack of foresight4.png"), ("image53.png", "lack of foresight3.png"),
                    ("image52.png", "lack of foresight2.png"), ("image51.png", "lack of foresight1.png")),
    "study_problem": (("image60.png", "study .weakness4.png"), ("image59.png", "study .weakness3.png"),
                       ("image58.png", "study .weakness2.png"), ("image57.png", "study .weakness1.png")),
    "anxiety": (("image81.png", "anxiety4.png"), ("image80.png", "anxiety3.png"),
                ("image78.png", "anxiety2.png"), ("image77.png", "anxiety1.png")),
    "depression": (("image88.png", "depression4.png"), ("image87.png", "depression3.png"),
                   ("image86.png", "depression2.png"), ("image84.png", "depression1.png")),
    # Existing subtype-priority order is retained; these four drawings sit beside
    # the matching subtype descriptions in the supplied template.
    "ocd": (("image91.png", "ocd3.png"), ("image92.png", "ocd4.png"),
            ("image93.png", "ocd2.png"), ("image94.png", "ocd1.png")),
    "motivation": (("image105.png", "unmotivated4.png"), ("image104.png", "unmotivated3.png"),
                   ("image103.png", "unmotivated2.png"), ("image102.png", "unmotivated1.png")),
    "self_confident": (("image111.png", "Lack of self-confidence4.png"),
                       ("image110.png", "Lack of self-confidence3.png"),
                       ("image109.png", "Lack of self-confidence2.png"),
                       ("image108.png", "Lack of self-confidence1.png")),
    "adhd": (("image130.png", "hyperactivity4.png"), ("image129.png", "hyperactivity3.png"),
             ("image128.png", "hyperactivity2.png"), ("image127.png", "hyperactivity1.png")),
    "family_problem": (("image137.png", "family problem4.png"), ("image136.png", "family problem3.png"),
                       ("image134.png", "family problem2.png"), ("image133.png", "family problem1.png")),
    "interpersonal": (("image145.png", "Interpersonal problems4.png"),
                      ("image143.png", "Interpersonal problems3.png"),
                      ("image142.png", "Interpersonal problems2.png"),
                      ("image140.png", "Interpersonal problems1.png")),
    "truma": (("image158.png", "war4.png"), ("image157.png", "war3.png"),
              ("image156.png", "war2.png"), ("image155.png", "war1.png")),
    "ideal": (("image152.png", "perfectionism4.png"), ("image151.png", "perfectionism3.png"),
              ("image149.png", "perfectionism2.png"), ("image148.png", "perfectionism1.png")),
})

# The top OCD illustrations are beside the four subtype descriptions. Keep their
# media targets keyed by subtype, rather than selecting only one by priority.
SCL_REPORT3_OCD_SUBTYPE_TARGETS = MappingProxyType({
    "ocd1": "image94.png",
    "ocd2": "image93.png",
    "ocd3": "image91.png",
    "ocd4": "image92.png",
})

# The bottom illustration slots are explicitly associated with the DOCX labels:
# right-to-left Normal, Mild, Moderate, Severe. Count selection is computed only
# from active subtype scores; it is not derived from the overall OCD severity.
SCL_REPORT3_OCD_COUNT_ASSETS = MappingProxyType({
    1: "ocd11.png", 2: "ocd22.png", 3: "ocd33.png", 4: "ocd44.png",
})
SCL_REPORT3_OCD_COUNT_TARGETS = MappingProxyType({
    1: "image95.png", 2: "image96.png", 3: "image97.png", 4: "image98.png",
})
_REPORT3_SCORE_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?\Z")
_PERSIAN_SCORE_TRANSLATION = str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫")


def _format_report3_dynamic_scores(replacements: Mapping[str, Any]) -> dict[str, Any]:
    """Localize only numeric score tokens at the Report3 document boundary."""
    formatted = dict(replacements)
    for key, value in replacements.items():
        if not key.endswith("scorefast"):
            continue
        score = str(value)
        if not _REPORT3_SCORE_NUMBER_RE.fullmatch(score):
            raise ValueError(f"Invalid dynamic Report3 score for {key}: {value!r}")
        formatted[key] = score.translate(_PERSIAN_SCORE_TRANSLATION)
    return formatted


def report3_ocd_media_for_active_subtypes(
        active_subtypes: tuple[str, ...], count_asset: str | None,
) -> tuple[tuple[str, str], ...]:
    """Return explicit subtype/count artwork targets from the shared calculation."""
    if len(set(active_subtypes)) != len(active_subtypes):
        raise ValueError("Report3 active OCD subtype list contains duplicates")
    unknown = set(active_subtypes) - set(SCL_REPORT3_OCD_SUBTYPE_TARGETS)
    if unknown:
        raise ValueError(f"Unknown active SCL OCD subtypes: {sorted(unknown)}")

    active_count = len(active_subtypes)
    expected_asset = SCL_REPORT3_OCD_COUNT_ASSETS.get(active_count)
    if count_asset != expected_asset:
        raise ValueError(
            "Report3 OCD count asset does not match active subtype count: "
            f"count={active_count}, expected={expected_asset!r}, received={count_asset!r}"
        )

    media = [
        (SCL_REPORT3_OCD_SUBTYPE_TARGETS[subtype], f"{subtype}.png")
        for subtype in active_subtypes
    ]
    if active_count:
        target = SCL_REPORT3_OCD_COUNT_TARGETS.get(active_count)
        if target is None or expected_asset is None:
            raise ValueError(f"No Report3 OCD count illustration mapping for count {active_count}")
        media.append((target, expected_asset))
    return tuple(media)

SCL_REPORT3_HIDDEN_MARKER_REPLACEMENTS = MappingProxyType({
    **{name: "" for name in (
        "adhd_sh", "anx_sh", "body_sh", "conf_sh", "dep_sh", "drug_sh", "family_sh",
        "future_sh", "game_sh", "inter_sh", "mot_sh", "ocs_sh", "sleep_sh", "study_sh", "truma_sh",
    )},
    **{name: "" for name in (
        "Addiction_so", "Adhd_so", "Anx_so", "Body_so", "Con_so", "Dep_so", "Family_so", "Future_so",
        "Ideal_so", "Inter_so", "Mobile_so", "Mot_so", "Ocd_so", "Sleep_so", "Study_so", "Truma_so",
    )},
})


def select_scl_report3_media(
        factor_scores: Mapping[str, float],
        labels: Mapping[str, Any],
) -> tuple[Mapping[str, tuple[str, str]], tuple[str, ...], str | None]:
    """Select legacy factor illustrations and authoritative OCD subtype metadata."""
    selected: dict[str, tuple[str, str]] = {}
    ocd_labels = labels.get("OCD", {})
    subtype_scores = {}
    if isinstance(ocd_labels, Mapping):
        for subtype in ("ocd1", "ocd2", "ocd3", "ocd4"):
            count = bookmark_scl_object[subtype]["count"]
            subtype_scores[subtype] = float(ocd_labels.get(subtype, 0)) / count
    active_subtypes = tuple(key for key, value in subtype_scores.items() if value > 2)
    count_asset = SCL_REPORT3_OCD_COUNT_ASSETS.get(len(active_subtypes))

    for factor, choices in SCL_REPORT3_IMAGE_MAP.items():
        if factor not in factor_scores:
            continue
        if factor == "ocd" and subtype_scores:
            if subtype_scores.get("ocd2", 0) > 2:
                index = 3
            elif subtype_scores.get("ocd1", 0) > 2:
                index = 0
            elif subtype_scores.get("ocd3", 0) > 2:
                index = 1
            elif subtype_scores.get("ocd4", 0) > 2:
                index = 2
            else:
                index = 3
        else:
            score = factor_scores[factor]
            index = 0 if score >= 3 else 1 if score >= 2 else 2 if score >= 1 else 3
        selected[factor] = choices[index]
    return _freeze(selected), active_subtypes, count_asset


def select_scl_score_image_name(factor: str, score: float) -> str:
    """Keep the persisted score-image rule on the factor-score scale."""
    choices = SCL_REPORT3_IMAGE_MAP.get(factor)
    if not choices:
        return ""
    index = 0 if score >= 3 else 1 if score >= 2 else 2 if score >= 1 else 3
    return choices[index][1]


@dataclass(frozen=True, slots=True)
class SCLReportSpec:
    key: str
    output_filename: str | None
    required_when_selected: bool
    renderer: Callable[[SCLReportContext, Path, Path], Path] | None
    pending_owner_contract: bool = False


def _report3_renderer(context: SCLReportContext, output_dir: Path, assets_dir: Path) -> Path:
    import config

    visuals = render_r3_visuals(context, assets_dir)
    if set(context.image_selections) != set(SCL_REPORT3_IMAGE_MAP):
        raise ValueError("SCL Report3 requires one selected status illustration for all 16 factors")
    selected_targets = [target for target, _ in context.image_selections.values()]
    if len(selected_targets) != len(set(selected_targets)):
        raise ValueError("SCL Report3 status illustrations resolve to duplicate DOCX media targets")
    required_visuals = {"image5.png", "roadmap_surface", "roadmap_psych", "roadmap_root"}
    if set(visuals) != required_visuals:
        raise RuntimeError(f"SCL Report3 renderer returned an incomplete chart set: {sorted(required_visuals - set(visuals))}")
    media = []
    asset_dir = Path(config.SCL_ASSET_DIR)
    for factor, (target, asset) in context.image_selections.items():
        # OCD's four top illustrations are selected individually from the
        # authoritative active subtype set below. The legacy single OCD entry is
        # retained in context for its existing score-image consumer only.
        if factor == "ocd":
            continue
        source = asset_dir / asset
        if not source.is_file():
            raise FileNotFoundError(f"Required SCL Report3 asset is missing: {source}")
        destination = assets_dir / asset
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        media.append((target, destination))

    ocd_media = report3_ocd_media_for_active_subtypes(
        tuple(context.active_ocd_subtypes), context.active_ocd_count_asset,
    )
    for target, asset in ocd_media:
        source = asset_dir / asset
        if not source.is_file():
            raise FileNotFoundError(f"Required SCL Report3 OCD illustration is missing: {source}")
        destination = assets_dir / f"active_{target.removesuffix('.png')}_{asset}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        media.append((target, destination))

    media_targets = [target for target, _ in media]
    if len(media_targets) != len(set(media_targets)):
        raise ValueError("SCL Report3 media mapping contains duplicate DOCX targets")
    media.append(("image5.png", visuals["image5.png"]))

    if context.student.logo_path:
        logo = Path(context.student.logo_path)
        if not logo.is_file():
            raise FileNotFoundError(f"SCL Report3 logo file is missing: {logo}")
        media.append(("image4.png", logo))

    generate_third_report_documents(
        user_directory=output_dir,
        user_report_info=dict(context.report3_user_info),
        phone=context.student.phone,
        colors_tag=list(context.report3_color_targets),
        colors_color=list(context.report3_color_values),
        report_text_replacements=_format_report3_dynamic_scores(context.report3_text_replacements),
        needed=list(context.report3_needed),
        unneeded=list(context.report3_unneeded),
        image_replacements=media,
        roadmap_images={
            "surface": visuals["roadmap_surface"],
            "psych": visuals["roadmap_psych"],
            "root": visuals["roadmap_root"],
        },
    )
    return output_dir / "Report3.pdf"


def _report4_renderer(context: SCLReportContext, output_dir: Path, assets_dir: Path) -> Path:
    del assets_dir
    if context.report4_kind not in {"anxiety", "ocd", "depression"}:
        raise ValueError("Report4 renderer requires an anxiety/OCD/depression selection")
    logo_targets = {"anxiety": "image14.png", "ocd": "image17.png", "depression": "image12.png"}
    images = []
    if context.student.logo_path:
        images.append((logo_targets[context.report4_kind], context.student.logo_path))
    generate_forth_report_documents(
        user_directory=output_dir,
        user_report_info=dict(context.report4_user_info),
        report_name=context.report4_kind,
        phone=context.student.phone,
        image_replacements=images,
    )
    return output_dir / "Report4.pdf"


def _study_skills_renderer(context: SCLReportContext, output_dir: Path, assets_dir: Path) -> Path:
    del assets_dir
    import config

    psychological_order = tuple(context.report3_layer_order.get("psych", ()))
    return generate_study_skills_report_documents(
        template_path=config.SCL_PSSHI_TEMPLATE_PATH,
        user_directory=output_dir,
        student_name=context.student.name,
        consultant_name=context.student.consultant_name,
        institute_name=context.student.institute_name,
        phone=context.student.phone,
        logo_path=context.student.logo_path,
        labels=context.labels,
        psychological_order=psychological_order,
        psychological_scores=context.factor_scores,
    )


def _report5_renderer(context: SCLReportContext, output_dir: Path, assets_dir: Path) -> Path:
    if not context.report5_categories or not context.report5_values:
        raise ValueError("Report5 renderer requires chart categories and values")
    chart_prefix = bar.create_bar_chart(
        categories=list(context.report5_categories),
        title="ﯽﺘﺧﺎﻨﺸﻧﺍﻭﺭ ﻞﻣﺍﻮﻋ ﯼﻪﺴﯾﺎﻘﻣ ﺭﺍﺩﻮﻤﻧ",
        values=list(context.report5_values),
        colors=list(context.report5_colors),
        rotation=45,
        size=8,
        path=assets_dir,
        filename="image1",
    )
    chart = Path(f"{chart_prefix}.png")
    if not chart.is_file():
        raise FileNotFoundError(f"SCL Report5 overview chart was not created: {chart}")
    images = [("image4.png", chart)]
    if context.student.logo_path:
        logo = Path(context.student.logo_path)
        if not logo.is_file():
            raise FileNotFoundError(f"SCL Report5 logo file is missing: {logo}")
        images.append(("image21.png", logo))
    generate_fifth_report_documents(
        user_directory=output_dir,
        user_report_info=dict(context.report5_user_info),
        image_names=["image4.png"],
        user_report_pictures=[chart],
        phone=context.student.phone,
        image_replacements=images[1:],
        needed=list(context.report5_needed),
        unneeded=list(context.report5_unneeded),
    )
    return output_dir / "Report5.pdf"


SCL_REPORT_REGISTRY: Mapping[str, SCLReportSpec] = MappingProxyType({
    "report3": SCLReportSpec("report3", "Report3.pdf", True, _report3_renderer),
    "report4": SCLReportSpec("report4", "Report4.pdf", True, _report4_renderer),
    "report5": SCLReportSpec("report5", "Report5.pdf", True, _report5_renderer),
    "study_skills": SCLReportSpec("study_skills", PSSHI_OUTPUT_NAME, True, _study_skills_renderer),
})


def _validate_pdf(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 5:
        raise RuntimeError(f"SCL report renderer did not produce a non-empty PDF: {path.name}")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise RuntimeError(f"SCL report renderer produced an invalid PDF: {path.name}")


def _publish_reports_atomically(staged: list[tuple[Path, Path]], backup_dir: Path) -> None:
    moved: list[tuple[Path, Path | None, bool]] = []
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        for index, (source, target) in enumerate(staged):
            backup = None
            if target.exists():
                backup = backup_dir / f"{index}-{target.name}"
                os.replace(target, backup)
            moved.append((target, backup, False))
            os.replace(source, target)
            moved[-1] = (target, backup, True)
    except Exception:
        for target, backup, published in reversed(moved):
            if published and target.exists():
                target.unlink()
            if backup is not None and backup.exists():
                os.replace(backup, target)
        raise


def render_scl_report_set(context: SCLReportContext, output_dir: Path | str) -> tuple[str, ...]:
    """Render selected legacy outputs to staging, then publish verified PDFs."""
    import config

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not config.SCL_REPORT3_TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"SCL Report3 template is missing: {config.SCL_REPORT3_TEMPLATE_PATH}")
    if not config.SCL_PSSHI_TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"SCL PSSHI study-skills template is missing: {config.SCL_PSSHI_TEMPLATE_PATH}")
    if not config.SCL_ASSET_DIR.is_dir():
        raise FileNotFoundError(f"SCL image asset directory is missing: {config.SCL_ASSET_DIR}")

    active_specs = [SCL_REPORT_REGISTRY["report3"], SCL_REPORT_REGISTRY["study_skills"]]
    if context.report4_kind is not None:
        active_specs.append(SCL_REPORT_REGISTRY["report4"])
    if context.report5_categories and context.report5_values:
        active_specs.append(SCL_REPORT_REGISTRY["report5"])

    staged_outputs = []
    with tempfile.TemporaryDirectory(prefix="scl-report-job-", dir=output_dir) as temporary:
        stage_root = Path(temporary)
        assets_dir = stage_root / "assets"
        assets_dir.mkdir()
        for spec in active_specs:
            if spec.renderer is None or spec.output_filename is None:
                if spec.required_when_selected:
                    raise RuntimeError(f"Required SCL renderer is not configured: {spec.key}")
                continue
            report_dir = stage_root / spec.key
            report_dir.mkdir()
            rendered_pdf = spec.renderer(context, report_dir, assets_dir)
            _validate_pdf(rendered_pdf)
            staged_outputs.append((rendered_pdf, output_dir / spec.output_filename))

        _publish_reports_atomically(staged_outputs, stage_root / "backups")
    return tuple(target.name for _, target in staged_outputs)
