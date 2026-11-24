# -*- coding: utf-8 -*-
"""
نمودار تناسب کلی با هفت شاخه تحصیلی — کارنامه ۲ (هدایت تحصیلی) باآزمون
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده (score عدد ۰ تا ۱۰۰؛ ترتیب ردیف‌ها همان ترتیب آرایه):
    from branch_fit_chart import render_branch_fit_chart
    svg = render_branch_fit_chart([
        {"name": "ریاضی و فیزیک", "score": 78},
        {"name": "علوم تجربی", "score": 64},
        ...
    ])
پیشنهاد محاسبه score: میانگین میزان تناسب چند رشته برتر هر شاخه (همان مقادیر T1).
سطح‌ها: ۰–۲۰ خیلی کم، ۲۰–۴۰ کم، ۴۰–۶۰ متوسط، ۶۰–۸۰ زیاد، ۸۰–۱۰۰ خیلی زیاد
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
from html import escape

COLORS = ["#E8505B", "#E39B00", "#9DB000", "#1FA463", "#0FA3C9", "#2F6FD6", "#8456C9"]
LEVELS = ["خیلی کم", "کم", "متوسط", "زیاد", "خیلی زیاد"]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def level(v):
    return LEVELS[min(4, int(max(0, v) // 20))]


def render_branch_fit_chart(items, width=1600, height=900, font="IRAN"):
    W, H = width, height
    top, bottom, label_w, left = 90, 30, 420, 320
    right = W - label_w
    plot_w = right - left
    row_h = (H - top - bottom) / len(items)
    max_s = max(d["score"] for d in items)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for g in range(6):
        gx = right - plot_w * g / 5
        s.append(f'<line x1="{_n(gx)}" x2="{_n(gx)}" y1="{top - 20}" y2="{H - bottom}" stroke="#E4E6F0" stroke-width="2" stroke-dasharray="6 8"/>')
        if g < 5:
            s.append(f'<text x="{_n(gx - plot_w / 10)}" y="{top - 40}" text-anchor="middle" font-size="26" fill="#8A8FB0">{LEVELS[g]}</text>')
    for i, d in enumerate(items):
        cy = top + row_h * i + row_h / 2
        c = COLORS[i % len(COLORS)]
        bh = min(48, row_h * 0.55)
        w = plot_w * max(0, min(100, d["score"])) / 100
        best = d["score"] == max_s
        bold = ' font-weight="bold"' if best else ""
        star = " ★" if best else ""
        s.append(f'<text x="{W - 40}" y="{_n(cy + 12)}" text-anchor="end" font-size="34"{bold} fill="#1F2340">{escape(d["name"])}{star}</text>')
        s.append(f'<rect x="{left}" y="{_n(cy - bh / 2)}" width="{plot_w}" height="{_n(bh)}" rx="{_n(bh / 2)}" fill="{c}" opacity="0.13"/>')
        s.append(f'<rect x="{_n(right - w)}" y="{_n(cy - bh / 2)}" width="{_n(w)}" height="{_n(bh)}" rx="{_n(bh / 2)}" fill="{c}"/>')
        s.append(f'<text x="{left - 24}" y="{_n(cy + 11)}" text-anchor="end" font-size="30" font-weight="bold" fill="{c}">{fa(round(d["score"]))}٪</text>')
        s.append(f'<text x="30" y="{_n(cy + 11)}" text-anchor="start" font-size="26" fill="#5B6085">{level(d["score"])}</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = [
    {"name": "ریاضی و فیزیک", "score": 78},
    {"name": "علوم تجربی", "score": 64},
    {"name": "علوم انسانی", "score": 52},
    {"name": "گروه هنر", "score": 35},
    {"name": "گروه کشاورزی", "score": 28},
    {"name": "گروه مدیریت و خدمات", "score": 47},
    {"name": "گروه صنعت", "score": 59},
]

if __name__ == "__main__":
    with open("branch_fit_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_branch_fit_chart(SAMPLE))
    print("branch_fit_chart.svg ساخته شد")
