# -*- coding: utf-8 -*-
"""کارت جایگزین برای فیلم/کتاب‌هایی که تصویر جلد ندارند.
اجرا: python fig_media.py out
"""
try:  # Package import in the SCL renderer; standalone compatibility for source users.
    from .svgkit import PALETTE as P, svg_doc, text, save
except ImportError:  # pragma: no cover - standalone script invocation
    from svgkit import PALETTE as P, svg_doc, text, save
import os, sys

def card(kind, title, cat, w=30, h=42):
    c, cd = P[cat], P[cat + "_d"]
    b = f'<rect width="{w}" height="{h}" rx="3" fill="{c}"/><rect x="0" y="{h*0.62}" width="{w}" height="{h*0.38}" rx="3" fill="{cd}"/>'
    if kind == "film":
        b += f'<rect x="7" y="7" width="16" height="12" rx="1.5" fill="none" stroke="#fff" stroke-width="1.2"/>'
        b += f'<polygon points="13,10 13,16 18,13" fill="#fff"/>'
        for x in (8.5, 12, 15.5, 19, 22.5):
            pass
    else:
        b += f'<path d="M7 8 h7 a2 2 0 0 1 2 2 v12 a2 2 0 0 0 -2 -2 h-7z M23 8 h-7 a2 2 0 0 0 -2 2 v12 a2 2 0 0 1 2 -2 h7z" fill="none" stroke="#fff" stroke-width="1.1"/>'
    words = title.split()
    lines, cur = [], ""
    for wd in words:
        if len(cur) + len(wd) > 13 and cur:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    y = h * 0.62 + 5.5
    for ln in lines[:3]:
        b += text(w/2, y, ln, size=2.9, fill="#fff", weight="bold", anchor="middle"); y += 4
    return svg_doc(w, h, b)

ITEMS = {
    "media_dep_film": ("film", "درون و بیرون ۱", "psych"),
    "media_future_book": ("book", "انسان در جستجوی معنا", "surface"),
    "media_ocd_book": ("book", "کتاب کار درمان وسواس", "psych"),
    "media_adhd_book": ("book", "حواس‌پرت‌ها", "root"),
    "media_ideal_film": ("film", "انکانتو", "root"),
    "media_ideal_book": ("book", "موهبت‌های کامل نبودن", "root"),
}

def build(outdir="out"):
    for k, (kind, t, cat) in ITEMS.items():
        save(os.path.join(outdir, f"{k}.svg"), card(kind, t, cat))

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "out")
