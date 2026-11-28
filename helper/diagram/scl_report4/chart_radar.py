"""Seven-axis study-skills radar from charts_all/psshi/chart_radar.py."""

import math

from .study_meta import SCALES
from .svgkit import PALETTE, svg_doc, text

LEVEL_COLORS = ("#3BB273", "#F2C14E", "#F28C38", "#E04848")
LEVEL_NAMES = ("مطلوب", "نیاز به توجه", "نیاز به تقویت", "نیاز جدی")


def radar(levels, width=170, height=128):
    if set(levels) != {label for _, label, _, _ in SCALES}:
        raise ValueError("PSSHI radar requires all seven authoritative skill levels")
    for label, level in levels.items():
        if isinstance(level, bool) or level not in (1, 2, 3, 4):
            raise ValueError(f"Invalid PSSHI radar level for {label}: {level!r}")

    cx, cy, radius = width / 2, height / 2 + 2, 46
    angles = [-math.pi / 2 + index * 2 * math.pi / len(SCALES) for index in range(len(SCALES))]
    body = ""
    for ring in range(4, 0, -1):
        ring_radius = radius * ring / 4
        points = " ".join(
            f"{cx + ring_radius * math.cos(angle):.2f},{cy + ring_radius * math.sin(angle):.2f}"
            for angle in angles
        )
        fill = "#F4F6FA" if ring % 2 else "#FFFFFF"
        body += f'<polygon points="{points}" fill="{fill}" stroke="#D9DEE7" stroke-width="0.4"/>'

    values = []
    for (key, label, name, color), angle in zip(SCALES, angles):
        body += (
            f'<line x1="{cx}" y1="{cy}" '
            f'x2="{cx + radius * math.cos(angle):.2f}" '
            f'y2="{cy + radius * math.sin(angle):.2f}" '
            'stroke="#D9DEE7" stroke-width="0.4"/>'
        )
        cosine, sine = math.cos(angle), math.sin(angle)
        label_x, label_y = cx + (radius + 3.2) * cosine, cy + (radius + 3.2) * sine
        body += f'<circle cx="{label_x:.2f}" cy="{label_y:.2f}" r="1.3" fill="{color}"/>'
        estimated_width = len(name) * 3.4 * 0.52
        if cosine > 0.3:
            body += text(label_x + 2.5 + estimated_width / 2, label_y + 1.3, name, 3.4, PALETTE["ink"], "bold", "middle")
        elif cosine < -0.3:
            body += text(label_x - 2.5 - estimated_width / 2, label_y + 1.3, name, 3.4, PALETTE["ink"], "bold", "middle")
        else:
            offset = 5.5 if sine > 0 else -2.6
            body += text(label_x, label_y + offset, name, 3.4, PALETTE["ink"], "bold", "middle")

        level = int(levels[label])
        value_radius = radius * (5 - level) / 4
        values.append((cx + value_radius * math.cos(angle), cy + value_radius * math.sin(angle), level))

    points = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in values)
    body += (
        f'<polygon points="{points}" fill="{PALETTE["navy"]}" fill-opacity="0.18" '
        f'stroke="{PALETTE["navy"]}" stroke-width="0.9"/>'
    )
    for x, y, level in values:
        body += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.1" fill="{LEVEL_COLORS[level - 1]}" stroke="#fff" stroke-width="0.6"/>'

    legend_x = width - 2
    for name, color in zip(LEVEL_NAMES, LEVEL_COLORS):
        body += f'<rect x="{legend_x - 3.6}" y="{height - 5.5}" width="3.6" height="3.6" rx="1" fill="{color}"/>'
        body += text(legend_x - 6 - len(name) * 1.5 / 2, height - 2.5, name, 2.9, PALETTE["ink"], anchor="middle")
        legend_x -= 34

    return svg_doc(width, height, body)
