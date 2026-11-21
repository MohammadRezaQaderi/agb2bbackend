from pathlib import Path

import arabic_reshaper
import matplotlib
from bidi.algorithm import get_display
from matplotlib import font_manager

FONT_PATHS = [
    Path(__file__).with_name("IRAN.ttf"),
    Path(__file__).with_name("IRAN.woff"),
]
FONT_FAMILY = "IRAN"


def configure_matplotlib() -> str:
    """Register the bundled Persian font and return the active family name."""
    font_path = next((path for path in FONT_PATHS if path.exists()), None)
    if font_path is not None:
        try:
            font_manager.fontManager.addfont(str(font_path))
            matplotlib.rcParams["font.family"] = FONT_FAMILY
        except RuntimeError:
            matplotlib.rcParams["font.family"] = "DejaVu Sans"
    else:
        matplotlib.rcParams["font.family"] = "DejaVu Sans"

    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["savefig.bbox"] = "tight"
    matplotlib.rcParams["savefig.pad_inches"] = 0.08
    return matplotlib.rcParams["font.family"][0]


def rtl(text) -> str:
    """Render Persian/Arabic labels correctly in matplotlib."""
    return get_display(arabic_reshaper.reshape(str(text)))


def to_persian_digits(value) -> str:
    mapping = str.maketrans("0123456789.%", "۰۱۲۳۴۵۶۷۸۹.%")
    return str(value).translate(mapping)
