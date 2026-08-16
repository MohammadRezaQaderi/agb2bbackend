import os

import matplotlib
import matplotlib.pyplot as plt

font = {"family": "B Nazanin"}
matplotlib.rc("font", **font)


def create_bi_chart(negative_values, positive_values, path, filename):
    """Create a bidirectional horizontal bar chart for two sets of values."""
    fig, ax_left = plt.subplots(figsize=(10, 5))

    categories_left = [
        "ﯽﯾﺍﺮﮔﻥﻭﺮﺑ",
        "ﺮﮕﺷﺯﺎﺳ",
        "ﯼﺭﻮﺠﻧﺭ ﻥﺍﻭﺭ",
        "ﻪﺑﺮﺠﺗ ﻪﺑ ﻩﺩﻮﺸﮔ",
        "ﯼﺮﯾﺬﭘ ﺖﯿﻟﻮﺌﺴﻣ",
    ]
    categories_right = [
        "ﯽﯾﺍﺮﮔﻥﻭﺭﺩ",
        "ﯼﺭﻮﺤﻣﺩﻮﺧ",
        "ﯽﻧﺎﺠﯿﻫﺭﺎﮐﻧﺍ",
        "ﺭﺎﮐ ﻪﻈﻓﺎﺤﻣ",
        "ﺐﻠﻃ ﻉﻮﻨﺗ",
    ]

    ax_left.barh(categories_left, negative_values, color="salmon", label="Negative")
    ax_left.set_yticks(range(len(categories_left)))
    ax_left.set_yticklabels(categories_left)
    ax_left.invert_xaxis()

    ax_right = ax_left.twinx()
    ax_right.barh(
        categories_right,
        positive_values,
        color="skyblue",
        label="Positive",
        left=0,
    )
    ax_right.set_yticks(range(len(categories_right)))
    ax_right.set_yticklabels(categories_right)

    tick_values = [-24, -20, -16, -12, -8, -4, 0, 4, 8, 12, 16, 20, 24]
    ax_left.set_xticks(tick_values)
    ax_right.set_xticks(tick_values)

    ax_left.axvline(x=0, color="gray", linewidth=0.5)
    ax_left.grid(axis="x")

    path_to_save = os.path.join(path, filename)
    plt.savefig(path_to_save)
    plt.close(fig)
    return path_to_save
