from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable, Mapping

import arabic_reshaper
from bidi.algorithm import get_display
from lxml import etree

from .clifton_chart import render_clifton_chart
from .commitment_chart import render_commitment_chart
from .gardner_bar_chart import render_gardner_bar_chart
from .gauge_chart import IQ_PRESET, render_gauge_chart
from .glance_chart import render_glance_chart
from .holland_chart import render_holland_chart
from .neo_overall_chart import render_neo_overall_chart
from .test_tube_chart import GARDNER_COLORS, render_test_tube_chart


GARDNER_SCALES = (
    ("Visual_spatial", "تصویری-فضایی"),
    ("Linguistic_verbal", "کلامی-زبانی"),
    ("Logical_mathematical", "منطقی-ریاضی"),
    ("Body_kinesthetic", "جسمی-حرکتی"),
    ("Musical", "موسیقایی"),
    ("Interpersonal", "بین فردی"),
    ("Intrapersonal", "درون فردی"),
    ("Naturalistic", "طبیعت گرا"),
)

NEO_SCALES = (
    ("Extraversion", "برون گرایی", "درون گرایی"),
    ("Agreeableness", "سازشگری", "خودمحوری"),
    ("Neuroticism", "روان رنجوری", "ثبات هیجانی"),
    ("Openness", "گشودگی به تجربه", "محافظه کاری"),
    ("Conscientiousness", "مسئولیت پذیری", "تنوع طلبی"),
)

HOLLAND_SCALES = (
    ("Realistic", "و", "واقع گرایی"),
    ("Investigative", "ج", "جستجوگری"),
    ("Artistic", "هـ", "هنری"),
    ("Social", "الف", "اجتماعی"),
    ("Enterprising", "م", "متهور"),
    ("Conventional", "ق", "قراردادی"),
)

CLIFTON_DOMAINS = (
    (
        "تفکر استراتژیک",
        {
            "Analytical": 44,
            "Context": 16,
            "Intellection": 44,
            "Ideation": 28,
            "Input": 20,
            "Strategic": 16,
            "Learner": 32,
            "Futuristic": 32,
        },
    ),
    (
        "ساخت روابط",
        {
            "Adaptability": 32,
            "Connectedness": 32,
            "Developer": 40,
            "Empathy": 24,
            "Harmony": 20,
            "Includer": 28,
            "Individualization": 24,
            "Positivity": 48,
            "Relator": 32,
        },
    ),
    (
        "نفوذ و تاثیرگذاری",
        {
            "Activator": 28,
            "Command": 36,
            "Communication": 36,
            "Competition": 36,
            "Significance": 48,
            "Maximizer": 28,
            "Woo": 36,
            "Self_assurance": 52,
        },
    ),
    (
        "اجرایی",
        {
            "Achiever": 24,
            "Consistency": 32,
            "Arranger": 52,
            "Responsibility": 44,
            "Belief": 44,
            "Focus": 48,
            "Deliberative": 32,
            "Discipline": 56,
            "Restorative": 24,
        },
    ),
)

MEDIA_TARGETS = (
    "image13.png",
    "image16.png",
    "image18.png",
    "image23.png",
    "image26.png",
    "image29.png",
    "image32.png",
    "image35.png",
    "image38.png",
    "image41.png",
    "image44.png",
    "image53.png",
    "image55.png",
    "image57.png",
    "image59.png",
    "image61.png",
    "image69.png",
    "image71.png",
    "image81.png",
)

_RTL_TEXT = re.compile(r"[\u0600-\u06ff]")


@dataclass(frozen=True)
class AGReport1ChartData:
    iq: dict[str, Any]
    gardner: tuple[dict[str, Any], ...]
    neo: tuple[dict[str, Any], ...]
    holland: tuple[dict[str, Any], ...]
    clifton: tuple[dict[str, Any], ...]
    commitment: dict[str, Any]


def _number(labels: Mapping[str, Any], key: str) -> float:
    if key not in labels:
        raise ValueError(f"AG Report 1 is missing required label: {key}")
    value = labels[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"AG Report 1 label {key} must be numeric")
    return float(value)


def _percent(value: float, maximum: float, key: str) -> float:
    if not 0 <= value <= maximum:
        raise ValueError(f"AG Report 1 label {key} must be between 0 and {maximum:g}; got {value:g}")
    return round(value * 100 / maximum, 2)


