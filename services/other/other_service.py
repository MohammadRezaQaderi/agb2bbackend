import json, httpx
from datetime import datetime

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper


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

def get_all_products(conn, cursor):
    query = """
        SELECT 
            product_id AS id, 
            name, 
            price, 
            status, 
            image 
        FROM product 
        ORDER BY created_time DESC
    """
    res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query)
    products_info = [
        {
            "id": p[0],
            "name": p[1],
            "price": p[2],
            "status": p[3],
            "image": p[4]
        }
        for p in res
    ]
    token = func_helper.get_tracking_code()
    return token, products_info, ""


def get_transactions(conn, cursor, request_data, user_info):
    try:
        query = """
                SELECT 
                    payment_id AS id, 
                    state, 
                    status, 
                    product_data, 
                    result, 
                    edited_time AS date 
                FROM payment 
                WHERE user_id = ? 
                ORDER BY created_time DESC
            """
        res = db_helper.search_allin_table(conn, cursor, query, str(user_info["user_id"]))
        transactions_info = []
        for p in res:
            try:
                # Parse the full product_data JSON
                full_product_data = json.loads(p[3]) if p[3] else {}
                
                # Extract only the required fields: packages, product_name, discount_price, price
                filtered_product_data = {
                    "packages": full_product_data.get("packages", {}),
                    "product_name": full_product_data.get("product_name", ""),
                    "discount_price": full_product_data.get("discount_price", 0),
                    "price": full_product_data.get("price", 0)
                }
                
                transactions_info.append({
                    "id": p[0],
                    "state": p[1],
                    "status": p[2],
                    "product_data": filtered_product_data,
                    "result": p[4],
                    "date": p[5]
                })
            except (json.JSONDecodeError, TypeError) as e:
                # If product_data is invalid JSON, include empty product_data
                print(f"Error parsing product_data for payment_id {p[0]}: {e}")
                transactions_info.append({
                    "id": p[0],
                    "state": p[1],
                    "status": p[2],
                    "product_data": {
                        "packages": {},
                        "product_name": "",
                        "discount_price": 0,
                        "price": 0
                    },
                    "result": p[4],
                    "date": p[5]
                })
        token = func_helper.get_tracking_code()
        return token, transactions_info, ""
    except Exception as e:
        print(e)
        return None, None, "مشکلی در دریافت لیست تراکنش‌ها رخ داده است."


def apply_discount(conn, cursor, request_data, user_info):
    try:
        query = 'SELECT id, discount_percentage, count, status, count_apply, expire_time FROM discounts WHERE code = ?'
        res = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["discount_code"])
        if not res:
            return None, None, "کد تخفیف مد نظر شما موجود نیست."

        if res.expire_time and datetime.now() > res.expire_time:
            return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
        if res.status == 'expired':
            return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
        if res.count == 0:
            return None, None, "متاسفانه کد تخفیف مدنظر اتمام یافته."

        field = '([code], [status], [phone], [user_id])'
        values = (request_data["discount_code"], "APPLY CODE", user_info["phone"], user_info["user_id"])
        db_helper.insert_value(conn=conn, cursor=cursor, table_name='using_discount', fields=field, values=values)
        db_helper.update_record(
            conn, cursor, "discounts", ["count_apply", "edited_time"], [
                res.count_apply + 1,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ], "id = ?", [res.id]
        )

        token = func_helper.get_tracking_code()
        new_total = (round(int(request_data["total_value"]) * (1 - res.discount_percentage))) / 100
        return token, {"new_total": new_total}, ""
    except Exception as e:
        print("error occurred in apply discounts", e)
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/other", "apply_discount", str(e), request_data, user_info
        )
        return None, None, "در پردازش کد تخفیف مشکلی پیش آمده"


def get_order_status(conn, cursor, data, user_info):
    try:
        query = """
                    SELECT 
                        payment_id AS id, 
                        state, 
                        status, 
                        price, 
                        product_data, 
                        result, 
                        edited_time AS date 
                    FROM payment 
                    WHERE user_id = ? and payment_id = ?
                    ORDER BY created_time DESC
                """

        res = db_helper.search_allin_table(conn, cursor, query, [str(user_info["user_id"]), str(data["payment_id"])])
        if len(res) != 0:
            status = res[0][2]
            transactions_info = {
                "id": res[0][0],
                "state": res[0][1],
                "status": res[0][2],
                "price": res[0][3],
                "product_data": json.loads(res[0][4]),
                "result": res[0][5],
                "date": res[0][6]
            }
        else:
            status = "UNDIFINE"
            transactions_info = {}
        token = func_helper.get_tracking_code()
        return token, transactions_info, status
    except Exception as e:
        print(e)
        return None, None, "مشکلی در دریافت وضعیت سفارش رخ داده است."


