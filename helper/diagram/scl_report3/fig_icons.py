# -*- coding: utf-8 -*-
"""آیکون‌های ۱۶ عامل کارنامه (طرح خطی سفید روی دایره رنگی).
اجرا:  python fig_icons.py  ->  خروجی در پوشه out/icons
"""
try:  # Package import in the SCL renderer; standalone compatibility for source users.
    from .svgkit import PALETTE as P, svg_doc, save
except ImportError:  # pragma: no cover - standalone script invocation
    from svgkit import PALETTE as P, svg_doc, save
import os, sys

S = 'fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
F = 'fill="#fff"'

ICONS = {
 # خواب: ماه و ستاره
 "sleep": f'<path d="M58 22 A30 30 0 1 0 80 64 A24 24 0 1 1 58 22Z" {S}/><circle cx="72" cy="30" r="3" {F}/><circle cx="82" cy="44" r="2" {F}/>',
 # موبایل
 "mobile": f'<rect x="34" y="20" width="32" height="60" rx="6" {S}/><line x1="45" y1="70" x2="55" y2="70" {S}/><path d="M70 30 q8 8 0 16 M76 24 q14 14 0 28" {S}/>',
 # جسم: قلب با نوار ضربان
 "body": f'<path d="M50 80 C20 60 18 38 32 30 C42 25 48 32 50 36 C52 32 58 25 68 30 C82 38 80 60 50 80Z" {S}/><polyline points="26,52 40,52 45,42 52,62 57,50 74,50" {S}/>',
 # آینده: قطب‌نما
 "future": f'<circle cx="50" cy="50" r="28" {S}/><polygon points="50,30 58,50 50,70 42,50" {S}/><circle cx="50" cy="50" r="3" {F}/>',
 # مطالعه: کتاب باز
 "study": f'<path d="M20 30 Q35 24 50 32 Q65 24 80 30 L80 72 Q65 66 50 74 Q35 66 20 72Z" {S}/><line x1="50" y1="32" x2="50" y2="74" {S}/>',
 # ضعف روانی: سپر با علامت هشدار
 "addict": f'<path d="M50 18 L76 28 L76 50 C76 66 64 76 50 82 C36 76 24 66 24 50 L24 28Z" {S}/><line x1="50" y1="36" x2="50" y2="54" {S}/><circle cx="50" cy="64" r="3.5" {F}/>',
 # اضطراب: ابر و صاعقه
 "anx": f'<path d="M30 58 a12 12 0 0 1 2 -24 a16 16 0 0 1 30 -4 a12 12 0 0 1 8 28Z" {S}/><polyline points="52,58 44,72 54,72 46,86" {S}/>',
 # افسردگی: ابر و باران
 "dep": f'<path d="M30 56 a12 12 0 0 1 2 -24 a16 16 0 0 1 30 -4 a12 12 0 0 1 8 28Z" {S}/><line x1="38" y1="66" x2="35" y2="76" {S}/><line x1="50" y1="66" x2="47" y2="80" {S}/><line x1="62" y1="66" x2="59" y2="76" {S}/>',
 # وسواس: پیکان‌های چرخشی
 "ocd": f'<path d="M72 44 A24 24 0 0 0 30 38" {S}/><polyline points="28,26 30,38 42,36" {S}/><path d="M28 56 A24 24 0 0 0 70 62" {S}/><polyline points="72,74 70,62 58,64" {S}/>',
 # بی‌انگیزگی: باتری کم
 "mot": f'<rect x="22" y="36" width="50" height="28" rx="5" {S}/><line x1="78" y1="45" x2="78" y2="55" {S}/><rect x="29" y="43" width="10" height="14" rx="2" {F}/>',
 # اعتماد به نفس: ستاره
 "conf": f'<polygon points="50,20 58,40 80,41 63,54 69,76 50,64 31,76 37,54 20,41 42,40" {S}/>',
 # بیش‌فعالی: خط زیگزاگ بی‌قراری
 "adhd": f'<polyline points="18,60 30,38 42,62 54,38 66,62 80,40" {S}/><circle cx="30" cy="74" r="3.5" {F}/><circle cx="54" cy="24" r="3.5" {F}/><circle cx="74" cy="72" r="3.5" {F}/>',
 # خانواده: خانه و قلب
 "family": f'<polyline points="20,50 50,24 80,50" {S}/><path d="M28 46 L28 78 L72 78 L72 46" {S}/><path d="M50 70 C40 63 39 55 44 52 C47 50 49 52 50 54 C51 52 53 50 56 52 C61 55 60 63 50 70Z" {F}/>',
 # بین‌فردی: دو نفر
 "inter": f'<circle cx="36" cy="38" r="9" {S}/><circle cx="64" cy="38" r="9" {S}/><path d="M20 76 a16 16 0 0 1 32 0" {S}/><path d="M48 76 a16 16 0 0 1 32 0" {S}/>',
 # کمال‌گرایی: هدف و پیکان
 "ideal": f'<circle cx="46" cy="54" r="26" {S}/><circle cx="46" cy="54" r="14" {S}/><circle cx="46" cy="54" r="3" {F}/><line x1="46" y1="54" x2="76" y2="24" {S}/><polyline points="66,22 76,24 78,34" {S}/>',
 # تروما: قلب با چسب زخم
 "truma": f'<path d="M50 80 C20 60 18 38 32 30 C42 25 48 32 50 36 C52 32 58 25 68 30 C82 38 80 60 50 80Z" {S}/><rect x="30" y="47" width="40" height="13" rx="6" transform="rotate(-30 50 53)" {S}/>',
 # آیکون‌های دسته
 "cat_surface": f'<path d="M18 66 L40 40 L52 54 L64 34 L82 66Z" {S}/><path d="M14 74 q9 -6 18 0 t18 0 t18 0 t18 0" {S}/>',
 "cat_psych": f'<path d="M50 22 C34 22 26 34 28 46 C22 50 24 60 32 62 C32 72 42 78 50 74 C58 78 68 72 68 62 C76 60 78 50 72 46 C74 34 66 22 50 22Z" {S}/><line x1="50" y1="26" x2="50" y2="72" {S}/>',
 "cat_root": f'<line x1="50" y1="20" x2="50" y2="52" {S}/><path d="M50 52 C46 64 34 68 26 80 M50 52 C54 64 66 68 74 80 M50 52 L50 82" {S}/><path d="M38 34 q12 -10 24 0" {S}/>',
}

CAT_OF = {"addict":"surface","body":"surface","sleep":"surface","mobile":"surface","future":"surface","study":"surface",
          "anx":"psych","dep":"psych","ocd":"psych","mot":"psych","conf":"psych",
          "adhd":"root","family":"root","inter":"root","ideal":"root","truma":"root",
          "cat_surface":"surface","cat_psych":"psych","cat_root":"root"}

def icon_group(key, color=None):
    c = color or P[CAT_OF[key]]
    return f'<circle cx="50" cy="50" r="48" fill="{c}"/>{ICONS[key]}'

def icon_svg(key, size_mm=20, color=None):
    body = f'<g transform="scale({size_mm/100})">{icon_group(key, color)}</g>'
    return svg_doc(size_mm, size_mm, body)

def build(outdir="out/icons"):
    paths = {}
    for k in ICONS:
        paths[k] = save(os.path.join(outdir, f"icon_{k}.svg"), icon_svg(k))
    return paths

if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "out/icons")
