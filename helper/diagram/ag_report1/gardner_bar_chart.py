# -*- coding: utf-8 -*-
"""
نمودار هوش‌های هشت‌گانه گاردنر — کارنامه ۱ باآزمون (بازطراحی نمودار میله‌ای)
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده (score عدد ۰ تا ۱۰۰؛ ستون‌ها از راست به چپ به ترتیب آرایه):
    from gardner_bar_chart import render_gardner_bar_chart
    svg = render_gardner_bar_chart([{"name": "تصویری–فضایی", "score": 64}, ...])
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
import itertools
from html import escape

INK, MUTED, GRID = "#1F2340", "#7A7FA3", "#E8EAF3"
COLORS = ["#00A0C2", "#D19C00", "#2D7FD3", "#E84393", "#4E9A30", "#7B5CD6", "#E07B12", "#E2574C"]
_ids = itertools.count(1)


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render_gardner_bar_chart(items, width=1600, height=900, font="IRAN"):
    uid = f"gb{next(_ids)}"
    W, H = width, height
    top, base, left, right = 110, H - 170, 90, W - 40
    n = len(items)
    col_w = (right - left) / n
    bw = min(110, col_w * 0.55)
    max_s = max(d["score"] for d in items)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}"><defs>']
    for i in range(n):
        c = COLORS[i % len(COLORS)]
        s.append(f'<linearGradient id="{uid}{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c}"/>'
                 f'<stop offset="1" stop-color="{c}" stop-opacity="0.65"/></linearGradient>')
    s.append('</defs><rect width="100%" height="100%" fill="#FFFFFF"/>')
    for g in range(0, 101, 20):
        y = base - (base - top) * g / 100
        s.append(f'<line x1="{left}" x2="{right}" y1="{_n(y)}" y2="{_n(y)}" stroke="{GRID}" stroke-width="2" {"" if g == 0 else "stroke-dasharray=" + chr(34) + "6 8" + chr(34)}/>')
        s.append(f'<text x="{left - 20}" y="{_n(y + 8)}" text-anchor="end" font-size="24" fill="{MUTED}">{fa(g)}</text>')
    for i, d in enumerate(items):
        c = COLORS[i % len(COLORS)]
        cx = right - col_w * i - col_w / 2
        h = (base - top) * max(0, min(100, d["score"])) / 100
        best = d["score"] == max_s
        s.append(f'<rect x="{_n(cx - bw / 2)}" y="{top}" width="{_n(bw)}" height="{base - top}" rx="{_n(bw / 2)}" fill="{c}" opacity="0.07"/>')
        if h > 0:
            rr = min(bw / 2, h)
            xl, xr, yt = cx - bw / 2, cx + bw / 2, base - h
            path = (f"M{_n(xl)},{base} L{_n(xl)},{_n(yt + rr)} A{_n(bw / 2)},{_n(rr)} 0 0 1 {_n(xr)},{_n(yt + rr)} "
                    f"L{_n(xr)},{base} Z")
            s.append(f'<path d="{path}" fill="url(#{uid}{i})"/>')
        by = base - h - 52
        s.append(f'<rect x="{_n(cx - 46)}" y="{_n(by)}" width="92" height="42" rx="21" fill="{c if best else "#FFFFFF"}" stroke="{c}" stroke-width="3"/>')
        s.append(f'<text x="{_n(cx)}" y="{_n(by + 30)}" text-anchor="middle" font-size="26" font-weight="bold" fill="{"#FFFFFF" if best else c}">{fa(round(d["score"]))}</text>')
        if best:
            s.append(f'<text x="{_n(cx)}" y="{_n(by - 14)}" text-anchor="middle" font-size="30" fill="#F2B705">★</text>')
        parts = [p.strip() for p in d["name"].replace("-", "–").split("–")]
        for k, p in enumerate(parts[:2]):
            s.append(f'<text x="{_n(cx)}" y="{base + 46 + k * 36}" text-anchor="middle" font-size="27" '
                     f'{"font-weight=" + chr(34) + "bold" + chr(34) + " " if best else ""}fill="{INK}">{escape(p)}</text>')
        s.append(f'<circle cx="{_n(cx)}" cy="{base + 22 + 36 * len(parts[:2]) + 30}" r="7" fill="{c}"/>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = [{"name": n, "score": v} for n, v in [
    ("تصویری–فضایی", 64), ("کلامی–زبانی", 72), ("منطقی–ریاضی", 58), ("جسمی–حرکتی", 45),
    ("موسیقایی", 50), ("بین‌فردی", 80), ("درون‌فردی", 68), ("طبیعت‌گرا", 40)]]
SAMPLES = [("هوش‌های هشت‌گانه گاردنر (کارنامه ۱)", lambda: render_gardner_bar_chart(SAMPLE))]

if __name__ == "__main__":
    with open("gardner_bar_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_gardner_bar_chart(SAMPLE))
    print("gardner_bar_chart.svg ساخته شد")
