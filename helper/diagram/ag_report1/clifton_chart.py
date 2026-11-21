# -*- coding: utf-8 -*-
"""
نمودار چهار حوزه استعداد کلیفتون — کارنامه ۱ باآزمون
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده (score عدد ۰ تا ۱۰۰؛ ستون‌ها از راست به چپ به ترتیب آرایه):
    from clifton_chart import render_clifton_chart
    svg = render_clifton_chart([
        {"name": "تفکر استراتژیک", "score": 72},
        {"name": "ساخت روابط", "score": 58},
        {"name": "نفوذ و تأثیرگذاری", "score": 40},
        {"name": "اجرایی", "score": 66},
    ])
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
from html import escape

COLORS = ["#2E9E5B", "#3E64C9", "#F2A900", "#7D3CBD"]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render_clifton_chart(items, width=1600, height=820, font="IRAN"):
    W, H = width, height
    top, base = 90, H - 150
    n = len(items)
    col_w = (W - 120) / n
    bar_w = min(170, col_w * 0.5)
    max_score = max(d["score"] for d in items)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for g in (0, 25, 50, 75, 100):
        y = base - (base - top) * g / 100
        dash = "8 8" if g else "0"
        s.append(f'<line x1="60" x2="{W - 60}" y1="{_n(y)}" y2="{_n(y)}" stroke="#E4E6F0" stroke-width="2" stroke-dasharray="{dash}"/>')
        s.append(f'<text x="40" y="{_n(y + 9)}" text-anchor="middle" font-size="24" fill="#8A8FB0">{fa(g)}</text>')
    for i, d in enumerate(items):
        c = COLORS[i % len(COLORS)]
        cx = W - 60 - col_w * i - col_w / 2  # راست‌به‌چپ
        h = (base - top) * max(0, min(100, d["score"])) / 100
        s.append(f'<rect x="{_n(cx - bar_w / 2)}" y="{top}" width="{_n(bar_w)}" height="{base - top}" rx="{_n(bar_w / 2)}" fill="{c}" opacity="0.12"/>')
        s.append(f'<rect x="{_n(cx - bar_w / 2)}" y="{_n(base - h)}" width="{_n(bar_w)}" height="{_n(h)}" rx="{_n(min(bar_w / 2, h / 2))}" fill="{c}"/>')
        s.append(f'<circle cx="{_n(cx)}" cy="{_n(base - h)}" r="44" fill="#fff" stroke="{c}" stroke-width="7"/>')
        s.append(f'<text x="{_n(cx)}" y="{_n(base - h + 12)}" text-anchor="middle" font-size="34" font-weight="bold" fill="{c}">{fa(round(d["score"]))}</text>')
        s.append(f'<text x="{_n(cx)}" y="{base + 62}" text-anchor="middle" font-size="36" font-weight="bold" fill="#1F2340">{escape(d["name"])}</text>')
        if d["score"] == max_score:
            s.append(f'<text x="{_n(cx)}" y="{base + 112}" text-anchor="middle" font-size="26" fill="{c}">★ حوزه برتر شما</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = [
    {"name": "تفکر استراتژیک", "score": 72},
    {"name": "ساخت روابط", "score": 58},
    {"name": "نفوذ و تأثیرگذاری", "score": 40},
    {"name": "اجرایی", "score": 66},
]

if __name__ == "__main__":
    with open("clifton_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_clifton_chart(SAMPLE))
    print("clifton_chart.svg ساخته شد")
