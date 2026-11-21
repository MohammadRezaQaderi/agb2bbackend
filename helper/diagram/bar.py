import os

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from helper.diagram.style import configure_matplotlib, rtl, to_persian_digits

FONT_FAMILY = configure_matplotlib()


def create_bar_chart(
    categories,
    title,
    values,
    colors,
    rotation,
    size,
    path,
    filename,
    y_limit: int = 100,
    dpi: int = 180,
    bar_width: float = 0.68,
    show_grid: bool = True,
    show_values: bool = True,
    facecolor: str = "#FAFBFC",
    title_size: int = 15,
    tick_size: int = 10,
    tick_weight: str = "normal",
    tick_ha: str = "right",
    tick_va: str = "top",
    bottom_margin: float | None = None,
    top_margin: float | None = None,
    left_margin: float | None = None,
    right_margin: float | None = None,
    exact_canvas: bool = False,
):
    """Create and save a vertical bar chart with Persian labels."""
    path_to_save = os.path.join(path, filename)

    fig, ax = plt.subplots(figsize=(10, size), dpi=dpi)
    fig.patch.set_facecolor("white")
    ax.set_facecolor(facecolor)

    reshaped_categories = [rtl(category) for category in categories]
    bars = ax.bar(
        reshaped_categories,
        values,
        color=colors,
        width=bar_width,
        edgecolor="none" if not show_grid else "white",
        linewidth=0 if not show_grid else 1.4,
        zorder=3,
    )

    if title:
        ax.set_title(rtl(title), family=FONT_FAMILY, fontsize=title_size, fontweight="bold", pad=10)

    ax.set_ylim(0, y_limit)
    ax.set_axisbelow(True)
    if show_grid:
        ax.yaxis.grid(True, color="#D8DEE8", linewidth=0.8)
    else:
        ax.yaxis.grid(False)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda tick, _: to_persian_digits(int(tick))))
    ax.xaxis.grid(False)
    ax.tick_params(axis="both", colors="#111111", labelsize=tick_size)
    ax.set_xticks(range(len(reshaped_categories)))
    ax.set_xticklabels(
        reshaped_categories,
        rotation=rotation,
        ha=tick_ha,
        va=tick_va,
        family=FONT_FAMILY,
        fontweight=tick_weight,
    )
    for label in ax.get_yticklabels():
        label.set_fontfamily(FONT_FAMILY)
        label.set_fontweight(tick_weight)

    if show_grid:
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color("#C7D0DD")
    else:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("#111111")
            spine.set_linewidth(0.8)

    if show_values:
        for rect, value in zip(bars, values):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                min(value + 2, y_limit - 1),
                to_persian_digits(int(round(value))),
                ha="center",
                va="bottom",
                fontsize=8,
                color="#263238",
                family=FONT_FAMILY,
            )

    margins = {
        "bottom": bottom_margin,
        "top": top_margin,
        "left": left_margin,
        "right": right_margin,
    }
    if any(value is not None for value in margins.values()):
        fig.subplots_adjust(**{key: value for key, value in margins.items() if value is not None})

    if path_to_save:
        if exact_canvas:
            with plt.rc_context({"savefig.bbox": None, "savefig.pad_inches": 0.1}):
                fig.savefig(path_to_save, dpi=dpi)
        else:
            fig.savefig(path_to_save, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path_to_save
