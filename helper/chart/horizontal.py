import os

import matplotlib.pyplot as plt


def create_horizontal_chart(
        categories,
        values,
        colors,
        bar_height: float = 0.25,
        path: str = "",
        filename: str | bool = False,
):
    """Create and save a minimal horizontal bar chart."""
    path_to_save = os.path.join(path, filename)

    categories.reverse()
    values.reverse()
    colors.reverse()

    plt.barh(categories, values, color=colors, height=bar_height)
    plt.xticks([])
    plt.yticks([])

    ax = plt.gca()
    ax.invert_xaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    if path_to_save:
        plt.savefig(path_to_save)
    plt.close()

    return path_to_save
