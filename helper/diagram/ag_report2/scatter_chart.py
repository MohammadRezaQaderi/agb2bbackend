# -*- coding: utf-8 -*-
"""
نمودار پراکندگی رشته‌ها — کارنامه ۲ باآزمون (بازطراحی)
هر دایره یک رشته است: ستون = شاخه تحصیلی، ارتفاع = میزان انطباق، اندازه = میزان استقبال.
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده:
    from scatter_chart import render_scatter_chart, BRANCHES
    svg = render_scatter_chart(
        [{"branch": "ریاضی و فیزیک", "name": "مهندسی برق", "fit": 82, "popularity": 70}, ...],
        branches=BRANCHES,      # ترتیب و رنگ شاخه‌ها (از راست به چپ)
        threshold=50,           # خط مرز تناسب
        label_top=4)            # نام N رشته برتر روی نمودار نوشته شود
    fit و popularity عدد ۰ تا ۱۰۰ هستند.
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
import hashlib
from html import escape

INK, MUTED, GRID = "#1F2340", "#7A7FA3", "#E8EAF3"
BRANCHES = [("ریاضی و فیزیک", "#E8505B"), ("علوم تجربی", "#E39B00"), ("علوم انسانی", "#9DB000"),
            ("گروه هنر", "#1FA463"), ("گروه کشاورزی", "#0FA3C9"), ("گروه مدیریت و خدمات", "#2F6FD6"), ("گروه صنعت", "#8456C9")]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _jit(key):
    h = hashlib.md5(key.encode("utf-8")).digest()
    return (h[0] / 255) * 2 - 1


def render_scatter_chart(items, branches=None, threshold=50, label_top=4, width=1600, height=1100, font="IRAN"):
    branches = branches or BRANCHES
    W, H = width, height
    left, right, top, bottom = 110, W - 40, 70, H - 170
    n = len(branches)
    col_w = (right - left) / n
    y = lambda v: bottom - (bottom - top) * max(0, min(100, v)) / 100
    bidx = {b[0]: i for i, b in enumerate(branches)}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">', '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for i, (name, col) in enumerate(branches):
        x0 = right - col_w * (i + 1)
        s.append(f'<rect x="{_n(x0 + 4)}" y="{top}" width="{_n(col_w - 8)}" height="{bottom - top}" rx="22" fill="{col}" opacity="{0.06 if i % 2 == 0 else 0.10}"/>')
        words = name.split(" ")
        lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else [name]
        for k, ln in enumerate(lines):
            s.append(f'<text x="{_n(x0 + col_w / 2)}" y="{bottom + 50 + k * 34}" text-anchor="middle" font-size="27" font-weight="bold" fill="{col}">{escape(ln)}</text>')
    for g in range(0, 101, 20):
        s.append(f'<line x1="{left}" x2="{right}" y1="{_n(y(g))}" y2="{_n(y(g))}" stroke="{GRID}" stroke-width="2"/>')
        s.append(f'<text x="{left - 18}" y="{_n(y(g) + 8)}" text-anchor="end" font-size="24" fill="{MUTED}">{fa(g)}</text>')
    s.append(f'<text x="40" y="{_n((top + bottom) / 2)}" text-anchor="middle" font-size="26" fill="{MUTED}" transform="rotate(-90 40 {_n((top + bottom) / 2)})">میزان انطباق با شما</text>')
    ty = y(threshold)
    s.append(f'<line x1="{left}" x2="{right}" y1="{_n(ty)}" y2="{_n(ty)}" stroke="{INK}" stroke-width="3" stroke-dasharray="10 10" opacity="0.5"/>')
    s.append(f'<rect x="{left + 8}" y="{_n(ty - 44)}" width="150" height="36" rx="18" fill="#FFFFFF" stroke="#C5C9DD" stroke-width="2"/>')
    s.append(f'<text x="{left + 83}" y="{_n(ty - 18)}" text-anchor="middle" font-size="22" fill="{MUTED}">مرز تناسب</text>')
    pts = []
    for d in items:
        if d["branch"] not in bidx:
            continue
        i = bidx[d["branch"]]
        col = branches[i][1]
        cx = right - col_w * i - col_w / 2 + _jit(d["name"] + d["branch"]) * col_w * 0.33
        cy = y(d["fit"])
        rr = 10 + 26 * max(0, min(100, d.get("popularity", 50))) / 100
        pts.append((rr, cx, cy, col, d))
    for rr, cx, cy, col, d in sorted(pts, key=lambda p: -p[0]):
        s.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(rr)}" fill="{col}" fill-opacity="0.45" stroke="{col}" stroke-width="3"/>')
    placed = []
    def _free(r):
        return all(r[2] < q[0] or r[0] > q[2] or r[3] < q[1] or r[1] > q[3] for q in placed)
    for rr, cx, cy, col, d in sorted(pts, key=lambda p: -p[4]["fit"])[:label_top]:
        w, h = 30 + 17 * len(d["name"]), 40
        cands = [(cx, cy - rr - 12 - h / 2), (cx, cy + rr + 12 + h / 2),
                 (cx - rr - 12 - w / 2, cy), (cx + rr + 12 + w / 2, cy),
                 (cx, cy - rr - 60 - h / 2), (cx, cy + rr + 60 + h / 2)]
        for lx, ly in cands:
            lx = min(max(lx, left + w / 2 + 4), right - w / 2 - 4)
            ly = min(max(ly, top + h / 2), bottom - h / 2)
            box = (lx - w / 2, ly - h / 2, lx + w / 2, ly + h / 2)
            if _free(box):
                placed.append(box)
                s.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="{_n(rr)}" fill="{col}" stroke="#FFFFFF" stroke-width="4"/>')
                s.append(f'<line x1="{_n(cx)}" y1="{_n(cy)}" x2="{_n(lx)}" y2="{_n(ly)}" stroke="{INK}" stroke-width="2" opacity="0.5"/>')
                s.append(f'<rect x="{_n(box[0])}" y="{_n(box[1])}" width="{_n(w)}" height="{h}" rx="20" fill="{INK}" opacity="0.9"/>')
                s.append(f'<text x="{_n(lx)}" y="{_n(ly + 8)}" text-anchor="middle" font-size="22" fill="#FFFFFF">{escape(d["name"])}</text>')
                break
    s.append(f'<text x="{right}" y="{H - 24}" text-anchor="end" font-size="22" fill="{MUTED}">اندازه هر دایره = میزان استقبال دانش‌آموزان از آن رشته</text>')
    s.append("</svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


def _sample():
    names = {
        "ریاضی و فیزیک": ["مهندسی برق", "مهندسی کامپیوتر", "مهندسی مکانیک", "مهندسی عمران", "معماری", "فیزیک", "ریاضی", "مهندسی صنایع", "مهندسی شیمی", "آمار", "هوافضا", "مهندسی مواد"],
        "علوم تجربی": ["پزشکی", "دندان‌پزشکی", "داروسازی", "پرستاری", "زیست‌شناسی", "علوم آزمایشگاهی", "فیزیوتراپی", "مامایی", "تغذیه", "دامپزشکی", "بینایی‌سنجی"],
        "علوم انسانی": ["حقوق", "روان‌شناسی", "مدیریت", "حسابداری", "علوم تربیتی", "ادبیات فارسی", "علوم سیاسی", "اقتصاد", "جامعه‌شناسی", "زبان‌شناسی"],
        "گروه هنر": ["گرافیک", "عکاسی", "نقاشی", "موسیقی", "صنایع دستی", "طلا و جواهر", "خیاطی", "انیمیشن"],
        "گروه کشاورزی": ["امور زراعی", "امور باغی", "امور دامی", "صنایع غذایی", "ماشین‌های کشاورزی", "پرورش آبزیان"],
        "گروه مدیریت و خدمات": ["حسابداری فنی", "امور اداری", "بازاریابی", "گردشگری", "هتلداری", "تربیت کودک", "کامپیوتر"],
        "گروه صنعت": ["الکترونیک", "الکتروتکنیک", "مکانیک خودرو", "ساختمان", "صنایع فلزی", "صنایع چوب", "مکاترونیک", "نقشه‌کشی"],
    }
    out = []
    for bi, (b, _) in enumerate(BRANCHES):
        for k, nm in enumerate(names[b]):
            h = hashlib.md5((b + nm).encode()).digest()
            base = [70, 62, 48, 38, 30, 44, 55][bi]
            out.append({"branch": b, "name": nm, "fit": max(3, min(97, base + (h[1] / 255 - 0.5) * 60)), "popularity": h[2] / 255 * 100})
    return out


SAMPLE = _sample()
SAMPLES = [("نمودار پراکندگی رشته‌ها (کارنامه ۲)", lambda: render_scatter_chart(SAMPLE))]

if __name__ == "__main__":
    with open("scatter_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_scatter_chart(SAMPLE))
    print("scatter_chart.svg ساخته شد")
