# -*- coding: utf-8 -*-
"""
گیج چارت (نمودار عقربه‌ای) — بازطراحی‌شده برای کارنامه‌های باآزمون
کاربردها:
  • کارنامه ۱: ضریب هوشی کتل           ← render_gauge_chart(112, **IQ_PRESET)
  • کارنامه ۲: انطباق با هر حوزه کاری   ← render_gauge_chart(56, **MATCH_PRESET)
  • هر شاخص دیگری با بازه و سطح‌های دلخواه
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده:
    from gauge_chart import render_gauge_chart, IQ_PRESET, MATCH_PRESET
    svg = render_gauge_chart(56, **MATCH_PRESET)
    svg = render_gauge_chart(112, **IQ_PRESET)
    svg = render_gauge_chart(70, vmin=0, vmax=100,
            segments=[(0, 50, "پایین", "#E8505B"), (50, 100, "بالا", "#2E9E5B")],
            caption="میزان انطباق")

پارامترها:
    value     مقدار
    vmin/vmax بازه نمودار
    segments  فهرست (از، تا، نام سطح، رنگ)
    caption   متن زیر عدد (مثلاً «ضریب هوشی»)
    show_value_suffix  پسوند عدد (مثلاً "٪")
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
import math
import itertools
from html import escape

INK, MUTED, TRACK = "#1F2340", "#7A7FA3", "#EEF0F7"
_ids = itertools.count(1)

MATCH_PRESET = dict(
    vmin=0, vmax=100, caption="میزان انطباق شما", show_value_suffix="٪",
    segments=[(0, 20, "خیلی کم", "#E8505B"), (20, 40, "کم", "#F28C4B"), (40, 60, "متوسط", "#F2C230"),
              (60, 80, "زیاد", "#7CC46A"), (80, 100, "خیلی زیاد", "#2E9E5B")])

IQ_PRESET = dict(
    vmin=40, vmax=170, caption="ضریب هوشی", show_value_suffix="",
    segments=[(40, 90, "زیر متوسط", "#F28C4B"), (90, 110, "متوسط", "#F2C230"),
              (110, 120, "قوی", "#9BD06A"), (120, 132, "باهوش", "#4FB06A"), (132, 170, "تیزهوش", "#1F8F5B")])


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _arc(cx, cy, r, a1, a2):
    p = lambda a: (cx - r * math.cos(a), cy - r * math.sin(a))
    x1, y1 = p(a1)
    x2, y2 = p(a2)
    large = 1 if (a2 - a1) > math.pi else 0
    return f"M{_n(x1)},{_n(y1)} A{r},{r} 0 {large} 1 {_n(x2)},{_n(y2)}"


def render_gauge_chart(value, vmin=0, vmax=100, segments=None, caption="", show_value_suffix="",
                       width=1000, height=640, font="IRAN"):
    segments = segments or MATCH_PRESET["segments"]
    uid = f"g{next(_ids)}"
    W, H = width, height
    # Fit the semi-circle to the requested canvas while preserving its shape.
    # Report2 detail pages have a short, wide image box; scale the illustration
    # to that box instead of leaving large unused margins around a fixed gauge.
    scale = min(W / 1000, H / 640)
    cx = W / 2
    cy = 0.615 * H
    r = min(0.414 * H, 0.40 * W)
    th = 0.0875 * H
    v = max(vmin, min(vmax, value))
    t = (v - vmin) / (vmax - vmin)
    ang = lambda x: math.pi * (max(vmin, min(vmax, x)) - vmin) / (vmax - vmin)
    active = next((s for s in segments if s[0] <= v <= s[1]), segments[-1])
    acol = active[3]

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">',
         f'<defs><radialGradient id="{uid}bg" cx="50%" cy="70%" r="65%"><stop offset="0" stop-color="{acol}" stop-opacity="0.10"/>'
         f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
         f'<linearGradient id="{uid}nd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3A3F6B"/><stop offset="1" stop-color="{INK}"/></linearGradient></defs>',
         '<rect width="100%" height="100%" fill="#FFFFFF"/>',
         f'<circle cx="{_n(cx)}" cy="{cy}" r="{r + 60}" fill="url(#{uid}bg)"/>']
    # مسیر زمینه
    s.append(f'<path d="{_arc(cx, cy, r, 0, math.pi)}" stroke="{TRACK}" stroke-width="{th + 16}" fill="none" stroke-linecap="round"/>')
    # سطح‌ها
    gap = 0.018
    for lo, hi, name, col in segments:
        a1, a2 = ang(lo) + gap, ang(hi) - gap
        on = (lo, hi, name, col) == active
        s.append(f'<path d="{_arc(cx, cy, r, a1, a2)}" stroke="{col}" stroke-width="{th}" fill="none" opacity="{1 if on else 0.28}"/>')
        if on:
            s.append(f'<path d="{_arc(cx, cy, r + th / 2 + 12, a1, a2)}" stroke="{col}" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.55"/>')
        am = (a1 + a2) / 2
        label_r = r + th / 2 + 0.078 * H
        lx, ly = cx - label_r * math.cos(am), cy - label_r * math.sin(am)
        anc = "end" if math.cos(am) > 0.35 else ("start" if math.cos(am) < -0.35 else "middle")
        s.append(f'<text x="{_n(lx)}" y="{_n(ly + 0.014 * H)}" text-anchor="{anc}" font-size="{_n(26 * scale)}" '
                 f'{"font-weight=" + chr(34) + "bold" + chr(34) + " " if on else ""}fill="{col if on else MUTED}">{escape(name)}</text>')
    # درجه‌بندی داخلی
    for i in range(41):
        a = math.pi * i / 40
        r1 = r - th / 2 - 0.022 * H
        r2 = r1 - ((0.025 if i % 5 == 0 else 0.013) * H)
        s.append(f'<line x1="{_n(cx - r1 * math.cos(a))}" y1="{_n(cy - r1 * math.sin(a))}" x2="{_n(cx - r2 * math.cos(a))}" '
                 f'y2="{_n(cy - r2 * math.sin(a))}" stroke="#C9CCDD" stroke-width="{_n((3 if i % 5 == 0 else 2) * scale)}" stroke-linecap="round"/>')
    # کمینه و بیشینه
    s.append(f'<text x="{_n(cx - r)}" y="{_n(cy + 0.078 * H)}" text-anchor="middle" font-size="{_n(24 * scale)}" fill="{MUTED}">{fa(vmin)}</text>')
    s.append(f'<text x="{_n(cx + r)}" y="{_n(cy + 0.078 * H)}" text-anchor="middle" font-size="{_n(24 * scale)}" fill="{MUTED}">{fa(vmax)}</text>')
    # عقربه
    a = math.pi * t
    tipx, tipy = cx - (r - th / 2 - 30) * math.cos(a), cy - (r - th / 2 - 30) * math.sin(a)
    nx, ny = math.sin(a) * 0.021 * H, -math.cos(a) * 0.021 * H
    tailx, taily = cx + 0.053 * H * math.cos(a), cy + 0.053 * H * math.sin(a)
    s.append(f'<polygon points="{_n(tipx)},{_n(tipy)} {_n(cx + nx)},{_n(cy + ny)} {_n(tailx)},{_n(taily)} {_n(cx - nx)},{_n(cy - ny)}" '
             f'fill="url(#{uid}nd)" stroke="#FFFFFF" stroke-width="3" stroke-linejoin="round"/>')
    s.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(0.047 * H)}" fill="#FFFFFF" stroke="{INK}" stroke-width="{_n(8 * scale)}"/>')
    s.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(0.017 * H)}" fill="{acol}"/>')
    # عدد و سطح
    val = fa(round(value)) + show_value_suffix
    s.append(f'<text x="{_n(cx)}" y="{_n(cy + 0.175 * H)}" text-anchor="middle" font-size="{_n(76 * scale)}" font-weight="bold" fill="{INK}">{val}</text>')
    if caption:
        s.append(f'<text x="{_n(cx)}" y="{_n(cy + 0.244 * H)}" text-anchor="middle" font-size="{_n(26 * scale)}" fill="{MUTED}">{escape(caption)}</text>')
    chip_h = 0.075 * H
    chip_w = min(W * 0.62, (46 + 22 * len(active[2])) * scale)
    chip_y = min(H - chip_h - 4, cy + 0.278 * H)
    s.append(f'<rect x="{_n(cx - chip_w / 2)}" y="{_n(chip_y)}" width="{_n(chip_w)}" height="{_n(chip_h)}" rx="{_n(chip_h / 2)}" fill="{acol}"/>')
    s.append(f'<text x="{_n(cx)}" y="{_n(chip_y + chip_h * 0.68)}" text-anchor="middle" font-size="{_n(27 * scale)}" font-weight="bold" fill="#FFFFFF">{escape(active[2])}</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLES = [
    ("ضریب هوشی کتل (کارنامه ۱)", lambda: render_gauge_chart(112, **IQ_PRESET)),
    ("انطباق با حوزه کاری — نمونه ۱ (کارنامه ۲)", lambda: render_gauge_chart(56, **MATCH_PRESET)),
    ("انطباق با حوزه کاری — نمونه ۲ (کارنامه ۲)", lambda: render_gauge_chart(87, **MATCH_PRESET)),
    ("انطباق با حوزه کاری — نمونه ۳ (کارنامه ۲)", lambda: render_gauge_chart(23, **MATCH_PRESET)),
]

if __name__ == "__main__":
    with open("gauge_chart.svg", "w", encoding="utf-8") as f:
        f.write(SAMPLES[0][1]())
    print("gauge_chart.svg ساخته شد")
