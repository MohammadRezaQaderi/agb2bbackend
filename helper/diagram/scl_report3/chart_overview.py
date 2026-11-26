# -*- coding: utf-8 -*-
"""نمودار «وضعیت ۱۶ عامل» — نمودار پویا برای هر دانش‌آموز.

هر عامل یک ردیف دارد: نام عامل، یک خط‌کش چهاربخشی (نرمال، خفیف، متوسط، شدید)،
نوار نمره که از راست شروع می‌شود و برچسب سطح و نمره در انتهای ردیف.

ورودی JSON:
    {"addict": {"score": 42, "level": 2}, "sleep": {"score": 61, "level": 3}, ...}
    level: ۱=نرمال، ۲=خفیف، ۳=متوسط، ۴=شدید   |   score: نمره (بازه با --max)
کلیدها: addict body sleep mobile future study anx dep ocd mot conf adhd family inter ideal truma

اجرا:
    python chart_overview.py scores.json overview_chart.svg --max 100
    python chart_overview.py --demo overview_chart.svg      (خط‌کش‌ها بدون نمره، برای قالب)
    python chart_overview.py scores.json chart.html --html  (صفحه HTML؛ فونت IRAN باید نصب یا کنار فایل باشد)

نکته فنی: متن‌ها با text-anchor و نویسه‌های RLE/PDF راست‌چین می‌شوند (نه direction="rtl")
تا در مرورگرها، Inkscape و LibreOffice یکسان و داخل کادر نمایش داده شوند.
در قالب ODT این تصویر با نام overview_chart (Pictures/overview_chart.svg) قرار دارد.
"""
try:  # Package import in the SCL renderer; standalone compatibility for source users.
    from .svgkit import PALETTE as P, LEVELS, svg_doc, text, save, fa
except ImportError:  # pragma: no cover - standalone script invocation
    from svgkit import PALETTE as P, LEVELS, svg_doc, text, save, fa
import json, argparse, math

FACTORS = [
    ("surface", "عوامل سطحی", [("addict", "ضعف روانی"), ("body", "مشکلات جسمی"), ("sleep", "مشکلات خواب"),
                               ("mobile", "وابستگی به موبایل و بازی"), ("future", "ابهام در آینده"), ("study", "مهارت‌های مطالعاتی")]),
    ("psych", "عوامل روان‌شناختی", [("anx", "اضطراب"), ("dep", "افسردگی"), ("ocd", "وسواس"),
                                     ("mot", "بی‌انگیزگی"), ("conf", "اعتماد به نفس پایین")]),
    ("root", "عوامل بنیادین", [("adhd", "بیش‌فعالی و عدم تمرکز"), ("family", "مشکلات خانوادگی"),
                                ("inter", "مشکلات بین‌فردی"), ("ideal", "کمال‌گرایی"), ("truma", "ترومای جنگ و کودکی")]),
]
PALE = {"lv1": "#E3F4EA", "lv2": "#FCF2D6", "lv3": "#FDE6D3", "lv4": "#FADADA"}

W = 180
LABEL_R, LABEL_W = 177, 46          # ستون نام عامل (راست)
TR_R, TR_L = 128, 34                # خط‌کش: از راست به چپ
BADGE_X, BADGE_W = 3, 28            # برچسب سطح (چپ)
ROW, HEAD = 8.2, 8.5

