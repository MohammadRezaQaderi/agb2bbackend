# -*- coding: utf-8 -*-
"""
داشبورد «وضعیت شما در یک نگاه» — کارنامه ۱ باآزمون
پنج نمودار کنار هم در یک تصویر:
  هوش کلی (کتل)، سه رغبت برتر (هالند)، هوش‌های چندگانه (گاردنر)،
  حوزه‌های استعداد (کلیفتون) و نیم‌رخ شخصیت (نئو)
بدون وابستگی به کتابخانه خارجی؛ خروجی یک رشته SVG است.

استفاده:
    from glance_chart import render_glance_chart
    svg = render_glance_chart({
        "iq": {"score": 112, "label": "قوی", "min": 40, "max": 170},
        "gardner": [{"name": "تصویری–فضایی", "score": 64}, ...],      # ۸ مورد، ۰ تا ۱۰۰
        "neo": [{"right": "برون‌گرایی", "left": "درون‌گرایی", "score": 62}, ...],
                # ۵ مورد؛ score بین ۰ تا ۱۰۰ و ۱۰۰ یعنی کاملاً سمت راست (قطب right)
        "holland": [{"code": "الف", "name": "اجتماعی"}, ...],          # سه رغبت برتر به ترتیب
        "clifton": [{"name": "تفکر استراتژیک", "score": 72}, ...],      # ۴ مورد
    })
تبدیل به PNG (اختیاری):  pip install cairosvg  و سپس  svg_to_png(svg, "out.png")
"""
import math
from html import escape

INK, MUTED, LINE = "#1F2340", "#6B7096", "#E4E6F0"
C = {"iq": "#1A8F87", "gardner": "#2F9E62", "neo": "#F08A24", "holland": "#7A4FD0", "clifton": "#D62839"}
NEO_COLORS = ["#2F6FD6", "#1FA463", "#F07B2E", "#E0AE00", "#E53935"]
HOL_COLORS = ["#7A4FD0", "#9C7BE0", "#BFA8EE"]
CL_COLORS = ["#2E9E5B", "#3E64C9", "#F2A900", "#7D3CBD"]


