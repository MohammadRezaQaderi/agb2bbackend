"""Small SVG primitives copied from the supplied PSSHI chart source."""

FONT = "IRAN"
PALETTE = {
    "navy": "#1F2A44",
    "ink": "#2B2F3A",
}


def esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def svg_doc(width_mm, height_mm, body, defs=""):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width_mm}mm" height="{height_mm}mm" '
        f'viewBox="0 0 {width_mm} {height_mm}" direction="ltr" style="direction:ltr">'
        f"<defs>{defs}</defs>{body}</svg>"
    )


def text(x, y, value, size=4, fill="#000", weight="normal", anchor="end", extra=""):
    weight = "bold" if weight == "bold" else "normal"
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>'
        f"\u202b{esc(value)}\u202c</text>"
    )
