import os

import arabic_reshaper
import matplotlib.pyplot as plt
from bidi.algorithm import get_display


def create_scatter_chart(
        branch_lines,
        current_x,
        x_positions,
        all_values,
        all_diameters,
        all_colors,
        branch_labels,
        path: str = "",
        filename: str | bool = False,
):
    """Create and save a scatter plot with vertical separators and Persian labels."""
    path_to_save = os.path.join(path, filename)
    plt.figure(figsize=(16, 16))

    branch_lines.append(current_x - 0.5)
    plt.scatter(x_positions, all_values, s=all_diameters, c=all_colors, alpha=0.5)
    plt.axhline(y=0, color="black", linestyle="--", linewidth=1)

    for line_pos in branch_lines:
        if line_pos > 0:
            plt.axvline(x=line_pos, color="gray", linestyle="--", linewidth=0.5)

    plt.xticks([])
    plt.yticks(fontsize=10, family="B Zar")

    y_min = min(all_values) - 0.2
    y_max = max(all_values) + 0.1
    plt.ylim(y_min, y_max)

    label_y = y_min - 0.05 * (y_max - y_min)
    for pos, label in branch_labels:
        reshaped_label = arabic_reshaper.reshape(label)
        bidi_label = get_display(reshaped_label)
        plt.text(
            pos,
            label_y,
            bidi_label,
            fontsize=12,
            rotation=90,
            family="B Zar",
            ha="center",
            va="top",
            color="blue",
        )

    plt.tight_layout()
    plt.savefig(path_to_save, dpi=300, bbox_inches="tight")
    plt.close()

    return path_to_save