def fa(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _clamp(v):
    return max(0, min(100, v))


def _panel(s, x, y, w, h, title, color):
    s.append(f'<rect x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="34" fill="#FFFFFF" stroke="{LINE}" stroke-width="3"/>')
    s.append(f'<rect x="{_n(x + w - 18)}" y="{_n(y + 34)}" width="18" height="48" rx="9" fill="{color}"/>')
    s.append(f'<text x="{_n(x + w - 44)}" y="{_n(y + 70)}" text-anchor="end" font-size="38" font-weight="bold" fill="{INK}">{escape(title)}</text>')


def _gauge(s, cx, cy, r, d):
    lo = 40 if d.get("min") is None else d["min"]
    hi = 170 if d.get("max") is None else d["max"]
    t = (max(lo, min(hi, d.get("score", 0))) - lo) / (hi - lo)
    pt = lambda a, rr: (cx - rr * math.cos(a), cy - rr * math.sin(a))
    segs = ["#F3B3A6", "#F6D58A", "#BFE3A8", "#7CC48A", "#2E9E6B"]
    for i, col in enumerate(segs):
        p1, p2 = pt(math.pi * i / len(segs), r), pt(math.pi * (i + 1) / len(segs), r)
        s.append(f'<path d="M{_n(p1[0])},{_n(p1[1])} A{r},{r} 0 0 1 {_n(p2[0])},{_n(p2[1])}" stroke="{col}" stroke-width="54" fill="none"/>')
    tip = pt(math.pi * t, r - 10)
    s.append(f'<line x1="{_n(cx)}" y1="{_n(cy)}" x2="{_n(tip[0])}" y2="{_n(tip[1])}" stroke="{INK}" stroke-width="10" stroke-linecap="round"/>')
    s.append(f'<circle cx="{_n(cx)}" cy="{_n(cy)}" r="20" fill="{INK}"/>')
    s.append(f'<text x="{_n(cx)}" y="{_n(cy + 92)}" text-anchor="middle" font-size="76" font-weight="bold" fill="{C["iq"]}">{fa(d.get("score", 0))}</text>')
    s.append(f'<text x="{_n(cx)}" y="{_n(cy + 150)}" text-anchor="middle" font-size="36" fill="{INK}">طبقه هوشی: {escape(d.get("label", ""))}</text>')


def _radar(s, cx, cy, r, items):
    if not items:
        return
    n = len(items)
    max_s = max(d["score"] for d in items)

    def pt(i, v):
        a = -math.pi / 2 - 2 * math.pi * i / n
        return (cx + r * v / 100 * math.cos(a), cy + r * v / 100 * math.sin(a))

    fmt = lambda p: f"{_n(p[0])},{_n(p[1])}"
    for g in (25, 50, 75, 100):
        s.append(f'<polygon points="{" ".join(fmt(pt(i, g)) for i in range(n))}" fill="none" stroke="{LINE}" stroke-width="3"/>')
    for i in range(n):
        p = pt(i, 100)
        s.append(f'<line x1="{_n(cx)}" y1="{_n(cy)}" x2="{_n(p[0])}" y2="{_n(p[1])}" stroke="{LINE}" stroke-width="3"/>')
    poly = " ".join(fmt(pt(i, _clamp(d["score"]))) for i, d in enumerate(items))
    s.append(f'<polygon points="{poly}" fill="{C["gardner"]}" fill-opacity="0.28" stroke="{C["gardner"]}" stroke-width="6" stroke-linejoin="round"/>')
    for i, d in enumerate(items):
        p, l = pt(i, _clamp(d["score"])), pt(i, 126)
        top = d["score"] == max_s
        s.append(f'<circle cx="{_n(p[0])}" cy="{_n(p[1])}" r="{14 if top else 9}" fill="{"#F2B705" if top else C["gardner"]}" stroke="#fff" stroke-width="4"/>')
        bold = ' font-weight="bold"' if top else ""
        s.append(f'<text x="{_n(l[0])}" y="{_n(l[1] + 10)}" text-anchor="middle" font-size="27"{bold} fill="{INK}">{escape(d["name"])}</text>')


def render_glance_chart(data, width=1600, height=1760, font="IRAN"):
    W, H = width, height
    g = 36
    col_w = (W - g - 6) / 2
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" direction="ltr" style="direction:ltr" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{font}">',
         '<rect width="100%" height="100%" fill="#F6F7FC"/><g transform="translate(3,0)">']

    # ردیف ۱: هوش کتل (راست) و رغبت‌های برتر هالند (چپ)
    y1, h1 = 3, 557
    _panel(s, col_w + g, y1, col_w, h1, "هوش کلی (کتل)", C["iq"])
    _gauge(s, col_w + g + col_w / 2, y1 + 330, 200, data.get("iq") or {"score": 0})
    _panel(s, 0, y1, col_w, h1, "سه رغبت شغلی برتر (هالند)", C["holland"])
    for i, d in enumerate((data.get("holland") or [])[:3]):
        tw = (col_w - 120) / 3
        tx = col_w - 40 - tw * (i + 1) + 10
        ty = y1 + 140
        mx = tx + (tw - 20) / 2
        s.append(f'<rect x="{_n(tx)}" y="{ty}" width="{_n(tw - 20)}" height="330" rx="28" fill="{HOL_COLORS[i]}"/>')
        s.append(f'<text x="{_n(mx)}" y="{ty + 70}" text-anchor="middle" font-size="34" fill="#fff">{fa(i + 1)}</text>')
        s.append(f'<text x="{_n(mx)}" y="{ty + 190}" text-anchor="middle" font-size="96" font-weight="bold" fill="#fff">{escape(d["code"])}</text>')
        s.append(f'<text x="{_n(mx)}" y="{ty + 280}" text-anchor="middle" font-size="34" font-weight="bold" fill="#fff">{escape(d["name"])}</text>')

    # ردیف ۲: هوش‌های چندگانه (راست) و حوزه‌های کلیفتون (چپ)
    y2, h2 = y1 + h1 + g, 640
    _panel(s, col_w + g, y2, col_w, h2, "هوش‌های چندگانه (گاردنر)", C["gardner"])
    _radar(s, col_w + g + col_w / 2, y2 + 365, 190, data.get("gardner") or [])
    _panel(s, 0, y2, col_w, h2, "حوزه‌های استعداد (کلیفتون)", C["clifton"])
    cl = data.get("clifton") or []
    max_c = max((d["score"] for d in cl), default=None)
    for i, d in enumerate(cl):
        y = y2 + 165 + i * 118
        x0, x1 = 50, col_w - 50
        bw, c = x1 - x0, CL_COLORS[i % 4]
        top = d["score"] == max_c
        bold = ' font-weight="bold"' if top else ""
        star = "  ★" if top else ""
        s.append(f'<text x="{_n(x1)}" y="{y}" text-anchor="end" font-size="32"{bold} fill="{INK}">{escape(d["name"])}{star}</text>')
        s.append(f'<text x="{x0}" y="{y}" text-anchor="start" font-size="30" font-weight="bold" fill="{c}">{fa(round(d["score"]))}</text>')
        s.append(f'<rect x="{x0}" y="{y + 22}" width="{_n(bw)}" height="34" rx="17" fill="{c}" opacity="0.15"/>')
        w = bw * _clamp(d["score"]) / 100
        s.append(f'<rect x="{_n(x1 - w)}" y="{y + 22}" width="{_n(w)}" height="34" rx="17" fill="{c}"/>')

    # ردیف ۳: پنج عامل شخصیت نئو
    y3 = y2 + h2 + g
    h3 = H - y3 - 3
    _panel(s, 0, y3, W - 6, h3, "نیم‌رخ شخصیت (نئو)", C["neo"])
    neo = data.get("neo") or []
    row_h = (h3 - 150) / max(1, len(neo))
    for i, d in enumerate(neo):
        y = y3 + 150 + row_h * i + row_h / 2
        x0, x1, c = 330, W - 336, NEO_COLORS[i % 5]
        s.append(f'<text x="{W - 56}" y="{_n(y + 11)}" text-anchor="end" font-size="32" font-weight="bold" fill="{c}">{escape(d["right"])}</text>')
        s.append(f'<text x="50" y="{_n(y + 11)}" text-anchor="start" font-size="32" fill="{MUTED}">{escape(d["left"])}</text>')
        s.append(f'<rect x="{x0}" y="{_n(y - 9)}" width="{x1 - x0}" height="18" rx="9" fill="{LINE}"/>')
        mid = (x0 + x1) / 2
        s.append(f'<line x1="{_n(mid)}" x2="{_n(mid)}" y1="{_n(y - 22)}" y2="{_n(y + 22)}" stroke="#C5C9DD" stroke-width="3"/>')
        px = x0 + (x1 - x0) * _clamp(d["score"]) / 100
        s.append(f'<circle cx="{_n(px)}" cy="{_n(y)}" r="24" fill="{c}" stroke="#fff" stroke-width="6"/>')
    s.append("</g></svg>")
    return "".join(s)


