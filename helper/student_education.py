EDUCATION_LEVELS = (
    {"id": "first", "label": "اول"},
    {"id": "second", "label": "دوم"},
)

EDUCATION_FIELDS = (
    {"id": "experimental", "label": "تجربی"},
    {"id": "mathematics", "label": "ریاضی"},
    {"id": "humanities", "label": "انسانی"},
    {"id": "technical_vocational_work_knowledge", "label": "فنی حرفه‌ای - کاردانش"},
)

EDUCATION_LEVEL_IDS = {item["id"] for item in EDUCATION_LEVELS}
EDUCATION_FIELD_IDS = {item["id"] for item in EDUCATION_FIELDS}
# Accept earlier values in case any were saved before the options were unified.
EDUCATION_FIELD_IDS.update({"technical_vocational", "work_knowledge"})
