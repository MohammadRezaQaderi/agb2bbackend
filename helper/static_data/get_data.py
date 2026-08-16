import json


def load_data():
    with open("./helper/static_data/fields_info.json", encoding="utf-8") as f:
        fields_info = json.load(f)

    with open("./helper/static_data/majors_info.json", encoding="utf-8") as f:
        majors_info = json.load(f)

    with open("./helper/static_data/categories_info.json", encoding="utf-8") as f:
        categories_info = json.load(f)

    return fields_info, majors_info, categories_info


FIELDS, MAJORS, CATEGORY = load_data()