def svg_to_png(svg, path):
    import cairosvg  # pip install cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path)


SAMPLE = {
    "iq": {"score": 112, "label": "قوی", "min": 40, "max": 170},
    "gardner": [{"name": n, "score": v} for n, v in [
        ("تصویری–فضایی", 64), ("کلامی–زبانی", 72), ("منطقی–ریاضی", 58), ("جسمی–حرکتی", 45),
        ("موسیقایی", 50), ("بین‌فردی", 80), ("درون‌فردی", 68), ("طبیعت‌گرا", 40)]],
    "neo": [{"right": r, "left": l, "score": v} for r, l, v in [
        ("برون‌گرایی", "درون‌گرایی", 62), ("سازشگری", "خودمحوری", 70), ("روان‌رنجوری", "ثبات هیجانی", 38),
        ("گشودگی به تجربه", "محافظه‌کاری", 75), ("مسئولیت‌پذیری", "تنوع‌طلبی", 55)]],
    "holland": [{"code": "الف", "name": "اجتماعی"}, {"code": "ج", "name": "جستجوگری"}, {"code": "هـ", "name": "هنری"}],
    "clifton": [{"name": n, "score": v} for n, v in [
        ("تفکر استراتژیک", 72), ("ساخت روابط", 58), ("نفوذ و تأثیرگذاری", 40), ("اجرایی", 66)]],
}

if __name__ == "__main__":
    with open("glance_chart.svg", "w", encoding="utf-8") as f:
        f.write(render_glance_chart(SAMPLE))
    print("glance_chart.svg ساخته شد")