def mellat_request_created(conn, cursor, data, user_info):
    try:
        token = 'eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoiQWRtaW4iLCJJc3N1ZXIiOiIwMUZhcmRha2hlaWxpc2FieiIsIlVzZXJuYW1lIjoiTXJxMjciLCJleHAiOjE3NTMwODc5NzcsImlhdCI6MTc1MzA4Nzk3N30.mlcxgBMXIjmw04DPeMkSL5Ijqlg-ifZXQnw_d889qvM'
        endpoint = "b2b"
        try:
            data["user_id"] = user_info.get("user_id")
            data["phone"] = user_info.get("phone")
            with httpx.Client() as client:
                request_data = {
                    "token": token,
                    "endpoint": endpoint,
                    "gateway": "mellat",
                    "data": data
                }

                response = client.post(
                    "https://baazmoon.com/get_ref_info",
                    json=request_data,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                else:
                    raise Exception(f"HTTP error: {response.status_code}")
        except Exception as e:
            print(f"Remote call failed, using local implementation: {e}")
        if result.get("authenticate") and result.get("is_successful"):
            ref_id = result["data"]["ref_id"]
            url = result["data"]["url"]
            message = result["message"]

            # We only store aggregated product information as JSON in product_data.
            field = '([payment_id], [user_id], [phone], [state], [status], [price], [discount_price], [track_id], [result], [discount_id], [message], [product_data], [token])'
            values = (
                data["payment_id"],
                user_info["user_id"],
                user_info["phone"],
                "SendPaymentGateway",
                "PEND",
                data["price"],
                data["discount_price"],
                ref_id,
                "انتقال به درگاه پرداخت",
                data["discount_id"],
                message,
                json.dumps(data, ensure_ascii=False),
                ref_id,
            )
            db_helper.insert_value(conn=conn, cursor=cursor, table_name='payment', fields=field,
                                   values=values)
            return ref_id, message, url

        else:
            message = result.get("message", "Unknown error from payment gateway")
            field = '([payment_id], [user_id], [phone], [state], [status], [price], [discount_price], [track_id], [result], [discount_id], [message], [product_data], [token])'
            values = (
                data["payment_id"], user_info["user_id"], user_info["phone"], "NOTREFID", "Error", data["price"],
                data["discount_price"], None, "", data["discount_id"], message,
                json.dumps(data, ensure_ascii=False), None)
            db_helper.insert_value(conn=conn, cursor=cursor, table_name='payment_log', fields=field,
                                   values=values)
            return None, message, None

    except Exception as e:
        field = '([payment_id], [user_id], [phone], [state], [status], [price], [discount_price], [track_id], [result], [discount_id], [message], [product_data], [token])'
        values = (
            data["payment_id"], user_info["user_id"], user_info["phone"], "MellatGatewayException", "Bug", data["price"],
            data["discount_price"], None, "مشکل در درگاه بانک ملت", data["discount_id"], str(e),
            json.dumps(data, ensure_ascii=False), None)
        db_helper.insert_value(conn=conn, cursor=cursor, table_name='payment_log', fields=field,
                               values=values)
        return None, str(e), None


def order_payment(conn, cursor, request_data, user_info):
    try:
        phone = user_info["phone"]

        # Expected request_data example:
        # {
        #     "AG": 10,
        #     "SCL": 50,
        #     "discount_code": "",
        #     "user_id": 4,
        #     "token": "314665f9-80a3-4929-95f1-41a19e665f06"
        # }

        # Determine basic product name based on selected packages.
        ag_count = int(request_data.get("AG", 0) or 0)
        scl_count = int(request_data.get("SCL", 0) or 0)
        if ag_count == 0 and scl_count > 0:
            product_name = "بسته‌ی اختلال"
        elif ag_count > 0 and scl_count == 0:
            product_name = "بسته‌ی هدایت"
        elif ag_count > 0 and scl_count > 0:
            product_name = "بسته‌ی هدایت و اختلال"
        else:
            product_name = "بدون محصول"

        discount_id = None
        discount_percentage = None
        if request_data.get("discount_code"):
            query = 'SELECT id, discount_percentage, count, status, used_apply, expire_time FROM discounts WHERE code = ?'
            res_discount = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["discount_code"])
            if not res_discount:
                return None, None, "کد تخفیف شما موجود نیست."
            elif res_discount:
                if datetime.now() > res_discount.expire_time:
                    return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
                elif res_discount.status == 'EXPIRED':
                    return None, None, "متاسفانه زمان مصرف این کد به پایان رسیده."
                elif res_discount.count == 0:
                    return None, None, "متاسفانه کد تخفیف مدنظر اتمام یافته."
                else:
                    discount_id = res_discount.id
                    discount_percentage = res_discount.discount_percentage
                    field = '([code], [status], [phone], [user_id])'
                    values = (request_data["discount_code"], "GOPAYMENT", user_info["phone"], user_info["user_id"])
                    res_cap = db_helper.insert_value(conn=conn, cursor=cursor, table_name='using_discount',
                                                     fields=field,
                                                     values=values)
                    db_helper.update_record(
                        conn,
                        cursor,
                        "discounts",
                        ["used_apply", "edited_time"],
                        [
                            res_discount.used_apply + 1,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ],
                        "id = ?",
                        [res_discount.id],
                    )

        # Calculate price based on selected packages and discounts.
        price, discount_price, ag_count, scl_count = func_helper.get_price_payment(
            request_data, discount_percentage=discount_percentage
        )

        payment_id = func_helper.get_payment_id(conn, cursor)

        # Store product details in a generic structure so future products can be added easily.
        product_data = {
            "price": price,
            "discount_price": discount_price,
            "product_name": product_name,
            "packages": {
                "AG": ag_count,
                "SCL": scl_count,
            },
            # Backward-compatible count fields for the payment table mapper.
            "AG": ag_count,
            "SCL": scl_count,
            "payment_id": payment_id,
            "card_phone": phone,
            "gateway": "mellat",
            "discount_id": discount_id,
        }
        return None, None, "متاسفانه فعلا درگاه پرداخت در دسترس نیست"
        ref_id, message, url = mellat_request_created(conn, cursor, product_data, user_info)
        return func_helper.get_tracking_code(), {"ref_id": ref_id, "url": url}, message
    except Exception as e:
        print(e)
        return None, None, "خطا در دسترسی به پرداخت"


