from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping
import importlib.util

import arabic_reshaper
from bidi.algorithm import get_display
from lxml import etree

from helper.diagram.ag_report1.gauge_chart import MATCH_PRESET, render_gauge_chart

_HERE = Path(__file__).resolve().parent
_RTL_TEXT = re.compile(r"[\u0600-\u06ff]")

BRANCHES = (
    (1, "علوم تجربی", "#E39B00"),
    (2, "ریاضی و فیزیک", "#E8505B"),
    (3, "علوم انسانی", "#9DB000"),
    (4, "هنر", "#1FA463"),
    (5, "مدیریت و خدمات", "#2F6FD6"),
    (6, "کشاورزی و امور دامی", "#0FA3C9"),
    (7, "صنعت", "#8456C9"),
)
BRANCH_COLORS = {identifier: color for identifier, _, color in BRANCHES}
BRANCH_ID_BY_LABEL = {
    "علوم تجربی": 1, "ریاضی و فیزیک": 2, "علوم انسانی": 3, "هنر": 4,
    "گروه هنر": 4, "مدیریت و خدمات": 5, "گروه مدیریت و خدمات": 5,
    "کشاورزی و امور دامی": 6, "گروه کشاورزی": 6, "صنعت": 7, "گروه صنعت": 7,
}

# Domain keys intentionally correspond to the stable category labels used by
# the existing AG report tables and calculation output.
DOMAIN_TARGETS = (
    ("دبیری و آموزش", "image20.png"),
    ("مدیریت", "image22.png"),
    ("علوم پایه", "image24.png"),
    ("هنر", "image26.png"),
    ("مهندسی سازه و عمران", "image28.png"),
    ("مهندسی صنعتی", "image30.png"),
    ("مهندسی الکترونیک و کامپیوتر", "image32.png"),
    ("علوم انسانی", "image34.png"),
    ("مالی و حسابداری", "image36.png"),
    ("روان‌شناسی و خدمات اجتماعی", "image38.png"),
    ("روابط عمومی و رسانه", "image40.png"),
    ("کشاورزی و امور دامی", "image42.png"),
    ("حقوق و علوم سیاسی", "image44.png"),
    ("خدمات فنی", "image46.png"),
    ("تکنسین فنی", "image48.png"),
    ("درمانی – بالینی", "image50.png"),
    ("تشخیصی – درمانی", "image52.png"),
    ("تکنسین کامپیوتر", "image54.png"),
)
DOMAIN_ALIASES = {
    "دبیری": "دبیری و آموزش",
    "مهندسی سازه": "مهندسی سازه و عمران",
    "الکترونیک و کامپیوتر": "مهندسی الکترونیک و کامپیوتر",
    "روانشناسی": "روان‌شناسی و خدمات اجتماعی",
    "روان‌شناسی": "روان‌شناسی و خدمات اجتماعی",
    "روابط عمومی": "روابط عمومی و رسانه",
    "بالینی و درمانی": "درمانی – بالینی",
    "تشخیصی و درمانی": "تشخیصی – درمانی",
}

GAUGE_TARGETS = tuple(target for _, target in DOMAIN_TARGETS)
MEDIA_TARGETS = (
    "image7.png",
    "image18.png",
    *GAUGE_TARGETS,
    "image58.png",
)


