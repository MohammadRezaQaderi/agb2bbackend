import warnings

from helper.diagram import bar, bidirection_two_side, gauge, scatter, tube
from helper.diagram.style import FONT_FAMILY, configure_matplotlib


def test_bundled_persian_font_is_registered():
    assert FONT_FAMILY == "IRAN"
    assert configure_matplotlib() == FONT_FAMILY


def test_diagrams_render_without_missing_glyph_warnings(tmp_path):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bar.create_bar_chart(
            ["تصویری فضایی", "منطقی ریاضی"],
            "توانایی‌ها",
            [60, 80],
            ["#3BABC5", "#E6C90B"],
            0,
            3,
            tmp_path,
            "bar.png",
        )
        gauge.create_gauge_chart(
            108,
            ["", "", "", "", ""],
            ["#42b74a", "#cfdf28", "#ffbb10", "#f76420", "#cf2020"],
            [(0, 51), (52, 89), (90, 119), (120, 147), (148, 200)],
            tmp_path,
            "gauge.png",
        )
        tube.create_tube_chart(32, "#42b74a", tmp_path, "tube.png")
        bidirection_two_side.create_bidirectional_two_side(
            "درون‌گرایی",
            "برون‌گرایی",
            -12,
            12,
            "#3BABC5",
            tmp_path,
            "bidirectional.png",
        )
        scatter.create_scatter_chart(
            [],
            2,
            [0, 1],
            [1, -1],
            [50, 50],
            ["#3BABC5", "#E6C90B"],
            [(0.5, "علوم تجربی")],
            tmp_path,
            "scatter.png",
        )

    missing_glyph = [warning for warning in caught if "Glyph" in str(warning.message)]
    assert missing_glyph == []
    assert all(
        (tmp_path / name).exists() for name in ("bar.png", "gauge.png", "tube.png", "bidirectional.png", "scatter.png")
    )
