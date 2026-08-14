import json
from datetime import datetime

import helper.db.db_helper as db_helper
import helper.func_helper as func_helper


def change_capacity(conn, cursor, request_data):
    """
    Update capacity with phone number of the user and log the changes.
    """
    try:
        phone = request_data.get("phone")
        kind = request_data.get("kind")
        count = request_data.get("count")

        if not phone:
            return None, "شماره تلفن الزامی است."

        if not kind:
            return None, "نوع بسته الزامی است."

        kind = kind.upper()
        if kind not in func_helper.PACKAGES_DATA:
            valid_packages = "، ".join(f"{package} ({func_helper.get_kind_name(package)})" for package in func_helper.PACKAGES_DATA.keys())
            return None, f"نوع بسته معتبر نیست. بسته‌های معتبر: {valid_packages}"

        if not isinstance(count, int):
            return None, "تعداد باید یک عدد صحیح مثبت باشد."

        if count <= 0:
            return None, "تعداد باید یک عدد صحیح مثبت باشد."

        # Get user user_info from users table
        query_user = 'SELECT user_id, role FROM users WHERE phone = ?'
        # Assuming the field name in users is 'id'. In your original snippet, you queried user_id,
        # so make sure this matches your actual schema.
        user_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_user, field=phone)

        if not user_res:
            return None, "کاربری با این شماره تلفن یافت نشد."

        user_id = user_res.user_id
        role = user_res.role

        if role not in ["ins", "sch", "ocon"]:
            return None, "نقش کاربر باید ins، sch یا ocon باشد."

        # Check if capacity record exists
        query_capacity = 'SELECT capacity_id FROM capacity WHERE user_id = ?'
        capacity_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_capacity, field=user_id)

        capacity_id = None
        if capacity_res:
            capacity_id = capacity_res.capacity_id
        else:
            # Create capacity record if it doesn't exist
            field = '([user_id], [phone])'
            values = (user_id, phone)
            capacity_result = db_helper.insert_value(
                conn=conn,
                cursor=cursor,
                table_name="capacity",
                fields=field,
                values=values,
                id_column="capacity_id"
            )
            if capacity_result and capacity_result.get("id"):
                capacity_id = capacity_result["id"]
            else:
                return None, "خطا در ایجاد رکورد ظرفیت."

        # Check if capacity_package record exists for this kind
        # NOTE: Added 'used' to the SELECT statement to capture it for logging
        query_package = (
            'SELECT capacity_package_id, total_allowed, allowed, used '
            'FROM capacity_package WHERE user_id = ? AND package_name = ?'
        )
        package_res = db_helper.search_table(
            conn=conn,
            cursor=cursor,
            query=query_package,
            field=(user_id, kind)
        )

        log_fields = '([user_id], [capacity_id], [capacity_package_id], [package_name], [allowed], [used], [change])'

        if package_res:
            # Update existing record
            capacity_package_id = package_res.capacity_package_id
            current_used = getattr(package_res, 'used', 0)
            current_total_allowed = getattr(package_res, 'total_allowed', None)
            if current_total_allowed is None:
                current_total_allowed = package_res.allowed + current_used
            new_allowed = package_res.allowed + count
            new_total_allowed = current_total_allowed + count

            db_helper.update_record(
                conn=conn,
                cursor=cursor,
                table_name="capacity_package",
                update_fields=["total_allowed", "allowed", "edited_time"],
                update_values=[new_total_allowed, new_allowed, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                condition="capacity_package_id = ?",
                condition_values=[capacity_package_id]
            )

            # Insert Log
            log_values = (
                user_id, capacity_id, capacity_package_id, kind, new_allowed, current_used, count)
            db_helper.insert_value(
                conn=conn, cursor=cursor, table_name="capacity_logs",
                fields=log_fields, values=log_values
            )

        else:
            # Insert new record
            field_package = '([capacity_id], [user_id], [phone], [package_name], [total_allowed], [allowed])'
            values_package = (capacity_id, user_id, phone, kind, count, count)

            # Pass id_column to capture the newly generated capacity_package_id
            insert_result = db_helper.insert_value(
                conn=conn,
                cursor=cursor,
                table_name="capacity_package",
                fields=field_package,
                values=values_package,
                id_column="capacity_package_id"
            )

            # Get the new ID for logging
            capacity_package_id = insert_result.get("id") if insert_result else None

            # Insert Log
            if capacity_package_id:
                log_values = (user_id, capacity_id, capacity_package_id, kind, count, 0, count)
                db_helper.insert_value(
                    conn=conn, cursor=cursor, table_name="capacity_logs",
                    fields=log_fields, values=log_values
                )

        package_names = list(func_helper.PACKAGES_DATA.keys())
        package_placeholders = ", ".join(["?"] * len(package_names))
        query_all_packages = (
            f'SELECT package_name, allowed FROM capacity_package '
            f'WHERE user_id = ? AND package_name IN ({package_placeholders})'
        )
        all_packages = db_helper.search_fetchall(
            conn=conn,
            cursor=cursor,
            query=query_all_packages,
            field=(user_id, *package_names)
        )

        capacity_result = {package_name: 0 for package_name in package_names}
        for pkg in all_packages:
            pkg_name = pkg.get("package_name", "").upper() if isinstance(pkg, dict) else getattr(pkg, "package_name",
                                                                                                 "").upper()
            if pkg_name in capacity_result:
                capacity_result[pkg_name] = pkg.get("allowed", 0) if isinstance(pkg, dict) else getattr(pkg, "allowed",
                                                                                                        0)

        token = func_helper.get_tracking_code()
        return token, {
            "phone": phone,
            "capacity": capacity_result
        }

    except Exception as e:
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/admin_request", "change_capacity", str(e), request_data, {}
        )
        return None, f"خطا در به‌روزرسانی ظرفیت: {str(e)}"


