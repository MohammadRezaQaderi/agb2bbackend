# -*- coding: utf-8 -*-
"""
لوله سنجش (Test Tube) — کارنامه ۱ باآزمون (بازطراحی لوله‌های هوش‌های گاردنر)
برای هر هوش یک لوله با رنگ همان هوش ساخته می‌شود.
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده:
    from test_tube_chart import render_test_tube_chart, GARDNER_COLORS
    svg = render_test_tube_chart(64, color=GARDNER_COLORS[0])     # score: ۰ تا ۱۰۰
GARDNER_COLORS به ترتیب: تصویری–فضایی، کلامی–زبانی، منطقی–ریاضی، جسمی–حرکتی،
موسیقایی، بین‌فردی، درون‌فردی، طبیعت‌گرا
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
import itertools

INK, MUTED = "#1F2340", "#7A7FA3"
GARDNER_COLORS = ["#00A0C2", "#D19C00", "#2D7FD3", "#E84393", "#4E9A30", "#7B5CD6", "#E07B12", "#E2574C"]
_ids = itertools.count(1)


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def render_test_tube_chart(score, color="#2D7FD3", width=240, height=700, font="IRAN"):
    uid = f"tt{next(_ids)}"
    W, H = width, height
    score = max(0, min(100, score))
    tx, tw = 35, min(130, W * 0.47)  # لوله؛ استفاده بهتر از عرض باکس تصویر باریک
    top, bottom = max(82, H * 0.11), H - max(24, H * 0.035)
    r = tw / 2
    body_top, body_bot = top + 26, bottom - r
    lvl_bot = bottom - 8
    lvl_top = body_top + 20
    ly = lvl_bot - (lvl_bot - lvl_top) * score / 100
    tube = (f"M{tx},{top} L{tx},{_n(body_bot)} A{_n(r)},{_n(r)} 0 0 0 {tx + tw},{_n(body_bot)} L{tx + tw},{top}")
    inner = (f"M{tx + 9},{_n(ly)} L{tx + 9},{_n(body_bot)} A{_n(r - 9)},{_n(r - 9)} 0 0 0 {tx + tw - 9},{_n(body_bot)} L{tx + tw - 9},{_n(ly)} Z")
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{font}">',
         f'<defs><linearGradient id="{uid}l" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{color}" stop-opacity="0.75"/>'
         f'<stop offset="0.45" stop-color="{color}"/><stop offset="1" stop-color="{color}" stop-opacity="0.8"/></linearGradient>'
         f'<linearGradient id="{uid}g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.9"/>'
         f'<stop offset="1" stop-color="#EEF0F7" stop-opacity="0.9"/></linearGradient></defs>',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>',
         f'<path d="{tube}" fill="url(#{uid}g)" stroke="#C9CCDD" stroke-width="5" stroke-linejoin="round"/>']
    if score > 0:
        s.append(f'<path d="{inner}" fill="url(#{uid}l)"/>')
        s.append(f'<ellipse cx="{tx + tw / 2}" cy="{_n(ly)}" rx="{_n(r - 9)}" ry="8" fill="{color}" opacity="0.55"/>')
        for bx, by, br in [(tx + 30, ly + 40, 6), (tx + 58, ly + 90, 4), (tx + 40, ly + 150, 5)]:
            if by < body_bot:
                s.append(f'<circle cx="{bx}" cy="{_n(by)}" r="{br}" fill="#FFFFFF" opacity="0.45"/>')
    s.append(f'<rect x="{tx + 16}" y="{top + 30}" width="10" height="{_n(body_bot - top - 60)}" rx="5" fill="#FFFFFF" opacity="0.7"/>')
    s.append(f'<rect x="{tx - 12}" y="{top - 10}" width="{tw + 24}" height="26" rx="13" fill="#FFFFFF" stroke="#C9CCDD" stroke-width="5"/>')
    for g in range(0, 101, 10):
        y = lvl_bot - (lvl_bot - lvl_top) * g / 100
        major = g % 20 == 0
        s.append(f'<line x1="{tx + tw + 8}" x2="{tx + tw + (26 if major else 16)}" y1="{_n(y)}" y2="{_n(y)}" stroke="#B5B9CF" stroke-width="{3 if major else 2}" stroke-linecap="round"/>')
        if major:
            s.append(f'<text x="{tx + tw + 25}" y="{_n(y + 7)}" text-anchor="start" font-size="{max(18, W * 0.075):.1f}" fill="{MUTED}">{fa(g)}</text>')
    badge_w, badge_h = tw + 36, max(54, H * 0.075)
    badge_y = max(8, top * 0.12)
    s.append(f'<rect x="{tx + tw / 2 - badge_w / 2}" y="{_n(badge_y)}" width="{_n(badge_w)}" height="{_n(badge_h)}" rx="{_n(badge_h / 2)}" fill="{color}"/>')
    s.append(f'<text x="{tx + tw / 2}" y="{_n(badge_y + badge_h * 0.69)}" text-anchor="middle" font-size="{max(28, W * 0.13):.1f}" font-weight="bold" fill="#FFFFFF">{fa(round(score))}٪</text>')
    s.append(f'<polygon points="{tx + tw / 2 - 12},{_n(badge_y + badge_h)} {tx + tw / 2 + 12},{_n(badge_y + badge_h)} {tx + tw / 2},{_n(badge_y + badge_h + 12)}" fill="{color}"/>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE_SCORES = [64, 72, 58, 45, 50, 80, 68, 40]
SAMPLES = [("لوله‌های سنجش هوش‌های گاردنر (کارنامه ۱) — هشت نمونه", lambda: "".join(
    f'<div style="display:inline-block;width:11.5%;vertical-align:top">{render_test_tube_chart(v, GARDNER_COLORS[i])}</div>'
    for i, v in enumerate(SAMPLE_SCORES)))]

if __name__ == "__main__":
    with open("test_tube_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_test_tube_chart(64, GARDNER_COLORS[0]))
    print("test_tube_chart.svg ساخته شد")
