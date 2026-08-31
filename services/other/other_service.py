import json
from datetime import datetime

from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.other import (
    create_comment,
    get_comment_user_info_by_phone,
    get_discount_by_code,
    get_result_state_for_user,
    get_scl_score_date,
    get_score_brain_categories,
    list_latest_comments,
    list_user_transactions,
    mark_notification_read_if_allowed,
    record_discount_usage,
)
import helper.func_helper as func_helper
from helper.response import build_comment_list_response, build_transaction_list_response


# AG_REPORT_INFO structure mapping result_state fields to their display names
# Fields from result_state table:
#   t_state NVARCHAR(100) -> تجربی (Experimental Sciences)
#   r_state NVARCHAR(100) -> ریاضی (Mathematics)
#   e_state NVARCHAR(100) -> انسانی (Humanities)
#   a_state NVARCHAR(100) -> هنر (Arts)
#   m_state NVARCHAR(100) -> مدیریت (Management)
#   f_state NVARCHAR(100) -> کشاورزی (Agriculture)
#   i_state NVARCHAR(100) -> صنعت (Industry)
AG_REPORT_INFO = {
    "t_state": {"name": "تجربی", "title": "t_state"},
    "r_state": {"name": "ریاضی", "title": "r_state"},
    "e_state": {"name": "انسانی", "title": "e_state"},
    "a_state": {"name": "هنر", "title": "a_state"},
    "m_state": {"name": "مدیریت", "title": "m_state"},
    "f_state": {"name": "کشاورزی", "title": "f_state"},
    "i_state": {"name": "صنعت", "title": "i_state"}
}

CATEGORY_DEF_COLOR = {
    "دبیری": "#c8acdc", "مدیریت": "#a0a4bc", "علوم پایه": "#a0c4e4", "هنر": "#a0dcfc",
    "مهندسی سازه": "#99dfb9", "مهندسی صنعتی": "#d8ecbc", "الکترونیک و کامپیوتر": "#fffc9c",
    "علوم انسانی": "#ffe699", "مالی و حسابداری": "#ff9999", "روانشناسی": "#e69999",
    "روابط عمومی": "#c6acd9", "کشاورزی و امور دامی": "#99a6bf", "حقوق و علوم سیاسی": "#99c6e6",
    "خدمات فنی": "#99dff9", "تکنسین فنی": "#99dfb9", "بالینی و درمانی": "#d3ecb9",
    "تشخیصی و درمانی": "#ffff99", "تکنسین کامپیوتر": "#ffe699"
}

def normalize_persian_text(text):
    """
    Normalize Persian text by replacing character variations:
    - ي (U+064A) -> ی (U+06CC)
    - ك (U+0643) -> ک (U+06A9)
    """
    if not text:
        return text
    # Replace Arabic Yeh (ي) with Persian Yeh (ی)
    text = text.replace("\u064A", "\u06CC")
    # Replace Arabic Kaf (ك) with Persian Kaf (ک)
    text = text.replace("\u0643", "\u06A9")
    return text

def get_transactions(request_data, user_info):
    try:
        with session_scope() as session:
            transactions = list_user_transactions(session=session, user_id=user_info["user_id"])
        transactions_info = build_transaction_list_response(transactions)
        token = func_helper.get_tracking_code()
        return token, transactions_info, ""
    except Exception as e:
        print(e)
        return None, None, "مشکلی در دریافت لیست تراکنش‌ها رخ داده است."


def apply_discount(request_data, user_info):
    try:
        with session_scope() as session:
            res = get_discount_by_code(session=session, code=request_data["discount_code"])
        if not res:
            return None, None, "کد تخفیف مد نظر شما موجود نیست."

        if res["expire_time"] and datetime.now() > res["expire_time"]:
            return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
        if res["status"] == 'expired':
            return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
        if res["count"] == 0:
            return None, None, "متاسفانه کد تخفیف مدنظر اتمام یافته."

        with session_scope() as session:
            record_discount_usage(
                session=session,
                discount_id=res["id"],
                code=request_data["discount_code"],
                status="APPLY CODE",
                phone=user_info["phone"],
                user_id=user_info["user_id"],
                counter_field="count_apply",
            )

        token = func_helper.get_tracking_code()
        new_total = (round(int(request_data["total_value"]) * (1 - res["discount_percentage"]))) / 100
        return token, {"new_total": new_total}, ""
    except Exception as e:
        print("error occurred in apply discounts", e)
        func_helper.service_exception_error_logging("ag_api/other", "apply_discount", str(e), request_data, user_info
        )
        return None, None, "در پردازش کد تخفیف مشکلی پیش آمده"


