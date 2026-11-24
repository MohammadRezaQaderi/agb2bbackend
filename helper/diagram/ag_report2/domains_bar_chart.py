# -*- coding: utf-8 -*-
"""
نمودار انطباق با ۱۸ حوزه کاری — کارنامه ۲ باآزمون (بازطراحی نمودار میله‌ای)
میله‌ها افقی و از بیشترین به کمترین مرتب می‌شوند و رنگ هر میله سطح انطباق را نشان می‌دهد.
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده (score عدد ۰ تا ۱۰۰):
    from domains_bar_chart import render_domains_bar_chart
    svg = render_domains_bar_chart([{"name": "دبیری و آموزش", "score": 68}, ...], sort=True)
سطح‌ها: ۰–۲۰ خیلی کم، ۲۰–۴۰ کم، ۴۰–۶۰ متوسط، ۶۰–۸۰ زیاد، ۸۰–۱۰۰ خیلی زیاد
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
from html import escape

INK, MUTED, GRID = "#1F2340", "#7A7FA3", "#E8EAF3"
LEVELS = [("خیلی کم", "#E8505B"), ("کم", "#F28C4B"), ("متوسط", "#F2C230"), ("زیاد", "#7CC46A"), ("خیلی زیاد", "#2E9E5B")]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def level(v):
    return LEVELS[min(4, int(max(0, v) // 20))]


def render_domains_bar_chart(items, sort=True, width=1600, height=None, font="IRAN"):
    data = sorted(items, key=lambda d: -d["score"]) if sort else list(items)
    W = width
    row_h = 120
    top = 155
    H = height or int(top + row_h * len(data) + 40)
    lab = 1150
    right, left = W - lab, 120
    pw = right - left
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">', '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    # راهنمای سطح‌ها
    lx = right
    for name, col in reversed(LEVELS):
        w = 40 + 19 * len(name)
        lx -= w + 18
        s.append(f'<rect x="{_n(lx)}" y="26" width="{_n(w)}" height="44" rx="22" fill="{col}" opacity="0.15"/>')
        s.append(f'<circle cx="{_n(lx + w - 22)}" cy="48" r="9" fill="{col}"/>')
        s.append(f'<text x="{_n(lx + w - 40)}" y="57" text-anchor="end" font-size="30" fill="{INK}">{name}</text>')
    for g in range(0, 101, 20):
        x = right - pw * g / 100
        s.append(f'<line x1="{_n(x)}" x2="{_n(x)}" y1="{top - 16}" y2="{H - 30}" stroke="{GRID}" stroke-width="2" stroke-dasharray="6 8"/>')
        s.append(f'<text x="{_n(x)}" y="{top - 26}" text-anchor="middle" font-size="30" fill="{MUTED}">{fa(g)}</text>')
    for i, d in enumerate(data):
        cy = top + row_h * i + row_h / 2
        name, col = level(d["score"])
        w = pw * max(0, min(100, d["score"])) / 100
        bold = ' font-weight="bold"' if i < 3 and sort else ""
        s.append(f'<text x="{W - 80}" y="{_n(cy + 20)}" text-anchor="end" font-size="68"{bold} fill="{INK}">{escape(d["name"])}</text>')
        s.append(f'<circle cx="{W - 46}" cy="{_n(cy)}" r="31" fill="{col}" opacity="0.18"/>')
        s.append(f'<text x="{W - 46}" y="{_n(cy + 12)}" text-anchor="middle" font-size="32" font-weight="bold" fill="{col}">{fa(i + 1)}</text>')
        s.append(f'<rect x="{left}" y="{_n(cy - 28)}" width="{pw}" height="56" rx="28" fill="#F2F3F8"/>')
        if w > 0:
            s.append(f'<rect x="{_n(right - w)}" y="{_n(cy - 28)}" width="{_n(w)}" height="56" rx="28" fill="{col}"/>')
        s.append(f'<text x="{_n(right - w - 18)}" y="{_n(cy + 18)}" text-anchor="end" font-size="52" font-weight="bold" fill="{col}">{fa(round(d["score"]))}٪</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = [{"name": n, "score": v} for n, v in [
    ("دبیری و آموزش", 68), ("مدیریت", 66), ("علوم پایه", 72), ("هنر", 41), ("مهندسی سازه و عمران", 55),
    ("مهندسی صنعتی", 58), ("الکترونیک و کامپیوتر", 81), ("تربیت بدنی", 33), ("مالی و حسابداری", 61),
    ("روان‌شناسی و خدمات اجتماعی", 74), ("روابط عمومی و رسانه", 49), ("کشاورزی و امور دامی", 27),
    ("حقوق و علوم سیاسی", 52), ("خدمات فنی", 22), ("تکنسین فنی", 18), ("درمانی – بالینی", 77),
    ("تشخیصی – درمانی", 63), ("تکنسین کامپیوتر", 46)]]
SAMPLES = [("انطباق با ۱۸ حوزه کاری (کارنامه ۲)", lambda: render_domains_bar_chart(SAMPLE))]

if __name__ == "__main__":
    with open("domains_bar_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_domains_bar_chart(SAMPLE))
    print("domains_bar_chart.svg ساخته شد")