def chart(data=None, vmax=100, thresholds=None):
    """thresholds: مرز سطح‌ها به‌صورت کسری از vmax (پیش‌فرض: چهار بخش مساوی)."""
    th = thresholds or [0.25, 0.5, 0.75]
    span = TR_R - TR_L
    cuts = [0] + th + [1]
    b, y = "", 2
    # سرستون سطح‌ها
    for i, (name, k) in enumerate(LEVELS):
        x0 = TR_R - span * cuts[i]; x1 = TR_R - span * cuts[i + 1]
        b += text((x0 + x1) / 2, y + 4.2, name, size=3.2, fill=P[k], weight="bold", anchor="middle")
    b += text(LABEL_R, y + 4.2, "عامل", size=3.2, fill=P["muted"], weight="bold")
    b += text(BADGE_X + BADGE_W / 2, y + 4.2, "وضعیت و نمره", size=3.2, fill=P["muted"], weight="bold", anchor="middle")
    y += 8
    for cat, cname, items in FACTORS:
        b += f'<rect x="0" y="{y}" width="{W}" height="{HEAD-1.5}" rx="2.5" fill="{P[cat+"_l"]}"/>'
        b += f'<rect x="{W-2.5}" y="{y}" width="2.5" height="{HEAD-1.5}" rx="1.2" fill="{P[cat]}"/>'
        b += text(W - 5.5, y + 4.7, cname, size=3.6, fill=P[cat + "_d"], weight="bold")
        y += HEAD
        for j, (key, name) in enumerate(items):
            cy = y + ROW / 2
            if j % 2 == 1:
                b += f'<rect x="0" y="{y}" width="{W}" height="{ROW}" fill="#F7F8FB"/>'
            b += text(LABEL_R, cy + 1.2, name, size=3.2, fill=P["ink"])
            # خط‌کش چهاربخشی کم‌رنگ
            for i, (_, k) in enumerate(LEVELS):
                x0 = TR_R - span * cuts[i + 1]; w = span * (cuts[i + 1] - cuts[i])
                b += f'<rect x="{x0+0.3}" y="{cy-2}" width="{w-0.6}" height="4" rx="1.5" fill="{PALE[k]}"/>'
            if data and key in data:
                sc = max(0.0, min(float(data[key].get("score", 0)), vmax))
                lv = max(1, min(int(data[key].get("level", 1)), 4))
                col = P[LEVELS[lv - 1][1]]
                L = max(span * sc / vmax, 2.5)
                b += f'<rect x="{TR_R-L}" y="{cy-2}" width="{L}" height="4" rx="2" fill="{col}"/>'
                b += f'<circle cx="{TR_R-L}" cy="{cy}" r="2.6" fill="#fff" stroke="{col}" stroke-width="1.2"/>'
                b += f'<rect x="{BADGE_X}" y="{cy-2.8}" width="{BADGE_W}" height="5.6" rx="2.8" fill="{col}"/>'
                # نام سطح و نمره به‌صورت دو متن جدا (بدون ترکیب عدد و حروف در یک خط) تا در همه نمایشگرها درست چیده شود
                b += text(BADGE_X + BADGE_W * 0.66, cy + 1.1, LEVELS[lv-1][0], size=3, fill="#fff", weight="bold", anchor="middle")
                b += f'<line x1="{BADGE_X + BADGE_W*0.36}" y1="{cy-1.8}" x2="{BADGE_X + BADGE_W*0.36}" y2="{cy+1.8}" stroke="#fff" stroke-width="0.35" opacity="0.8"/>'
                score_label = f"{sc:.1f}".rstrip("0").rstrip(".").replace(".", "٫")
                b += text(BADGE_X + BADGE_W * 0.18, cy + 1.1, fa(score_label), size=3, fill="#fff", weight="bold", anchor="middle")
            else:
                b += f'<rect x="{BADGE_X}" y="{cy-2.8}" width="{BADGE_W}" height="5.6" rx="2.8" fill="none" stroke="#D1D5DB" stroke-width="0.4"/>'
            y += ROW
        y += 2.5
    return svg_doc(W, round(y, 1), b)

HTML_TMPL = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>نمودار وضعیت شانزده عامل</title>
<style>
  @font-face { font-family: "IRAN"; src: local("IRAN"), url("IRAN.ttf") format("truetype"); font-weight: normal; }
  @font-face { font-family: "IRAN"; src: local("IRAN Bold"), local("IRAN-Bold"), url("IRAN_Bold.ttf") format("truetype"); font-weight: bold; }
  body { margin: 0; padding: 24px; background: #F7F8FB; font-family: "IRAN", sans-serif; color: #2B2F3A; }
  .card { max-width: 900px; margin: 0 auto; background: #fff; border-radius: 16px; padding: 20px 24px; box-shadow: 0 2px 12px rgba(31,42,68,.08); }
  h1 { font-size: 20px; margin: 0 0 6px; color: #1F2A44; }
  p { font-size: 13px; color: #6B7280; margin: 0 0 16px; }
  svg { width: 100%; height: auto; display: block; direction: ltr; }
</style>
</head>
<body>
<div class="card">
  <h1>نمودار وضعیت شانزده عامل</h1>
  <p>طول هر نوار نمره و رنگش سطح وضعیت را نشان می‌دهد.</p>
  __SVG__
</div>
</body>
</html>
"""

def html(data=None, vmax=100, thresholds=None):
    svg = chart(data, vmax, thresholds)
    svg = svg.replace('width="180mm"', 'width="180"', 1)
    svg = svg.split('height="', 1)[0] + svg.split('height="', 1)[1].split('"', 1)[1]  # حذف ارتفاع ثابت
    return HTML_TMPL.replace("__SVG__", svg)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inp", nargs="?")
    ap.add_argument("out", nargs="?", default="overview_chart.svg")
    ap.add_argument("--max", type=float, default=100)
    ap.add_argument("--demo", action="store_true", help="خط‌کش خالی بدون نمره (برای قالب)")
    ap.add_argument("--html", action="store_true", help="خروجی صفحه HTML به‌جای SVG")
    a = ap.parse_args()
    if a.demo:
        data, out = None, (a.inp or a.out)
    else:
        data, out = json.load(open(a.inp, encoding="utf-8")), a.out
    save(out, html(data, a.max) if a.html else chart(data, a.max))
