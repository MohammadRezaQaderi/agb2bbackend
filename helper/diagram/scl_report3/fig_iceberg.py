# -*- coding: utf-8 -*-
"""نمودار کوه یخ سه لایه عوامل: سطحی (بالای آب)، روان‌شناختی (زیر سطح)، بنیادین (اعماق).
اجرا: python fig_iceberg.py out
"""
try:  # Package import in the SCL renderer; standalone compatibility for source users.
    from .svgkit import PALETTE as P, svg_doc, text, save, fa
except ImportError:  # pragma: no cover - standalone script invocation
    from svgkit import PALETTE as P, svg_doc, text, save, fa
import os, sys

W, H, WATER = 180, 120, 36

def iceberg():
    defs = ('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E8F3FA"/></linearGradient>'
            '<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#BFE2F3"/><stop offset="0.55" stop-color="#4E8DB8"/><stop offset="1" stop-color="#1F4E79"/></linearGradient>'
            '<linearGradient id="ice" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCEFF8"/></linearGradient>'
            '<linearGradient id="deep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E6F5FC" stop-opacity="0.95"/><stop offset="1" stop-color="#9FCBE3" stop-opacity="0.85"/></linearGradient>'
            f'<clipPath id="frame"><rect x="0" y="0" width="{W}" height="{H}" rx="6"/></clipPath>')
    b = f'<g clip-path="url(#frame)">'
    b += f'<rect x="0" y="0" width="{W}" height="{WATER}" fill="url(#sky)"/>'
    b += f'<rect x="0" y="{WATER}" width="{W}" height="{H-WATER}" fill="url(#sea)"/>'
    # بدنه زیر آب
    b += (f'<path d="M38 {WATER} C30 44 22 50 21 62 C19 76 16 92 30 110 C40 118 70 119 86 108 '
          f'C96 98 98 80 95 62 C93 50 90 42 84 {WATER} Z" fill="url(#deep)" stroke="#8CC3DE" stroke-width="0.5"/>')
    b += f'<path d="M58 {WATER} L50 62 L60 88 L52 112" fill="none" stroke="#FFFFFF" stroke-width="0.6" opacity="0.6"/>'
    b += f'<path d="M72 {WATER} L80 58 L74 84 L82 104" fill="none" stroke="#FFFFFF" stroke-width="0.6" opacity="0.5"/>'
    # نوک کوه بالای آب
    b += f'<path d="M38 {WATER} L49 15 L56 21 L65 6 L76 20 L84 {WATER} Z" fill="url(#ice)" stroke="#9CCFE6" stroke-width="0.6"/>'
    b += f'<path d="M65 6 L62 {WATER} M49 15 L53 {WATER}" fill="none" stroke="#C7E4F2" stroke-width="0.6"/>'
    # موج سطح آب
    wave = f"M0 {WATER} " + " ".join(f"q4 -1.6 8 0 t8 0" for _ in range(12))
    b += f'<path d="{wave}" fill="none" stroke="#5BA8D0" stroke-width="0.9"/>'
    b += '</g>'
    b += f'<rect x="0.3" y="0.3" width="{W-0.6}" height="{H-0.6}" rx="6" fill="none" stroke="{P["line"]}" stroke-width="0.6"/>'
    # کارت‌های لایه‌ها
    bands = [(1, "عوامل سطحی", "خواب، موبایل، مطالعه، بدن، آینده", 20, 74, "surface"),
             (2, "عوامل روان‌شناختی", "اضطراب، افسردگی، وسواس، انگیزه", 64, 94, "psych"),
             (3, "عوامل بنیادین", "خانواده، روابط، تمرکز، کمال‌گرایی، تروما", 98, 90, "root")]
    cx0, cw, ch = 100, 76, 17
    for n, title, sub, y, edge, k in bands:
        b += f'<line x1="{edge}" y1="{y}" x2="{cx0}" y2="{y}" stroke="{P[k]}" stroke-width="0.7" stroke-dasharray="1.8 1.3"/>'
        b += f'<circle cx="{edge}" cy="{y}" r="1.6" fill="{P[k]}" stroke="#fff" stroke-width="0.5"/>'
        b += f'<rect x="{cx0+0.5}" y="{y-ch/2+0.8}" width="{cw}" height="{ch}" rx="4" fill="#000" opacity="0.08"/>'
        b += f'<rect x="{cx0}" y="{y-ch/2}" width="{cw}" height="{ch}" rx="4" fill="#FFFFFF" stroke="{P[k]}" stroke-width="0.8"/>'
        b += f'<circle cx="{cx0+cw-7}" cy="{y}" r="4.6" fill="{P[k]}"/>'
        b += text(cx0 + cw - 7, y + 1.7, fa(n), size=5, fill="#fff", weight="bold", anchor="middle")
        tc = cx0 + (cw - 14) / 2 + 1   # وسط ناحیه متن؛ مستقل از نحوه راست‌چین‌سازی نمایشگر
        b += text(tc, y - 1.2, title, size=4.2, fill=P[k + "_d"], weight="bold", anchor="middle", extra='')
        b += text(tc, y + 4.6, sub, size=3.1, fill=P["ink"], anchor="middle")
    # بدون direction="rtl" تا در همه نمایشگرها (مرورگر، Inkscape، LibreOffice) یکسان چیده شود
    return svg_doc(W, H, b, defs).replace(' direction="rtl"', "")

def build(outdir="out"):
    return save(os.path.join(outdir, "iceberg.svg"), iceberg())

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "out")
