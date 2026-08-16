import math
import os

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Rectangle, Wedge

font = {"family": "B Nazanin"}
matplotlib.rc("font", **font)


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
            rel_pos = (value - r[0]) / (r[1] - r[0])
            start_angle = i * (180 / n)
            return 180 - (start_angle + rel_pos * (180 / n))
    return 0


def num_to_char(num, formatter="%1.1f%%"):
    """Convert a number to a formatted string with Persian digits and percent."""
    num_as_string = formatter % num
    mapping = dict(zip("0123456789.%", "۰۱۲۳۴۵۶۷۸۹.%"))
    return "".join(mapping[digit] for digit in num_as_string)


def num_to_persian(num):
    """Convert an integer to a string with Persian digits."""
    persian_digits = {
        "0": "۰",
        "1": "۱",
        "2": "۲",
        "3": "۳",
        "4": "۴",
        "5": "۵",
        "6": "۶",
        "7": "۷",
        "8": "۸",
        "9": "۹",
    }
    num_str = str(num)
    persian_num_str = "".join(persian_digits[digit] for digit in num_str)
    return persian_num_str


def create_gauge_chart(value, labels, colors, ranges, path: str = "", filename: str | bool = False):
    """Create and save a semi-circular gauge chart."""
    value = math.ceil(value)
    arrow_pos = get_arrow_pos(value, ranges)

    n = len(labels)
    fig, ax = plt.subplots()
    ang_range, mid_points = degree_range(n)
    labels = [label for label in labels[::-1]]

    patches = []
    for ang, c in zip(ang_range, colors):
        patches.append(Wedge((0.0, 0.0), 0.4, *ang, facecolor="w", lw=2))
        patches.append(
            Wedge(
                (0.0, 0.0),
                0.4,
                *ang,
                width=0.10,
                facecolor=c,
                lw=2,
                alpha=0.5,
            )
        )
    for p in patches:
        ax.add_patch(p)

    for mid, lab in zip(mid_points, labels):
        ax.text(
            0.35 * np.cos(np.radians(mid)),
            0.35 * np.sin(np.radians(mid)),
            lab,
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=14,
            fontweight="bold",
            rotation=rot_text(mid),
        )

    r = Rectangle((-0.4, -0.1), 0.8, 0.1, facecolor="w", lw=2)
    ax.add_patch(r)

    persian_text = num_to_persian(int(value))
    ax.text(
        0,
        -0.10,
        persian_text,
        family="B Nazanin",
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=22,
        fontweight="bold",
    )

    arrow_style = {
        "width": 0.01,
        "head_width": 0.04,
        "head_length": 0.1,
        "overhang": 0.3,
        "facecolor": "black",
        "edgecolor": "black",
    }
    ax.arrow(
        0,
        0,
        0.225 * np.cos(np.radians(arrow_pos)),
        0.225 * np.sin(np.radians(arrow_pos)),
        **arrow_style,
    )
    ax.add_patch(Circle((0, 0), radius=0.02, facecolor="k"))
    ax.add_patch(Circle((0, 0), radius=0.01, facecolor="w", zorder=11))

    ax.set_frame_on(False)
    ax.axes.set_xticks([])
    ax.axes.set_yticks([])
    ax.axis("equal")
    plt.tight_layout()

    path_to_save = os.path.join(path, filename)
    if path_to_save:
        fig.savefig(path_to_save, dpi=200)
    plt.close(fig)
    return path_to_save