def get_user_info(conn, cursor, request_data):
    """
    Get user user_info by phone number.
    
    Requirements:
    - Request data has phone
    - Get information from users and ins, sch, ocon, con, stu tables
    - For ocon, sch, ins return capacity
    - Return user user_info
    """
    try:
        phone = request_data.get("phone")

        if not phone:
            return None, "شماره تلفن الزامی است."

        # Get user user_info from users table
        query_user = 'SELECT user_id, role FROM users WHERE phone = ?'
        user_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_user, field=phone)

        if not user_res:
            return None, "کاربری با این شماره تلفن یافت نشد."

        user_id = user_res.user_id
        role = user_res.role

        user_info = {
            "user_id": user_id,
            "phone": phone,
            "role": role
        }

        # Get role-specific information
        if role == "ins":
            query_role = 'SELECT ins_id, name, logo, verify FROM ins WHERE phone = ?'
            role_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_role, field=phone)
            if role_res:
                user_info.update({
                    "ins_id": role_res.ins_id,
                    "name": role_res.name,
                    "logo": role_res.logo,
                    "verify": role_res.verify
                })

                # Get capacity for ins
                query_capacity = 'SELECT package_name, allowed, used FROM capacity_package WHERE user_id = ?'
                capacity_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query_capacity, field=user_id)
                capacity_info = {
                    row["package_name"]: {"allowed": row["allowed"], "used": row["used"]}
                    for row in capacity_res
                }
                user_info["capacity"] = capacity_info

        elif role == "sch":
            query_role = 'SELECT sch_id, name, logo, verify FROM sch WHERE phone = ?'
            role_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_role, field=phone)
            if role_res:
                user_info.update({
                    "sch_id": role_res.sch_id,
                    "name": role_res.name,
                    "logo": role_res.logo,
                    "verify": role_res.verify
                })

                # Get capacity for sch
                query_capacity = 'SELECT package_name, allowed, used FROM capacity_package WHERE user_id = ?'
                capacity_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query_capacity, field=user_id)
                capacity_info = {
                    row["package_name"]: {"allowed": row["allowed"], "used": row["used"]}
                    for row in capacity_res
                }
                user_info["capacity"] = capacity_info

        elif role == "ocon":
            query_role = 'SELECT ocon_id, first_name, last_name, sex, verify FROM ocon WHERE phone = ?'
            role_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_role, field=phone)
            if role_res:
                user_info.update({
                    "ocon_id": role_res.ocon_id,
                    "first_name": role_res.first_name,
                    "last_name": role_res.last_name,
                    "sex": role_res.sex,
                    "verify": role_res.verify
                })

                # Get capacity for ocon
                query_capacity = 'SELECT package_name, allowed, used FROM capacity_package WHERE user_id = ?'
                capacity_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query_capacity, field=user_id)
                capacity_info = {
                    row["package_name"]: {"allowed": row["allowed"], "used": row["used"]}
                    for row in capacity_res
                }
                user_info["capacity"] = capacity_info

        elif role == "con":
            query_role = 'SELECT con_id, first_name, last_name, sex, ins_id, ins_role FROM con WHERE phone = ?'
            role_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_role, field=phone)
            if role_res:
                user_info.update({
                    "con_id": role_res.con_id,
                    "first_name": role_res.first_name,
                    "last_name": role_res.last_name,
                    "sex": role_res.sex,
                    "ins_id": role_res.ins_id,
                    "ins_role": role_res.ins_role
                })

        elif role == "stu":
            query_role = 'SELECT stu_id, first_name, last_name, sex, city, birth_date, ins_id, con_id, ins_role FROM stu WHERE phone = ?'
            role_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_role, field=phone)
            if role_res:
                user_info.update({
                    "stu_id": role_res.stu_id,
                    "first_name": role_res.first_name,
                    "last_name": role_res.last_name,
                    "sex": role_res.sex,
                    "city": role_res.city,
                    "birth_date": role_res.birth_date,
                    "ins_id": role_res.ins_id,
                    "con_id": role_res.con_id,
                    "ins_role": role_res.ins_role
                })

                # Get access field
                query_access = 'SELECT access FROM stu WHERE phone = ?'
                access_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_access, field=phone)
                if access_res:
                    raw_access = getattr(access_res, "access", None) or "{}"
                    try:
                        access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
                    except (json.JSONDecodeError, TypeError):
                        access_data = {}
                    user_info["access"] = access_data

        token = func_helper.get_tracking_code()
        return token, user_info

    except Exception as e:
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/admin_request", "get_user_info", str(e), request_data, {}
        )
        return None, f"خطا در دریافت اطلاعات کاربر: {str(e)}"


