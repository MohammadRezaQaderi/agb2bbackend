# -*- coding: utf-8 -*-
"""
نیم‌رخ کلی شخصیت نئو — کارنامه ۱ باآزمون (بازطراحی نمودار کلی پنج عامل)
هر ردیف یک طیف دوقطبی است؛ میله از وسط به سمت قطب غالب کشیده می‌شود.
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده (score بین ۰ تا ۱۰۰؛ ۱۰۰ = کاملاً سمت راست / قطب right؛ ۵۰ = متعادل):
    from neo_overall_chart import render_neo_overall_chart
    svg = render_neo_overall_chart([
        {"right": "برون‌گرایی", "left": "درون‌گرایی", "score": 62}, ...])
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
from html import escape

INK, MUTED, LINE = "#1F2340", "#7A7FA3", "#E8EAF3"
NEO_FACTOR_COLORS = {
    "Extraversion": "#2F6FD6",
    "Agreeableness": "#1FA463",
    "Neuroticism": "#F07B2E",
    "Openness": "#E0AE00",
    "Conscientiousness": "#E53935",
}
_FALLBACK_COLORS = tuple(NEO_FACTOR_COLORS.values())


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render_neo_overall_chart(items, width=1600, height=820, font="IRAN"):
    W, H = width, height
    top, bottom, lab = 110, 40, 300
    x0, x1 = lab, W - lab
    mid = (x0 + x1) / 2
    row_h = (H - top - bottom) / len(items)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">', '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for g, name in [(0, "کاملاً"), (25, "نسبتاً"), (50, "متعادل"), (75, "نسبتاً"), (100, "کاملاً")]:
        x = x0 + (x1 - x0) * g / 100
        s.append(f'<line x1="{_n(x)}" x2="{_n(x)}" y1="{top - 20}" y2="{H - bottom}" stroke="{"#C5C9DD" if g == 50 else LINE}" '
                 f'stroke-width="{3 if g == 50 else 2}" {"" if g == 50 else "stroke-dasharray=" + chr(34) + "6 8" + chr(34)}/>')
        s.append(f'<text x="{_n(x)}" y="{top - 40}" text-anchor="middle" font-size="24" fill="{MUTED}">{name}</text>')
    for i, d in enumerate(items):
        c = NEO_FACTOR_COLORS.get(d.get("key"), _FALLBACK_COLORS[i % len(_FALLBACK_COLORS)])
        cy = top + row_h * i + row_h / 2
        sc = max(0, min(100, d["score"]))
        px = x0 + (x1 - x0) * sc / 100
        right_dom = sc >= 50
        scale = min(1.55, max(1.0, row_h / 86))
        bar_h, marker_r = 48 * scale, 34 * scale
        s.append(f'<rect x="{x0}" y="{_n(cy - bar_h / 2)}" width="{x1 - x0}" height="{_n(bar_h)}" rx="{_n(bar_h / 2)}" fill="{c}" opacity="0.07"/>')
        bx, bw = (mid, px - mid) if right_dom else (px, mid - px)
        if bw > 0:
            s.append(f'<rect x="{_n(bx)}" y="{_n(cy - bar_h / 2)}" width="{_n(bw)}" height="{_n(bar_h)}" rx="{_n(bar_h / 2)}" fill="{c}" opacity="0.85"/>')
        s.append(f'<circle cx="{_n(px)}" cy="{_n(cy)}" r="{_n(marker_r)}" fill="#FFFFFF" stroke="{c}" stroke-width="{_n(7 * scale)}"/>')
        s.append(f'<text x="{_n(px)}" y="{_n(cy + 10 * scale)}" text-anchor="middle" font-size="{_n(26 * scale)}" font-weight="bold" fill="{c}">{fa(round(sc))}</text>')
        label_size = 32 * scale
        s.append(f'<text x="{W - 30}" y="{_n(cy + 11 * scale)}" text-anchor="end" font-size="{_n(label_size)}" {"font-weight=" + chr(34) + "bold" + chr(34) + " fill=" + chr(34) + c + chr(34) if right_dom else "fill=" + chr(34) + MUTED + chr(34)}>{escape(d["right"])}</text>')
        s.append(f'<text x="30" y="{_n(cy + 11 * scale)}" text-anchor="start" font-size="{_n(label_size)}" {"font-weight=" + chr(34) + "bold" + chr(34) + " fill=" + chr(34) + c + chr(34) if not right_dom else "fill=" + chr(34) + MUTED + chr(34)}>{escape(d["left"])}</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = [{"right": r, "left": l, "score": v} for r, l, v in [
    ("برون‌گرایی", "درون‌گرایی", 62), ("سازشگری", "خودمحوری", 70), ("روان‌رنجوری", "ثبات هیجانی", 38),
    ("گشودگی به تجربه", "محافظه‌کاری", 75), ("مسئولیت‌پذیری", "تنوع‌طلبی", 55)]]
SAMPLES = [("نیم‌رخ کلی شخصیت نئو (کارنامه ۱)", lambda: render_neo_overall_chart(SAMPLE))]

if __name__ == "__main__":
    with open("neo_overall_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_neo_overall_chart(SAMPLE))
    print("neo_overall_chart.svg ساخته شد")
