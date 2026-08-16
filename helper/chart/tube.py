import os

import matplotlib
import matplotlib.patches as patches
import matplotlib.pyplot as plt

font = {"family": "B Nazanin"}
matplotlib.rc("font", **font)


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


def create_tube_chart(charge_level, color, path, filename, dpi: int = 100):
    """Create and save a vertical tube/thermometer style chart."""
    fig_size_width = 88 / dpi
    fig_size_height = 257 / dpi
    charge_level = charge_level * 2

    fig, ax = plt.subplots(figsize=(fig_size_width, fig_size_height), dpi=dpi)
    path_to_save = os.path.join(path, filename)
    ax.axis("off")

    background_border = patches.Rectangle(
        (0.5, 0.5),
        0.9,
        9.9,
        linewidth=1,
        edgecolor="black",
        facecolor="none",
    )
    ax.add_patch(background_border)

    for i in range(0, 101, 10):
        ax.text(
            0.05,
            i / 100 * 9.9,
            num_to_persian(i),
            family="B Nazanin",
            ha="right",
            va="center",
            color="black",
            fontsize=5,
        )

    background = patches.FancyBboxPatch(
        (0.1, 0.1),
        0.8,
        9.9,
        boxstyle="round,pad=-0.004,rounding_size=0.2",
        edgecolor="none",
        facecolor="#d9d9d9",
    )
    ax.add_patch(background)

    charge_height = charge_level / 100 * 9.9
    charge = patches.FancyBboxPatch(
        (0.1, 0.1),
        0.8,
        charge_height,
        boxstyle="round,pad=-0.004,rounding_size=0.5",
        edgecolor="none",
        facecolor=color,
    )
    ax.add_patch(charge)

    ax.set_aspect("equal")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 10)

    percentage_text = num_to_persian(int(charge_level))
    ax.text(
        0.5,
        -0.05,
        percentage_text,
        family="B Nazanin",
        ha="center",
        va="center",
        color="black",
        fontsize=8,
        transform=ax.transAxes,
    )

    if path_to_save:
        plt.savefig(path_to_save, dpi=dpi)
    plt.close(fig)
    return path_to_save