def _load_chart_module(filename: str):
    """Load an isolated Report2 SVG renderer bundled with this adapter."""
    path = _HERE / filename
    if not path.is_file():
        raise FileNotFoundError(f"AG Report 2 chart source is missing: {path}")
    spec = importlib.util.spec_from_file_location(f"ag_report2_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load AG Report 2 chart source: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shape_svg_text(svg: str) -> bytes:
    root = etree.fromstring(svg.encode("utf-8"))
    for node in root.iter():
        if node.text and _RTL_TEXT.search(node.text):
            node.text = get_display(arabic_reshaper.reshape(node.text))
        if node.tail and _RTL_TEXT.search(node.tail):
            node.tail = get_display(arabic_reshaper.reshape(node.tail))
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def branch_id_for(branch: Mapping[str, Any]) -> int:
    identifier = branch.get("BranchId", branch.get("Id"))
    if identifier is not None:
        return int(identifier)
    label = str(branch.get("Branch", branch.get("name", ""))).strip()
    try:
        return BRANCH_ID_BY_LABEL[label]
    except KeyError as exc:
        raise ValueError(f"Unknown Report2 branch label: {label!r}") from exc


def _renderers(
    branches: list[Mapping[str, Any]],
    categories: list[Mapping[str, Any]],
    fields: list[Mapping[str, Any]],
) -> dict[str, Any]:
    branch_chart = _load_chart_module("branch_fit_chart.py")
    domains_chart = _load_chart_module("domains_bar_chart.py")
    scatter_chart = _load_chart_module("scatter_chart.py")

    branch_scores = {branch_id_for(branch): branch.get("Value") for branch in branches}
    branch_label_by_id = {identifier: label for identifier, label, _ in BRANCHES}
    branch_items = [
        {"name": branch_label_by_id.get(identifier, label), "score": branch_scores[identifier],
         "color": BRANCH_COLORS[identifier]}
        for identifier, label, _ in BRANCHES
        if identifier in branch_scores
    ]
    missing_branches = [label for identifier, label, _ in BRANCHES if identifier not in branch_scores]
    if missing_branches:
        raise ValueError(f"AG Report 2 branch scores are missing: {missing_branches}")
    domain_scores = {str(c.get("Category")): c.get("Value") for c in categories}
    for old, canonical in DOMAIN_ALIASES.items():
        if old in domain_scores and canonical not in domain_scores:
            domain_scores[canonical] = domain_scores[old]
    missing_domains = [name for name, _ in DOMAIN_TARGETS if name not in domain_scores]
    if missing_domains:
        raise ValueError(f"AG Report 2 category scores are missing: {missing_domains}")
    domain_items = [
        {"name": name, "score": domain_scores[name]}
        for name, _ in DOMAIN_TARGETS
        if name in domain_scores
    ]
    scatter_items = []
    for item in fields:
        identifier = int(item.get("BranchId", 0))
        branch_label = branch_label_by_id.get(identifier)
        if branch_label is None:
            continue
        scatter_items.append({
            "branch": branch_label,
            "name": str(item.get("Field") or ""),
            "fit": item.get("Personality", 0),
            # Keep the source Ratio unchanged; the renderer maps its legacy
            # Matplotlib marker area to an equivalent SVG circle radius.
            "popularity": item.get("Ratio", 0),
        })

    renderers = {
        "image7.png": lambda: branch_chart.render_branch_fit_chart(
            branch_items, width=1600, height=900, font="IRAN"
        ),
        "image18.png": lambda: domains_chart.render_domains_bar_chart(
            domain_items, sort=True, width=3200, height=2430, font="IRAN"
        ),
        "image58.png": lambda: scatter_chart.render_scatter_chart(
            scatter_items,
            branches=[(label, BRANCH_COLORS[identifier]) for identifier, label, _ in BRANCHES],
            width=1600,
            height=1608,
            font="IRAN",
        ),
    }
    if len(domain_items) != len(DOMAIN_TARGETS) or len(branch_items) != len(BRANCHES):
        raise ValueError(
            "AG Report 2 chart data is incomplete: "
            f"branches={len(branch_items)}/{len(BRANCHES)}, "
            f"domains={len(domain_items)}/{len(DOMAIN_TARGETS)}"
        )
    for domain_name, target in DOMAIN_TARGETS:
        score = domain_scores[domain_name]
        renderers[target] = lambda score=score: render_gauge_chart(
            score, **MATCH_PRESET, width=1500, height=960, font="IRAN", layout_scale=1.08
        )
    return renderers


def render_report_media(
    branches: list[Mapping[str, Any]],
    categories: list[Mapping[str, Any]],
    fields: list[Mapping[str, Any]],
    output_directory: Path | str,
) -> dict[str, Path]:
    """Render exact Report2 chart targets; leaves static template media intact."""
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("CairoSVG is required to render AG Report 2 charts") from exc

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    renderers = _renderers(branches, categories, fields)
    expected = set(MEDIA_TARGETS)
    if set(renderers) != expected:
        missing = sorted(expected - set(renderers))
        extra = sorted(set(renderers) - expected)
        raise ValueError(f"AG Report 2 renderer map mismatch; missing={missing}, extra={extra}")

    rendered: dict[str, Path] = {}
    for target in MEDIA_TARGETS:
        destination = output / target
        cairosvg.svg2png(bytestring=_shape_svg_text(renderers[target]()), write_to=str(destination))
        rendered[target] = destination
    return rendered


def persianize_text(value: Any) -> str:
    """Convert user-visible Report2 digits while leaving data untouched."""
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
