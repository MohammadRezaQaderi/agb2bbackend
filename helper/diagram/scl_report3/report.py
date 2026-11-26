"""Presentation-only adapters from the shared SCL context to supplied R3 charts."""

from __future__ import annotations

from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping

import arabic_reshaper
from bidi.algorithm import get_display
from lxml import etree

from . import chart_overview, fig_iceberg, fig_roadmap
from .svgkit import fa, text
from quiz_packages.scl.legacy_v1.report_bookmarks import CALC_DATA


# R3 chart aliases are deliberately distinct from the SCL and R5 factor keys.
R3_FACTOR_KEY_MAP: Mapping[str, tuple[str, str]] = MappingProxyType({
    "addict": ("drug_addicion", "addict"),
    "body": ("body_problem", "body"),
    "sleep": ("sleep_problem", "sleep"),
    "mobile": ("game_addiction", "game"),
    "future": ("wage_future", "future"),
    "study": ("study_problem", "study"),
    "anx": ("anxiety", "anx"),
    "dep": ("depression", "dep"),
    "ocd": ("ocd", "ocd"),
    "mot": ("motivation", "motive"),
    "conf": ("self_confident", "conf"),
    "adhd": ("adhd", "adhd"),
    "family": ("family_problem", "family"),
    "inter": ("interpersonal", "interp"),
    "ideal": ("ideal", "ideal"),
    "truma": ("truma", "ptsd"),
})

R3_STATE_LEVELS = MappingProxyType({
    "نرمال": 1,
    "نیازمند توجه": 2,
    "نگران کننده": 3,
    "بحرانی": 4,
})

_RTL_TEXT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

def build_r3_chart_scores(context) -> dict[str, dict[str, int | float]]:
    """Convert existing 0–4 SCL values to the chart's 0–100 and 1–4 contract.

    R3's displayed score is the already-computed out-of-10 ``scorefast`` value.
    Multiplying that presentation value by ten produces the chart's 0–100 scale.
    Severity levels come from the existing severity-state calculation, retaining
    its exact 0/1/2/3 boundaries.
    """
    expected_calc_keys = {calc_key for calc_key, _ in R3_FACTOR_KEY_MAP.values()}
    missing = expected_calc_keys - set(context.factor_scores)
    if missing:
        raise ValueError(f"Missing SCL factor scores for R3 chart: {sorted(missing)}")

    scores = {}
    for chart_key, (calc_key, prefix) in R3_FACTOR_KEY_MAP.items():
        raw_score = float(context.factor_scores[calc_key])
        if not 0 <= raw_score <= 4:
            raise ValueError(f"SCL factor score outside expected 0–4 range: {calc_key}={raw_score}")
        state = context.severity_states.get(calc_key)
        if state not in R3_STATE_LEVELS:
            raise ValueError(f"Missing or unknown SCL severity state for {calc_key}: {state!r}")
        score10 = context.report3_text_replacements.get(f"{prefix}scorefast")
        if score10 is None:
            raise ValueError(f"Missing Report3 out-of-10 score for {calc_key}")
        try:
            score100 = float(score10) * 10
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid Report3 out-of-10 score for {calc_key}: {score10!r}") from exc
        if not 0 <= score100 <= 100:
            raise ValueError(f"R3 presentation score outside 0–100 range: {calc_key}={score100}")
        scores[chart_key] = {"score": score100, "level": R3_STATE_LEVELS[state]}
    return scores


def build_r3_overview_svg(context) -> str:
    return chart_overview.chart(build_r3_chart_scores(context), vmax=100, thresholds=[0.25, 0.5, 0.75])


def build_r3_iceberg_svg() -> str:
    return fig_iceberg.iceberg()


def build_r3_roadmap_svg(context, layer: str) -> str:
    """Use the supplied roadmap art and fill its card positions from SCL context."""
    if layer not in fig_roadmap.STATIONS:
        raise ValueError(f"Unknown R3 roadmap layer: {layer}")
    chart = fig_roadmap.roadmap(layer)
    body = []
    factor_keys = fig_roadmap.STATIONS[layer]
    cards = fig_roadmap.layout(len(factor_keys))

    for chart_key, card in zip(factor_keys, cards):
        calc_key, prefix = R3_FACTOR_KEY_MAP[chart_key]
        name = CALC_DATA[calc_key]["name"]
        state = context.severity_states[calc_key]
        priority = context.priorities.get(calc_key)
        if not priority:
            raise ValueError(f"Missing SCL intervention priority for {calc_key}")
        score10 = str(context.report3_text_replacements[f"{prefix}scorefast"])
        score10_fa = fa(score10.replace(".", "٫"))
        cy = card["cy"]
        body.append(text(120, cy - 5.2, name, size=3.4, fill="#1F2A44", weight="bold"))
        body.append(text(120, cy + 0.3, f"وضعیت: {state}", size=2.7, fill="#2B2F3A"))
        body.append(text(120, cy + 5.6, f"اولویت: {priority}", size=2.6, fill="#6B7280"))
        body.append(text(7, cy + 5.6, f"نمره: {score10_fa} از ۱۰", size=2.5, fill="#6B7280", anchor="start"))

    svg = chart.replace("</svg>", "".join(body) + "</svg>")
    return svg


def _shape_svg_text(svg: str) -> bytes:
    """Shape Persian text before CairoSVG rasterization, matching Report1's path."""
    root = etree.fromstring(svg.encode("utf-8"))
    for node in root.iter():
        if node.text and _RTL_TEXT.search(node.text):
            node.text = get_display(arabic_reshaper.reshape(node.text))
        if node.tail and _RTL_TEXT.search(node.tail):
            node.tail = get_display(arabic_reshaper.reshape(node.tail))
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def render_r3_visuals(context, output_dir: Path | str, dpi: int = 200) -> dict[str, Path]:
    """Render context-backed R3 SVG charts to DOCX PNG media with shaped RTL text."""
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("CairoSVG is required to render SCL Report3 charts") from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    svgs = {
        "image5.png": build_r3_overview_svg(context),
        "roadmap_surface": build_r3_roadmap_svg(context, "surface"),
        "roadmap_psych": build_r3_roadmap_svg(context, "psych"),
        "roadmap_root": build_r3_roadmap_svg(context, "root"),
    }
    for name, svg in svgs.items():
        filename = f"{name}.png" if not name.endswith(".png") else name
        path = output_dir / filename
        cairosvg.svg2png(bytestring=_shape_svg_text(svg), write_to=str(path), dpi=dpi)
        outputs[name] = path
    return outputs