def check_student_quiz_answer(conn, cursor, request_data):
    """
    Check student quiz answer and student state.
    
    Requirements:
    - With quiz_answer table check student quiz answer
    - Check student state (in stu table with access field for permission and limits)
    - Return object of student quiz answer and student state
    """
    try:
        phone = request_data.get("phone")

        if not phone:
            return None, "شماره تلفن الزامی است."

        # Get student user_info
        query_stu = 'SELECT user_id, first_name, last_name, access FROM stu WHERE phone = ?'
        stu_res = db_helper.search_table(conn=conn, cursor=cursor, query=query_stu, field=phone)

        if not stu_res:
            return None, "دانش‌آموزی با این شماره تلفن یافت نشد."

        user_id = stu_res.user_id

        # Get access field
        raw_access = getattr(stu_res, "access", None) or "{}"
        try:
            access_data = json.loads(raw_access) if isinstance(raw_access, str) else (raw_access or {})
        except (json.JSONDecodeError, TypeError):
            access_data = {}

        # Get quiz answers
        query_quiz = 'SELECT quiz_id, quiz_kind, answers, state FROM quiz_answer WHERE user_id = ? ORDER BY quiz_id ASC'
        quiz_res = db_helper.search_fetchall(conn=conn, cursor=cursor, query=query_quiz, field=user_id)

        quiz_answers = []
        for quiz in quiz_res:
            quiz_answers.append({
                "quiz_id": quiz.get("quiz_id"),
                "quiz_kind": quiz.get("quiz_kind"),
                "answers": quiz.get("answers"),
                "state": quiz.get("state")
            })

        # Process student state from access field
        student_state = {}
        for package_name in ["AG", "SCL"]:
            package_info = access_data.get(package_name, {})
            permission = 0
            limit = 0

            if isinstance(package_info, dict):
                permission = int(package_info.get("permission") or 0)
                limit = int(package_info.get("limit") or 0)
            elif isinstance(package_info, bool):
                permission = 1 if package_info else 0
            elif isinstance(package_info, (int, float, str)):
                try:
                    permission = int(package_info) if str(package_info).strip() != "" else 0
                except ValueError:
                    permission = 0

            student_state[package_name] = {
                "permission": permission,
                "limit": limit
            }

        result = {
            "student_id": user_id,
            "phone": phone,
            "first_name": stu_res.first_name,
            "last_name": stu_res.last_name,
            "quiz_answers": quiz_answers,
            "student_state": student_state,
            "access": access_data
        }

        token = func_helper.get_tracking_code()
        return token, result

    except Exception as e:
        func_helper.service_exception_error_logging(
            conn, cursor, "ag_api/admin_request", "check_student_quiz_answer", str(e), request_data, {}
        )
        return None, f"خطا در بررسی پاسخ‌های آزمون دانش‌آموز: {str(e)}"