def order_payment(request_data, user_info):
    try:
        # Expected request_data example:
        # {
        #     "AG": 10,
        #     "SCL": 50,
        #     "discount_code": "",
        #     "user_id": 4,
        #     "token": "314665f9-80a3-4929-95f1-41a19e665f06"
        # }

        discount_percentage = None
        if request_data.get("discount_code"):
            with session_scope() as session:
                res_discount = get_discount_by_code(session=session, code=request_data["discount_code"])
            if not res_discount:
                return None, None, "کد تخفیف شما موجود نیست."
            elif res_discount:
                if res_discount["expire_time"] and datetime.now() > res_discount["expire_time"]:
                    return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
                elif res_discount["status"] == 'EXPIRED':
                    return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
                elif res_discount["count"] == 0:
                    return None, None, "متاسفانه کد تخفیف مدنظر اتمام یافته."
                else:
                    discount_id = res_discount["id"]
                    discount_percentage = res_discount["discount_percentage"]
                    with session_scope() as session:
                        record_discount_usage(
                            session=session,
                            discount_id=discount_id,
                            code=request_data["discount_code"],
                            status="GOPAYMENT",
                            phone=user_info["phone"],
                            user_id=user_info["user_id"],
                            counter_field="used_apply",
                        )

        # Keep the existing package/discount validation path while the gateway is disabled.
        func_helper.get_price_payment(request_data, discount_percentage=discount_percentage)
        return None, None, "متاسفانه فعلا درگاه پرداخت در دسترس نیست"
    except Exception as e:
        print(e)
        return None, None, "خطا در دسترسی به پرداخت"


def get_report_data(request_data, user_info):
    try:
        kind = request_data.get("report_type", "").upper()
        student_id = request_data.get("student_id")
        
        if not student_id:
            return None, None, "شناسه دانش‌آموز ارسال نشده است."
        
        if kind == "AG":
            with session_scope() as session:
                result_state = get_result_state_for_user(session=session, user_id=student_id)
                raw_brain_categories = get_score_brain_categories(session=session, user_id=student_id)
            
            # Build result_state data
            result_state_data = {}
            if result_state:
                for field_key, field_info in AG_REPORT_INFO.items():
                    field_value = result_state.get(field_key)
                    result_state_data[field_key] = {
                        "name": field_info["name"],
                        "title": field_info["title"],
                        "value": field_value if field_value else None
                    }
            else:
                for field_key, field_info in AG_REPORT_INFO.items():
                    result_state_data[field_key] = {
                        "name": field_info["name"],
                        "title": field_info["title"],
                        "value": None
                    }
            
            # Parse brain_categories from JSON
            brain_categories_data = []
            if raw_brain_categories:
                try:
                    raw_data = json.loads(raw_brain_categories) if isinstance(raw_brain_categories, str) else (raw_brain_categories or [])
                    # Ensure it's a list
                    if not isinstance(raw_data, list):
                        raw_data = []
                    
                    # Transform each item: add color, convert value to int, rename keys
                    brain_categories_data = []
                    for item in raw_data:
                        category_name = item.get("Category") or item.get("category")
                        value = item.get("Value") or item.get("value", 0)
                        
                        # Normalize Persian characters for matching
                        normalized_category = normalize_persian_text(category_name)
                        
                        # Get color from CATEGORY_DEF_COLOR with normalized matching
                        color = "#cccccc"  # default fallback
                        if normalized_category:
                            # Try direct match first
                            if normalized_category in CATEGORY_DEF_COLOR:
                                color = CATEGORY_DEF_COLOR[normalized_category]
                            else:
                                # Try normalized matching with all keys
                                for key, value_color in CATEGORY_DEF_COLOR.items():
                                    if normalize_persian_text(key) == normalized_category:
                                        color = value_color
                                        break
                        
                        # Convert value to int
                        try:
                            value_int = int(float(value))
                        except (ValueError, TypeError):
                            value_int = 0
                        
                        brain_categories_data.append({
                            "name": category_name,
                            "color": color,
                            "value": value_int
                        })
                except (json.JSONDecodeError, TypeError):
                    brain_categories_data = []
            
            # Build report_data with both keys
            report_data = {
                "result_state": result_state_data,
                "brain_categories": brain_categories_data
            }
            
            token = func_helper.get_tracking_code()
            return token, report_data, ""
        elif kind == "SCL":
            with session_scope() as session:
                raw_scl_date = get_scl_score_date(session=session, user_id=student_id)

            # Extract scl_date
            scl_date_data = None
            if raw_scl_date:
                # Try to parse as JSON if it's a JSON string, otherwise return as string
                try:
                    if isinstance(raw_scl_date, str):
                        # Try parsing as JSON
                        try:
                            scl_date_data = json.loads(raw_scl_date)
                        except (json.JSONDecodeError, TypeError):
                            # If not JSON, return as string
                            scl_date_data = raw_scl_date
                    else:
                        scl_date_data = raw_scl_date
                except Exception:
                    scl_date_data = raw_scl_date
            
            # Build report_data with scl_date
            report_data = {
                "scl_date": scl_date_data
            }
            
            token = func_helper.get_tracking_code()
            return token, report_data, ""
        else:
            token = func_helper.get_tracking_code()
            return token, {}, ""
    except Exception as e:
        print(e)
        return None, None, "خطا در دریافت اطلاعات گزارش."


