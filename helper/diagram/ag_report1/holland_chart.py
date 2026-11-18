# -*- coding: utf-8 -*-
"""
نمودار رغبت‌های شغلی هالند (RIASEC) — کارنامه ۱ باآزمون
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده:
    from holland_chart import render_holland_chart
    svg = render_holland_chart([
        {"code": "و",   "name": "واقع‌گرایی", "score": 42},   # score: عدد ۰ تا ۱۰۰
        {"code": "ج",   "name": "جستجوگری",  "score": 78},
        {"code": "هـ",  "name": "هنری",       "score": 55},
        {"code": "الف", "name": "اجتماعی",    "score": 90},
        {"code": "م",   "name": "متهور",      "score": 30},
        {"code": "ق",   "name": "قراردادی",   "score": 64},
    ])

سطح‌ها: ۰–۲۵ پایین، ۲۵–۵۰ نسبتاً پایین، ۵۰–۷۵ نسبتاً بالا، ۷۵–۱۰۰ بالا
(اگر مرزهای سیستم شما فرق دارد، LEVELS را تغییر دهید.)
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
from html import escape

COLORS = ["#E8833A", "#2D9CDB", "#E84393", "#27AE60", "#F2B705", "#7A4FD0"]
LEVELS = [
    (0, 25, "پایین", "#F4F5FB"),
    (25, 50, "نسبتاً پایین", "#ECEEF8"),
    (50, 75, "نسبتاً بالا", "#E3E6F5"),
    (75, 100, "بالا", "#D9DDF2"),
]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render_holland_chart(items, width=1600, height=900, font="IRAN"):
    W, H = width, height
    top, bottom, label_w, left = 120, 40, 380, 70
    right = W - label_w
    plot_w = right - left
    row_h = (H - top - bottom) / len(items)
    x = lambda v: right - plot_w * max(0, min(100, v)) / 100  # راست‌به‌چپ
    max_score = max(d["score"] for d in items)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for lo, hi, label, fill in LEVELS:
        x1, x2 = x(hi), x(lo)
        s.append(f'<rect x="{_n(x1)}" y="{top - 10}" width="{_n(x2 - x1)}" height="{H - top - bottom + 10}" fill="{fill}"/>')
        s.append(f'<text x="{_n((x1 + x2) / 2)}" y="{top - 34}" text-anchor="middle" font-size="30" fill="#4A4F7A">{label}</text>')
    for i, d in enumerate(items):
        cy = top + row_h * i + row_h / 2
        c = COLORS[i % len(COLORS)]
        bh = min(46, row_h * 0.5)
        bold = ' font-weight="bold"' if d["score"] == max_score else ""
        s.append(f'<circle cx="{W - 50}" cy="{_n(cy)}" r="30" fill="{c}"/>')
        s.append(f'<text x="{W - 50}" y="{_n(cy + 11)}" text-anchor="middle" font-size="28" font-weight="bold" fill="#fff">{escape(d["code"])}</text>')
        s.append(f'<text x="{W - 100}" y="{_n(cy + 12)}" text-anchor="end" font-size="34"{bold} fill="#1F2340">{escape(d["name"])}</text>')
        s.append(f'<rect x="{left}" y="{_n(cy - bh / 2)}" width="{plot_w}" height="{_n(bh)}" rx="{_n(bh / 2)}" fill="#FFFFFF" opacity="0.7"/>')
        bx = x(d["score"])
        s.append(f'<rect x="{_n(bx)}" y="{_n(cy - bh / 2)}" width="{_n(right - bx)}" height="{_n(bh)}" rx="{_n(bh / 2)}" fill="{c}"/>')
        s.append(f'<circle cx="{_n(bx)}" cy="{_n(cy)}" r="{_n(bh / 2 + 10)}" fill="#fff" stroke="{c}" stroke-width="6"/>')
        s.append(f'<text x="{_n(bx)}" y="{_n(cy + 10)}" text-anchor="middle" font-size="26" font-weight="bold" fill="{c}">{fa(round(d["score"]))}</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = [
    {"code": "و", "name": "واقع‌گرایی", "score": 42},
    {"code": "ج", "name": "جستجوگری", "score": 78},
    {"code": "هـ", "name": "هنری", "score": 55},
    {"code": "الف", "name": "اجتماعی", "score": 90},
    {"code": "م", "name": "متهور", "score": 30},
    {"code": "ق", "name": "قراردادی", "score": 64},
]

if __name__ == "__main__":
    with open("holland_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_holland_chart(SAMPLE))
    print("holland_chart.svg ساخته شد")
