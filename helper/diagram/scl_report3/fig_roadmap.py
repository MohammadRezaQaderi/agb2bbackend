# -*- coding: utf-8 -*-
"""نقشه مسیر (جاده پیچ‌درپیچ) برای سه دسته عوامل.
تصویر فقط شامل جاده، ایستگاه‌ها و قاب کارت‌هاست؛ نام ایستگاه و تگ‌ها (statefast و ...)
به‌صورت متن روی تصویر در سند قرار می‌گیرند تا موتور گزارش‌ساز بتواند آن‌ها را جایگزین کند.
تابع layout مختصات کارت‌ها را برمی‌گرداند (میلی‌متر) تا سند دقیقاً روی همان نقاط چیده شود.
اجرا: python fig_roadmap.py out
"""
try:  # Package import in the SCL renderer; standalone compatibility for source users.
    from .svgkit import PALETTE as P, svg_doc, text, save, fa
    from .fig_icons import icon_group
except ImportError:  # pragma: no cover - standalone script invocation
    from svgkit import PALETTE as P, svg_doc, text, save, fa
    from fig_icons import icon_group
import os, sys, math

W, H = 180, 196
CARD_X, CARD_W, CARD_H = 3, 143, 26
ROAD_X = 162

STATIONS = {
    "surface": ["addict", "body", "sleep", "mobile", "future", "study"],
    "psych":   ["anx", "dep", "ocd", "mot", "conf"],
    "root":    ["adhd", "family", "inter", "ideal", "truma"],
}

def layout(n):
    top, bottom = 16, H - 14
    step = (bottom - top) / n
    ys = [top + step * (i + 0.5) for i in range(n)]
    cards = [dict(x=CARD_X, y=y - CARD_H / 2, w=CARD_W, h=CARD_H, cy=y) for y in ys]
    return cards

def road_x(y):
    return ROAD_X + 7 * math.sin(y / 18.0)

def roadmap(cat):
    keys = STATIONS[cat]
    cards = layout(len(keys))
    c, cl, cd = P[cat], P[cat + "_l"], P[cat + "_d"]
    body = f'<rect x="0" y="0" width="{W}" height="{H}" rx="6" fill="{cl}"/>'
    # جاده
    pts = [(road_x(y), y) for y in [i * 2 for i in range(0, int(H / 2) + 1)]]
    d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts)
    body += f'<path d="{d}" fill="none" stroke="#4B5563" stroke-width="13" stroke-linecap="round"/>'
    body += f'<path d="{d}" fill="none" stroke="#6B7280" stroke-width="11" stroke-linecap="round"/>'
    body += f'<path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="0.9" stroke-dasharray="4 3"/>'
    # شروع و پایان
    body += f'<rect x="{road_x(5)-11}" y="1.5" width="22" height="8" rx="4" fill="{cd}"/>'
    body += text(road_x(5), 7.2, "شروع مسیر", size=3.4, fill="#fff", weight="bold", anchor="middle")
    body += f'<rect x="{road_x(H-5)-11}" y="{H-9.5}" width="22" height="8" rx="4" fill="{cd}"/>'
    body += text(road_x(H-5), H-3.8, "پایان مسیر", size=3.4, fill="#fff", weight="bold", anchor="middle")
    for i, (k, cd_) in enumerate(zip(keys, cards)):
        y = cd_["cy"]; rx = road_x(y)
        # اتصال کارت به ایستگاه
        body += f'<line x1="{CARD_X+CARD_W}" y1="{y}" x2="{rx-7}" y2="{y}" stroke="{c}" stroke-width="1" stroke-dasharray="1.6 1.2"/>'
        # کارت
        body += (f'<rect x="{cd_["x"]+0.8}" y="{cd_["y"]+1.2}" width="{CARD_W}" height="{CARD_H}" rx="5" fill="#000" opacity="0.06"/>'
                 f'<rect x="{cd_["x"]}" y="{cd_["y"]}" width="{CARD_W}" height="{CARD_H}" rx="5" fill="#fff" stroke="{c}" stroke-width="0.7"/>'
                 f'<rect x="{CARD_X+CARD_W-4}" y="{cd_["y"]}" width="4" height="{CARD_H}" rx="2" fill="{c}"/>')
        # آیکون داخل کارت (سمت راست)
        body += f'<g transform="translate({CARD_X+CARD_W-22},{y-8}) scale(0.16)">{icon_group(k)}</g>'
        # ایستگاه
        body += f'<circle cx="{rx}" cy="{y}" r="7" fill="#fff" stroke="{c}" stroke-width="1.6"/>'
        body += text(rx, y + 2.3, fa(i + 1), size=6, fill=cd, weight="bold", anchor="middle")
    return svg_doc(W, H, body)

def build(outdir="out"):
    return {cat: save(os.path.join(outdir, f"roadmap_{cat}.svg"), roadmap(cat)) for cat in STATIONS}

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "out")
