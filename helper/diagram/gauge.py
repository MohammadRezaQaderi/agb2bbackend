import math
import os

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Rectangle, Wedge

from helper.diagram.style import configure_matplotlib, rtl, to_persian_digits

FONT_FAMILY = configure_matplotlib()


def degree_range(n):
    """Return start/end degree ranges and midpoints for n segments over 180 degrees."""
    start = np.linspace(0, 180, n + 1, endpoint=True)[0:-1]
    end = np.linspace(0, 180, n + 1, endpoint=True)[1::]
    mid_points = start + (end - start) / 2.0
    return np.c_[start, end], mid_points


def rot_text(ang):
    """Compute label rotation for a given angle."""
    rotation = np.degrees(np.radians(ang) * np.pi / np.pi - np.radians(90))
    return rotation


def get_arrow_pos(value, ranges):
    """Compute the arrow angle on the gauge based on the value and ranges."""
    n = len(ranges)
    for i, r in enumerate(ranges):
        if r[0] <= value <= r[1]:
            rel_pos = 0 if r[1] == r[0] else (value - r[0]) / (r[1] - r[0])
            start_angle = i * (180 / n)
            return 180 - (start_angle + rel_pos * (180 / n))
    return 0


def num_to_char(num, formatter="%1.1f%%"):
    """Convert a number to a formatted string with Persian digits and percent."""
    return to_persian_digits(formatter % num)


def num_to_persian(num):
    """Convert an integer to a string with Persian digits."""
    return to_persian_digits(num)


def create_gauge_chart(
    value,
    labels,
    colors,
    ranges,
    path: str = "",
    filename: str | bool = False,
    figsize=(4.2, 2.5),
    dpi: int = 200,
    ring_radius: float = 0.43,
    ring_width: float = 0.13,
    label_size: int = 11,
    value_size: int = 24,
    font_weight: str = "bold",
    arrow_scale: float = 0.28,
    exact_canvas: bool = False,
):
    """Create and save a semi-circular gauge chart."""
    min_value = ranges[0][0]
    max_value = ranges[-1][1]
    value = max(min_value, min(max_value, math.ceil(value)))
    arrow_pos = get_arrow_pos(value, ranges)

    n = len(labels)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("white")
    ang_range, mid_points = degree_range(n)
    labels = [rtl(label) for label in labels[::-1]]

    patches = []
    for ang, c in zip(ang_range, colors):
        patches.append(Wedge((0.0, 0.0), ring_radius, *ang, facecolor="white", lw=0))
        patches.append(
            Wedge(
                (0.0, 0.0),
                ring_radius,
                *ang,
                width=ring_width,
                facecolor=c,
                lw=0,
                edgecolor="white",
                alpha=0.9,
            )
        )
    for p in patches:
        ax.add_patch(p)

    for mid, lab in zip(mid_points, labels):
        ax.text(
            (ring_radius - ring_width / 2) * np.cos(np.radians(mid)),
            (ring_radius - ring_width / 2) * np.sin(np.radians(mid)),
            lab,
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=label_size,
            fontweight=font_weight,
            family=FONT_FAMILY,
            rotation=rot_text(mid),
        )

    r = Rectangle((-ring_radius, -0.11), ring_radius * 2, 0.12, facecolor="white", lw=0)
    ax.add_patch(r)

    persian_text = num_to_persian(int(value))
    ax.text(
        0,
        -0.10,
        persian_text,
        family=FONT_FAMILY,
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=value_size,
        fontweight=font_weight,
    )

    arrow_style = {
        "width": 0.018 if arrow_scale > 0.3 else 0.012,
        "head_width": 0.075 if arrow_scale > 0.3 else 0.05,
        "head_length": 0.11 if arrow_scale > 0.3 else 0.09,
        "overhang": 0.25,
        "facecolor": "#17212B",
        "edgecolor": "#17212B",
        "length_includes_head": True,
        "zorder": 10,
    }
    ax.arrow(
        0,
        0,
        arrow_scale * np.cos(np.radians(arrow_pos)),
        arrow_scale * np.sin(np.radians(arrow_pos)),
        **arrow_style,
    )
    ax.add_patch(Circle((0, 0), radius=0.04 if arrow_scale > 0.3 else 0.035, facecolor="#17212B", zorder=11))
    ax.add_patch(Circle((0, 0), radius=0.014, facecolor="white", zorder=12))

    ax.set_frame_on(False)
    ax.axes.set_xticks([])
    ax.axes.set_yticks([])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-ring_radius - 0.08, ring_radius + 0.08)
    ax.set_ylim(-0.16, ring_radius + 0.1)
    if not exact_canvas:
        plt.tight_layout()

    path_to_save = os.path.join(path, filename)
    if path_to_save:
        if exact_canvas:
            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
            with plt.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0.1}):
                fig.savefig(path_to_save, dpi=dpi)
        else:
            fig.savefig(path_to_save, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path_to_save
