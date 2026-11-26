# -*- coding: utf-8 -*-
"""ابزار مشترک ساخت تصاویر SVG کارنامه دوپامین (باآزمون).
همه متن‌ها با فونت IRAN نوشته می‌شوند؛ برای نمایش درست، فونت IRAN و IRAN Bold
باید روی سیستم نصب باشد. خروجی SVG را می‌توان با Inkscape به PNG تبدیل کرد:
    inkscape file.svg --export-type=png --export-dpi=200
"""
import os
FONT = "IRAN"

PALETTE = {
    "navy": "#1F2A44", "ink": "#2B2F3A", "muted": "#6B7280", "line": "#E5E7EB",
    "brand": "#D7262E", "bg": "#F7F8FB",
    # دسته‌ها
    "surface": "#F08A24", "surface_l": "#FFF3E6", "surface_d": "#B35F0E",
    "psych": "#7B4FC9", "psych_l": "#F3EEFC", "psych_d": "#56339A",
    "root": "#13908F", "root_l": "#E4F5F4", "root_d": "#0B6564",
    # سطوح
    "lv1": "#3BB273", "lv2": "#F2C14E", "lv3": "#F28C38", "lv4": "#E04848",
}
LEVELS = [("نرمال", "lv1"), ("خفیف", "lv2"), ("متوسط", "lv3"), ("شدید", "lv4")]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def fa(n):
    return str(n).translate(FA_DIGITS)

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))

def svg_doc(w_mm, h_mm, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w_mm}mm" height="{h_mm}mm" viewBox="0 0 {w_mm} {h_mm}" direction="ltr" style="direction:ltr">'
            f'<defs>{defs}</defs>{body}</svg>')

def text(x, y, s, size=4, fill="#000", weight="normal", anchor="end", extra=""):
    """متن فارسی راست‌چین که در همه نمایشگرها (مرورگر، Inkscape، LibreOffice) یکسان دیده می‌شود.
    anchor='end'  : لبه راست متن روی x قرار می‌گیرد (راست‌چین)
    anchor='start': لبه چپ متن روی x قرار می‌گیرد
    anchor='middle': وسط متن روی x
    از ویژگی direction="rtl" استفاده نمی‌شود (برخی نمایشگرها با آن، لبه شروع/پایان را برعکس می‌کنند)؛
    به‌جای آن متن داخل نویسه‌های کنترلی RLE...PDF قرار می‌گیرد تا ترتیب کلمات، اعداد و علامت‌ها
    راست‌به‌چپ بماند."""
    w = "bold" if weight == "bold" else "normal"
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>\u202b{esc(s)}\u202c</text>')

def save(path, svg):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path
