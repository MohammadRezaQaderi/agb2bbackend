# -*- coding: utf-8 -*-
"""
نمودار تعهد تحصیلی — کارنامه ۱ باآزمون (نمودار جدید)
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده:
    from commitment_chart import render_commitment_chart
    svg = render_commitment_chart({"score": 68})
    # score: نمره تعهد تحصیلی بین ۰ تا ۱۰۰
    # label (اختیاری): اگر سیستم شما سطح را خودش تعیین می‌کند، متن آن را بدهید.

سطح‌ها: ۰–۲۰ خیلی کم، ۲۰–۴۰ کم، ۴۰–۶۰ متوسط، ۶۰–۸۰ زیاد، ۸۰–۱۰۰ خیلی زیاد
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
import math
from html import escape

INK, MUTED, MAIN = "#1F2340", "#6B7096", "#1C6FB8"
LEVELS = [("خیلی کم", "#E8505B"), ("کم", "#F28C4B"), ("متوسط", "#F2C230"), ("زیاد", "#7CC46A"), ("خیلی زیاد", "#2E9E5B")]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render_commitment_chart(data, width=1600, height=640, font="IRAN"):
    W, H = width, height
    score = max(0, min(100, float(data.get("score") or 0)))
    li = min(4, int(score // 20))
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>']

    # گیج نیم‌دایره (سمت راست)
    cx, cy, r = W - 480, H - 150, 290
    pt = lambda a, rr: (cx - rr * math.cos(a), cy - rr * math.sin(a))
    for i, (name, color) in enumerate(LEVELS):
        a1, a2 = math.pi * i / 5 + 0.012, math.pi * (i + 1) / 5 - 0.012
        p1, p2, lp = pt(a1, r), pt(a2, r), pt((a1 + a2) / 2, r + 52)
        anc = "end" if i < 2 else ("start" if i > 2 else "middle")
        on = i == li
        s.append(f'<path d="M{_n(p1[0])},{_n(p1[1])} A{r},{r} 0 0 1 {_n(p2[0])},{_n(p2[1])}" stroke="{color}" '
                 f'stroke-width="70" fill="none" opacity="{1 if on else 0.35}"/>')
        bold = ' font-weight="bold"' if on else ""
        s.append(f'<text x="{_n(lp[0])}" y="{_n(lp[1] + 10)}" text-anchor="{anc}" font-size="28"{bold} '
                 f'fill="{color if on else MUTED}">{name}</text>')
    tip = pt(math.pi * score / 100, r - 20)
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{_n(tip[0])}" y2="{_n(tip[1])}" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="24" fill="{INK}"/>')
    s.append(f'<text x="{cx}" y="{cy + 100}" text-anchor="middle" font-size="40" fill="{MUTED}">نمره تعهد تحصیلی: '
             f'<tspan font-weight="bold" fill="{MAIN}">{fa(round(score))} از ۱۰۰</tspan></text>')

    # نردبان سطح‌ها (سمت چپ)
    x0, bw, row_h, y0 = 70, 560, 92, 70
    s.append(f'<text x="{x0 + bw}" y="{y0 - 18}" text-anchor="end" font-size="32" font-weight="bold" fill="{INK}">سطح تعهد تحصیلی شما</text>')
    for k in range(4, -1, -1):
        name, color = LEVELS[k]
        y = y0 + (4 - k) * row_h + 14
        on = k == li
        s.append(f'<rect x="{x0}" y="{y}" width="{bw}" height="{row_h - 16}" rx="20" fill="{color}" opacity="{1 if on else 0.14}"/>')
        style = 'font-weight="bold" fill="#FFFFFF"' if on else f'fill="{MUTED}"'
        s.append(f'<text x="{x0 + bw - 30}" y="{_n(y + row_h / 2 + 4)}" text-anchor="end" font-size="32" {style}>{name}</text>')
        if on:
            s.append(f'<text x="{x0 + 30}" y="{_n(y + row_h / 2 + 4)}" text-anchor="start" font-size="28" font-weight="bold" fill="#FFFFFF">◀ شما اینجا هستید</text>')
    if data.get("label"):
        s.append(f'<text x="{x0 + bw}" y="{y0 + 5 * row_h + 40}" text-anchor="end" font-size="28" fill="{MUTED}">{escape(data["label"])}</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = {"score": 68}

if __name__ == "__main__":
    with open("commitment_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_commitment_chart(SAMPLE))
    print("commitment_chart.svg ساخته شد")
