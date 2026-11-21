import os

import matplotlib.patches as patches
import matplotlib.pyplot as plt

from helper.diagram.style import configure_matplotlib, to_persian_digits

FONT_FAMILY = configure_matplotlib()


def num_to_persian(num):
    """Convert an integer to a string with Persian digits."""
    return to_persian_digits(num)


def create_tube_chart(
    charge_level,
    color,
    path,
    filename,
    dpi: int = 100,
    width_px: int = 88,
    height_px: int = 257,
    sample_style: bool = False,
    show_background: bool = True,
    labels_side: str = "right",
):
    """Create and save a vertical tube/thermometer style chart."""
    fig_size_width = width_px / dpi
    fig_size_height = height_px / dpi
    charge_level = max(0, min(100, charge_level * 2))

    fig, ax = plt.subplots(figsize=(fig_size_width, fig_size_height), dpi=dpi)
    fig.patch.set_facecolor("#fbf6b8" if sample_style and show_background else "white")
    path_to_save = os.path.join(path, filename)
    ax.axis("off")

    label_on_left = labels_side == "left"
    tube_x = 0.42 if label_on_left else (0.18 if sample_style else 0.28)
    tube_width = 0.42 if sample_style else 0.54
    tube_bottom = 0.65 if sample_style else 0.35
    tube_height = 8.25 if sample_style else 9.35
    label_x = tube_x - 0.12 if label_on_left else (0.93 if sample_style else tube_x - 0.11)

    for i in range(0, 101, 10):
        y = tube_bottom + i / 100 * tube_height
        if sample_style:
            if label_on_left:
                ax.plot([tube_x - 0.08, tube_x - 0.02], [y, y], color="#e5d992", linewidth=0.7)
            else:
                ax.plot(
                    [tube_x + tube_width + 0.02, tube_x + tube_width + 0.08], [y, y], color="#e5d992", linewidth=0.7
                )
        else:
            ax.plot([tube_x - 0.08, tube_x - 0.02], [y, y], color="#9AA6B2", linewidth=0.6)
        ax.text(
            label_x,
            y,
            num_to_persian(i),
            family=FONT_FAMILY,
            ha="right",
            va="center",
            color="#b7aa66" if sample_style else "#36454F",
            fontsize=5.5 if not sample_style else 5.2,
        )

    shadow = patches.FancyBboxPatch(
        (tube_x + 0.025, tube_bottom - 0.015),
        tube_width,
        tube_height,
        boxstyle="round,pad=0.006,rounding_size=0.28",
        edgecolor="none",
        facecolor="#000000",
        alpha=0.08 if sample_style else 0.12,
        zorder=1,
    )
    ax.add_patch(shadow)

    background = patches.FancyBboxPatch(
        (tube_x, tube_bottom),
        tube_width,
        tube_height,
        boxstyle="round,pad=0.006,rounding_size=0.28",
        edgecolor="#d8ecd8" if sample_style else "#C3CBD5",
        linewidth=3.0 if sample_style else 0.8,
        facecolor="#ffffff" if not show_background else ("#f9fad6" if sample_style else "#EDF1F5"),
        alpha=0.72 if sample_style else 1,
        zorder=2,
    )
    ax.add_patch(background)

    charge_height = charge_level / 100 * tube_height
    charge = patches.FancyBboxPatch(
        (tube_x, tube_bottom),
        tube_width,
        charge_height,
        boxstyle="round,pad=0.006,rounding_size=0.28",
        edgecolor="none",
        facecolor=color,
        alpha=0.92 if sample_style else 0.95,
        zorder=3,
    )
    ax.add_patch(charge)

    highlight = patches.FancyBboxPatch(
        (tube_x + 0.08, tube_bottom + 0.2),
        tube_width * 0.18,
        tube_height - 0.5,
        boxstyle="round,pad=0.002,rounding_size=0.12",
        edgecolor="none",
        facecolor="white",
        alpha=0.22 if sample_style else 0.32,
        zorder=4,
    )
    ax.add_patch(highlight)

    if sample_style:
        top = patches.Ellipse(
            (tube_x + tube_width / 2, tube_bottom + tube_height + 0.12),
            tube_width * 1.25,
            0.38,
            edgecolor="#d8ecd8",
            facecolor="#ffffff" if not show_background else "#fbf6b8",
            linewidth=3,
            alpha=0.8,
            zorder=5,
        )
        ax.add_patch(top)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 10)

    percentage_text = num_to_persian(int(charge_level))
    ax.text(
        0.5,
        0.02,
        percentage_text,
        family=FONT_FAMILY,
        ha="center",
        va="bottom",
        color="#b7aa66" if sample_style else "#17212B",
        fontsize=7.5 if sample_style else 8.5,
        fontweight="bold",
        transform=ax.transAxes,
    )

    if path_to_save:
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        with plt.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0}):
            fig.savefig(path_to_save, dpi=dpi)
    plt.close(fig)
    return path_to_save
