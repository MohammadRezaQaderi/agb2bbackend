from quiz_packages.psy.generated_manifest import PACKAGE_NAMES as PSY_PACKAGE_NAMES


AG_QUIZ_NAME_TITLE = [
    "کتل", "گاردنر", "نئو", "کلیفتون", "هالند",
    "تعهد‌", "پرسشنامه"
]

SCL_QUIZ_NAME_TITLE = [
    "زندگی شخصی", "زندگی روانشناختی", "زندگی تحصیلی", "زندگی اجتماعی"
]

PSY_PACKAGE_TITLES = {
    "PSY_ANX": "اضطراب",
    "PSY_DEP": "افسردگی",
    "PSY_INTERNET": "وابستگی به اینترنت",
    "PSY_MBTI": "تیپ‌شناسی MBTI",
    "PSY_MOTIVATION": "انگیزش تحصیلی",
    "PSY_NEEDS": "نیازهای اساسی",
    "PSY_SOCIAL": "مهارت‌های اجتماعی",
    "PSY_NEO": "شخصیت‌شناسی نئو",
    "PSY_COPING_STRATEGIES": "راهبردهای مقابله‌ای",
    "PSY_OCD": "وسواس و کمال‌گرایی",
    "PSY_EQ_IQ": "هوش هیجانی و ریون",
    "PSY_GARDNER": "هوش‌های چندگانه گاردنر",
    "PSY_SCL90": "علائم روانی SCL-90",
    "PSY_STUDY_SKILLS": "مهارت‌های مطالعه",
}

PSY_PACKAGE_DESCRIPTIONS = {
    "PSY_ANX": "سنجش نشانه‌های اضطراب",
    "PSY_DEP": "سنجش نشانه‌های افسردگی",
    "PSY_INTERNET": "بررسی الگوی استفاده از اینترنت",
    "PSY_MBTI": "شناخت ترجیحات شخصیتی",
    "PSY_MOTIVATION": "بررسی انگیزه‌های تحصیلی",
    "PSY_NEEDS": "ارزیابی نیازهای روان‌شناختی",
    "PSY_SOCIAL": "سنجش مهارت‌های ارتباطی و اجتماعی",
    "PSY_NEO": "ارزیابی پنج عامل شخصیت",
    "PSY_COPING_STRATEGIES": "بررسی شیوه‌های مواجهه با فشار",
    "PSY_OCD": "سنجش نشانه‌های وسواس و کمال‌گرایی",
    "PSY_EQ_IQ": "ارزیابی هوش هیجانی و توانایی شناختی",
    "PSY_GARDNER": "شناخت الگوی هوش‌های چندگانه",
    "PSY_SCL90": "غربالگری علائم روان‌شناختی",
    "PSY_STUDY_SKILLS": "ارزیابی عادت‌ها و مهارت‌های مطالعه",
}


PACKAGES_DATA = {
    "AG": {
        10: 1600000,
        20: 2900000,
        50: 5800000,
        100: 9600000,
        101: 99999999
    },
    "SCL": {
        10: 1600000,
        20: 2900000,
        50: 5800000,
        100: 9600000,
        101: 99999999
    },
    **{package_name: {} for package_name in PSY_PACKAGE_NAMES},
}

PROVINCES = [
    {
        "id": 1,
        "name": "آذربایجان شرقی",
        "slug": "آذربایجان-شرقی"
    },
    {
        "id": 2,
        "name": "آذربایجان غربی",
        "slug": "آذربایجان-غربی"
    },
    {
        "id": 3,
        "name": "اردبیل",
        "slug": "اردبیل"
    },
    {
        "id": 4,
        "name": "اصفهان",
        "slug": "اصفهان"
    },
    {
        "id": 5,
        "name": "البرز",
        "slug": "البرز"
    },
    {
        "id": 6,
        "name": "ایلام",
        "slug": "ایلام"
    },
    {
        "id": 7,
        "name": "بوشهر",
        "slug": "بوشهر"
    },
    {
        "id": 8,
        "name": "تهران",
        "slug": "تهران"
    },
    {
        "id": 9,
        "name": "چهارمحال و بختیاری",
        "slug": "چهارمحال-بختیاری"
    },
    {
        "id": 10,
        "name": "خراسان جنوبی",
        "slug": "خراسان-جنوبی"
    },
    {
        "id": 11,
        "name": "خراسان رضوی",
        "slug": "خراسان-رضوی"
    },
    {
        "id": 12,
        "name": "خراسان شمالی",
        "slug": "خراسان-شمالی"
    },
    {
        "id": 13,
        "name": "خوزستان",
        "slug": "خوزستان"
    },
    {
        "id": 14,
        "name": "زنجان",
        "slug": "زنجان"
    },
    {
        "id": 15,
        "name": "سمنان",
        "slug": "سمنان"
    },
    {
        "id": 16,
        "name": "سیستان و بلوچستان",
        "slug": "سیستان-بلوچستان"
    },
    {
        "id": 17,
        "name": "فارس",
        "slug": "فارس"
    },
    {
        "id": 18,
        "name": "قزوین",
        "slug": "قزوین"
    },
    {
        "id": 19,
        "name": "قم",
        "slug": "قم"
    },
    {
        "id": 20,
        "name": "کردستان",
        "slug": "کردستان"
    },
    {
        "id": 21,
        "name": "کرمان",
        "slug": "کرمان"
    },
    {
        "id": 22,
        "name": "کرمانشاه",
        "slug": "کرمانشاه"
    },
    {
        "id": 23,
        "name": "کهگیلویه و بویراحمد",
        "slug": "کهگیلویه-بویراحمد"
    },
    {
        "id": 24,
        "name": "گلستان",
        "slug": "گلستان"
    },
    {
        "id": 25,
        "name": "لرستان",
        "slug": "لرستان"
    },
    {
        "id": 26,
        "name": "گیلان",
        "slug": "گیلان"
    },
    {
        "id": 27,
        "name": "مازندران",
        "slug": "مازندران"
    },
    {
        "id": 28,
        "name": "مرکزی",
        "slug": "مرکزی"
    },
    {
        "id": 29,
        "name": "هرمزگان",
        "slug": "هرمزگان"
    },
    {
        "id": 30,
        "name": "همدان",
        "slug": "همدان"
    },
    {
        "id": 31,
        "name": "یزد",
        "slug": "یزد"
    }
]


def get_kind_name(kind: str) -> str:
    normalized_kind = kind.upper()
    if normalized_kind == "SCL":
        return "SCL دوپامین"
    if normalized_kind == "AG":
        return "AG استعدادسنجی"
    if normalized_kind in PSY_PACKAGE_TITLES:
        return f"PSY {PSY_PACKAGE_TITLES[normalized_kind]}"
    return kind
