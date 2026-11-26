# -*- coding: utf-8 -*-
"""نوار راهنمای چهار سطح وضعیت + چهره‌های سطح (برای عواملی که تصویر کارتونی ندارند).
اجرا: python fig_levels.py out
"""
try:  # Package import in the SCL renderer; standalone compatibility for source users.
    from .svgkit import PALETTE as P, LEVELS, svg_doc, text, save, fa
except ImportError:  # pragma: no cover - standalone script invocation
    from svgkit import PALETTE as P, LEVELS, svg_doc, text, save, fa
import os, sys

def level_scale(w=170, h=16):
    """نوار گرادیانی چهار سطح، از راست (نرمال) به چپ (شدید)."""
    seg = w / 4
    body = ""
    for i, (name, key) in enumerate(LEVELS):
        x = w - (i + 1) * seg
        r = 'rx="4"' if i in (0, 3) else ""
        body += f'<rect x="{x+0.6}" y="2" width="{seg-1.2}" height="{h-4}" rx="3" fill="{P[key]}"/>'
        body += text(x + seg/2, h/2 + 1.6, f"{fa(i+1)} · {name}", size=4.4, fill="#fff", weight="bold", anchor="middle")
    return svg_doc(w, h, body)

def face(level, size=30):
    """چهره ساده: ۱=خندان ... ۴=ناراحت."""
    key = LEVELS[level-1][1]
    curve = {1: 10, 2: 4, 3: -3, 4: -9}[level]
    brow = {1: "", 2: "", 3: '<path d="M30 36 l10 -3 M70 36 l-10 -3" stroke="#fff" stroke-width="4" stroke-linecap="round"/>',
            4: '<path d="M30 33 l11 5 M70 33 l-11 5" stroke="#fff" stroke-width="4" stroke-linecap="round"/>'}[level]
    body = (f'<g transform="scale({size/100})"><circle cx="50" cy="50" r="46" fill="{P[key]}"/>'
            f'<circle cx="36" cy="44" r="5" fill="#fff"/><circle cx="64" cy="44" r="5" fill="#fff"/>{brow}'
            f'<path d="M32 66 Q50 {66+curve*1.6} 68 66" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/></g>')
    return svg_doc(size, size, body)

def build(outdir="out"):
    save(os.path.join(outdir, "level_scale.svg"), level_scale())
    for i in range(1, 5):
        save(os.path.join(outdir, f"face_{i}.svg"), face(i))

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "out")

def arrow_up(w=12, h=10, color="#9CA3AF"):
    body = f'<path d="M{w/2} 1 L{w-1.5} {h*0.55} H{w*0.66} V{h-1} H{w*0.34} V{h*0.55} H1.5 Z" fill="{color}"/>'
    return svg_doc(w, h, body)

if __name__ == "__main__":
    save(os.path.join(sys.argv[1] if len(sys.argv) > 1 else "out", "arrow_up.svg"), arrow_up())
