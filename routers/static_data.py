from fastapi import APIRouter, HTTPException

import helper.static_data.get_data as static_data

router = APIRouter()


@router.get("/ags_api/majors")
@router.get("/ag_api/majors")
async def get_majors():
    return {"majors": static_data.MAJORS}


@router.get("/ags_api/majors/{major_id}/categories")
@router.get("/ag_api/majors/{major_id}/categories")
async def get_major_categories(major_id: int):
    major_item = next((item for item in static_data.MAJORS if item["id"] == major_id), None)
    if not major_item:
        raise HTTPException(status_code=404, detail="Major not found")

    categories = [item for item in static_data.CATEGORY if item.get("number") == major_item["id"]]
    return {"major": major_item, "categories": categories}


@router.get("/ags_api/fields/{field_id}")
@router.get("/ag_api/fields/{field_id}")
async def get_field(field_id: int):
    field_item = next((item for item in static_data.FIELDS if item["id"] == field_id), None)
    if not field_item:
        raise HTTPException(status_code=404, detail="Field not found")

    category_items = [item for item in static_data.CATEGORY if item.get("id") == field_id]
    field_item_with_categories = field_item.copy()

    if category_items:
        field_item_with_categories["categories"] = category_items
        first_category = category_items[0]
        for key in ["a1", "a2", "a3", "a4", "a5", "a6"]:
            if key in first_category:
                field_item_with_categories[key] = first_category[key]
    else:
        for key in ["a1", "a2", "a3", "a4", "a5", "a6"]:
            field_item_with_categories[key] = None

    return {"field": field_item_with_categories}