def _commitment_label(score: float) -> str:
    return ("خیلی کم", "کم", "متوسط", "زیاد", "خیلی زیاد")[min(4, int(score // 20))]


def _clifton_score(labels: Mapping[str, Any], scales: Mapping[str, float]) -> float:
    percentages = [_percent(_number(labels, key), maximum, key) for key, maximum in scales.items()]
    return round(sum(percentages) / len(percentages), 2)


def build_chart_data(labels: Mapping[str, Any]) -> AGReport1ChartData:
    """Validate raw AG labels and normalize every Report 1 chart to its display scale."""
    iq_score = _number(labels, "IQ_Number")
    if not 0 <= iq_score <= 200:
        raise ValueError(f"AG Report 1 label IQ_Number must be between 0 and 200; got {iq_score:g}")

    gardner = tuple(
        {"key": key, "name": name, "score": _percent(_number(labels, key), 50, key)}
        for key, name in GARDNER_SCALES
    )
    neo = tuple(
        {
            "key": key,
            "right": right,
            "left": left,
            "score": _percent(_number(labels, key), 48, key),
        }
        for key, right, left in NEO_SCALES
    )
    holland = tuple(
        {
            "key": key,
            "code": code,
            "name": name,
            "score": _percent(_number(labels, key), 50, key),
        }
        for key, code, name in HOLLAND_SCALES
    )
    clifton = tuple(
        {"name": name, "score": _clifton_score(labels, scales)}
        for name, scales in CLIFTON_DOMAINS
    )
    commitment_score = _percent(_number(labels, "SES"), 224, "SES")
    commitment = {"score": commitment_score, "label": _commitment_label(commitment_score)}
    iq_label = next(
        (segment[2] for segment in IQ_PRESET["segments"] if segment[0] <= iq_score <= segment[1]),
        IQ_PRESET["segments"][-1][2],
    )
    return AGReport1ChartData(
        iq={"score": iq_score, "label": iq_label, "min": 40, "max": 170},
        gardner=gardner,
        neo=neo,
        holland=holland,
        clifton=clifton,
        commitment=commitment,
    )


def _renderers(data: AGReport1ChartData) -> dict[str, Callable[[], str]]:
    glance = {
        "iq": data.iq,
        "gardner": data.gardner,
        "neo": data.neo,
        "holland": sorted(data.holland, key=lambda item: item["score"], reverse=True)[:3],
        "clifton": data.clifton,
    }
    renderers: dict[str, Callable[[], str]] = {
        "image13.png": lambda: render_glance_chart(glance, width=1600, height=1760, font="Vazirmatn"),
        "image16.png": lambda: render_gauge_chart(
            data.iq["score"], **IQ_PRESET, width=1500, height=960, font="Vazirmatn"
        ),
        "image18.png": lambda: render_gardner_bar_chart(
            data.gardner, width=2400, height=1350, font="Vazirmatn"
        ),
        "image69.png": lambda: render_holland_chart(
            data.holland, width=1600, height=900, font="Vazirmatn"
        ),
        "image71.png": lambda: render_clifton_chart(
            data.clifton, width=1600, height=820, font="Vazirmatn"
        ),
        "image81.png": lambda: render_commitment_chart(
            data.commitment, width=1600, height=640, font="Vazirmatn"
        ),
    }
    for target, item, color in zip(
        ("image23.png", "image26.png", "image29.png", "image32.png", "image35.png", "image38.png", "image41.png", "image44.png"),
        data.gardner,
        GARDNER_COLORS,
    ):
        renderers[target] = lambda item=item, color=color: render_test_tube_chart(
            item["score"], color=color, width=360, height=1050, font="Vazirmatn"
        )
    for target, item in zip(
        ("image53.png", "image55.png", "image57.png", "image59.png", "image61.png"),
        data.neo,
    ):
        renderers[target] = lambda item=item: render_neo_overall_chart(
            [item], width=3000, height=225, font="Vazirmatn"
        )
    return renderers


def _shape_svg_text(svg: str) -> bytes:
    """Shape Persian SVG text for Cairo/Pango environments without RTL layout."""
    root = etree.fromstring(svg.encode("utf-8"))
    for node in root.iter():
        if node.text and _RTL_TEXT.search(node.text):
            node.text = get_display(arabic_reshaper.reshape(node.text))
        if node.tail and _RTL_TEXT.search(node.tail):
            node.tail = get_display(arabic_reshaper.reshape(node.tail))
    return etree.tostring(root, encoding="utf-8", xml_declaration=True)


def render_report_media(data: AGReport1ChartData, output_directory: Path | str) -> dict[str, Path]:
    """Render exact DOCX media targets into an isolated directory."""
    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover - deployment configuration guard
        raise RuntimeError("CairoSVG is required to render AG Report 1 charts") from exc

    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    rendered: dict[str, Path] = {}
    renderers = _renderers(data)
    if set(renderers) != set(MEDIA_TARGETS):
        missing = sorted(set(MEDIA_TARGETS) - set(renderers))
        raise RuntimeError(f"AG Report 1 renderer map is incomplete: {missing}")
    for target in MEDIA_TARGETS:
        destination = output / target
        cairosvg.svg2png(bytestring=_shape_svg_text(renderers[target]()), write_to=str(destination))
        if not destination.is_file() or destination.stat().st_size == 0:
            raise RuntimeError(f"AG Report 1 rendered an empty chart: {target}")
        rendered[target] = destination
    return rendered