def get_report_data(conn, cursor, request_data, user_info):
    try:
        kind = request_data.get("report_type", "").upper()
        student_id = request_data.get("student_id")
        
        if not student_id:
            return None, None, "شناسه دانش‌آموز ارسال نشده است."
        
        if kind == "AG":
            # Fetch result_state from result_state table
            query_result_state = """
                SELECT 
                    t_state, r_state, e_state, a_state, 
                    m_state, f_state, i_state
                FROM result_state 
                WHERE user_id = ?
            """
            res_result_state = db_helper.search_table(conn=conn, cursor=cursor, query=query_result_state, field=student_id)
            
            # Fetch brain_categories from scores table
            query_scores = """
                SELECT brain_categories
                FROM scores
                WHERE user_id = ?
            """
            res_scores = db_helper.search_table(conn=conn, cursor=cursor, query=query_scores, field=student_id)
            
            # Build result_state data
            result_state_data = {}
            if res_result_state:
                for field_key, field_info in AG_REPORT_INFO.items():
                    field_value = getattr(res_result_state, field_key, None)
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
            if res_scores:
                raw_brain_categories = getattr(res_scores, "brain_categories", None)
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
            # Fetch scl_date from scl_scores table
            query_scl_scores = """
                SELECT scl_date
                FROM scl_scores
                WHERE user_id = ?
            """
            res_scl_scores = db_helper.search_table(conn=conn, cursor=cursor, query=query_scl_scores, field=student_id)
            
            # Extract scl_date
            scl_date_data = None
            if res_scl_scores:
                raw_scl_date = getattr(res_scl_scores, "scl_date", None)
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


def get_comments(conn, cursor):
    try:
        query = """
            SELECT TOP 100
                id,
                name,
                comment,
                rating,
                persian_date
            FROM comments
            ORDER BY created_time DESC
        """
        res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query)
        comments = [
            {
                "id": p["id"],
                "name": p["name"],
                "comment": p["comment"],
                "rating": p["rating"],
                "persian_date": p["persian_date"],
            }
            for p in res
        ]
        return func_helper.get_tracking_code(), comments, ""
    except Exception as e:
        print("error occurred in get comments", e)
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/other", "get_comments", str(e), {}, {}
        )
        return None, None, "خطا در دریافت نظرات."


def add_comment(conn, cursor, request_data):
    try:
        query = 'SELECT role, user_id FROM users WHERE phone = ?'
        res_role = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["phone"])
        if res_role is None:
            return None, None, "کاربر یافت نشد."

        user_role = res_role[0]
        db_name = ""
        if user_role in ["ins", "sch"]:
            if user_role == "ins":
                query = 'SELECT user_id, name, phone FROM ins WHERE phone = ?'
            else:
                query = 'SELECT user_id, name, phone FROM sch WHERE phone = ?'
            res_user = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["phone"])
            if res_user is None:
                return None, None, "اطلاعات کاربر یافت نشد."
            db_name = res_user[1]
        elif user_role in ["con", "ocon"]:
            if user_role == "con":
                query = 'SELECT user_id, first_name, last_name, phone FROM con WHERE phone = ?'
            else:
                query = 'SELECT user_id, first_name, last_name, phone FROM ocon WHERE phone = ?'
            res_user = db_helper.search_table(conn=conn, cursor=cursor, query=query, field=request_data["phone"])
            if res_user is None:
                return None, None, "اطلاعات کاربر یافت نشد."
            db_name = res_user[1] + " " + res_user[2]

        field = '([name], [comment], [rating], [persian_date], [user_id], [phone], [db_name], [role])'
        values = (
            request_data["first_name"] + " " + request_data["last_name"],
            request_data["comment"],
            request_data["rating"],
            request_data["date"],
            res_role[1],
            request_data["phone"],
            db_name,
            user_role,
        )
        db_helper.insert_value(conn=conn, cursor=cursor, table_name='comments', fields=field, values=values)
        return func_helper.get_tracking_code(), None, "نظر شما با موفقیت ثبت شد."
    except Exception as e:
        conn.rollback()
        print("error occurred in add comment", e)
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/other", "add_comment", str(e), request_data, {}
        )
        return None, None, "خطا در ثبت نظر."
