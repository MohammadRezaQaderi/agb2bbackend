import os

import arabic_reshaper
import matplotlib
import matplotlib.pyplot as plt
from bidi.algorithm import get_display

font = {"family": "B Nazanin"}
matplotlib.rc("font", **font)


def create_bidirectional_two_side(
        first_label,
        second_label,
        first_value,
        second_value,
        color,
        path,
        filename,
        dpi: int = 100,
):
    """Create a two-sided horizontal bar chart comparing two labeled values."""
    fig_size_width = 1000 / dpi
    fig_size_height = 50 / dpi

    reshaped_text = arabic_reshaper.reshape(first_label)
    first_label = get_display(reshaped_text)
    reshaped_text = arabic_reshaper.reshape(second_label)
    second_label = get_display(reshaped_text)

    path_to_save = os.path.join(path, filename)

    fig, ax = plt.subplots(figsize=(fig_size_width, fig_size_height), dpi=200)
    bars = ax.barh(
        [0, 0],
        [first_value, second_value],
        color=[color, color],
        edgecolor="white",
    )

    max_val = 24
    ax.set_xlim(-24, 24)
    ax.set_xticks([-24, -20, -16, -12, -8, -4, 0, 4, 8, 12, 16, 20, 24])

    for bar in bars:
        width = bar.get_width()
        y_center = bar.get_y() + bar.get_height() / 2
        if width < 0:
            ax.text(
                width - 50,
                y_center,
                f"{abs(width)}K",
                family="B Nazanin",
                va="center",
                ha="right",
                color="white",
            )
            ax.text(
                -max_val,
                y_center,
                first_label,
                family="B Nazanin",
                va="center",
                ha="right",
                color="black",
            )
        else:
            ax.text(
                width + 50,
                y_center,
                f"{width}K",
                family="B Nazanin",
                va="center",
                ha="left",
                color="white",
            )
            ax.text(
                max_val,
                y_center,
                second_label,
                family="B Nazanin",
                va="center",
                ha="left",
                color="black",
            )

    ax.axhline(y=0, color="gray", linestyle="-", linewidth=1)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_ticks_position("none")
    ax.get_yaxis().set_visible(False)
    ax.get_xaxis().set_visible(True)
    fig.patch.set_facecolor("white")

    if path_to_save:
        plt.savefig(path_to_save)
    plt.close(fig)
    return path_to_save