def get_comments():
    try:
        with session_scope() as session:
            comment_rows = list_latest_comments(session=session, limit=100)
        comments = build_comment_list_response(comment_rows)
        return func_helper.get_tracking_code(), comments, ""
    except Exception as e:
        print("error occurred in get comments", e)
        func_helper.service_exception_error_logging("ag_api/other", "get_comments", str(e), {}, {}
        )
        return None, None, "خطا در دریافت نظرات."


def add_comment(request_data):
    try:
        with session_scope() as session:
            user = get_comment_user_info_by_phone(session=session, phone=request_data["phone"])
            if user is None:
                return None, None, "کاربر یافت نشد."

            create_comment(
                session=session,
                name=request_data["first_name"] + " " + request_data["last_name"],
                comment=request_data["comment"],
                rating=request_data["rating"],
                persian_date=request_data["date"],
                user_id=user["user_id"],
                phone=request_data["phone"],
                db_name=user["db_name"],
                role=user["role"],
            )
        return func_helper.get_tracking_code(), None, "نظر شما با موفقیت ثبت شد."
    except Exception as e:
        print("error occurred in add comment", e)
        func_helper.service_exception_error_logging("ag_api/other", "add_comment", str(e), request_data, {}
        )
        return None, None, "خطا در ثبت نظر."


def _notification_role_aliases(role):
    if not role:
        return []

    return {
        "ins": ["ins", "institute"],
        "sch": ["sch", "school"],
        "ocon": ["ocon", "ownerConsultant"],
        "con": ["con"],
        "stu": ["stu", "student"],
    }.get(role, [role])


def mark_notification_read(request_data, user_info):
    try:
        notification_id = int(request_data["notification_id"])
        user_id = int(user_info["user_id"])
        with session_scope() as session:
            was_marked = mark_notification_read_if_allowed(
                session=session,
                notification_id=notification_id,
                user_id=user_id,
                role_aliases=_notification_role_aliases(user_info.get("role")),
            )
        if not was_marked:
            return None, None, "اعلان مورد نظر یافت نشد."

        return func_helper.get_tracking_code(), {"notification_id": notification_id, "is_read": 1}, ""
    except (TypeError, ValueError):
        return None, None, "شناسه اعلان معتبر نیست."
    except Exception as e:
        print("error occurred in mark notification read", e)
        func_helper.service_exception_error_logging("ag_api/other", "mark_notification_read", str(e), request_data, user_info
        )
        return None, None, "خطا در ثبت وضعیت اعلان."
