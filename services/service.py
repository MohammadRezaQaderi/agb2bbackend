from services.accounts_gateway import add_consultant, add_student
from services.admin.admin_gateway import (
    admin_change_capacity,
    admin_check_student_quiz_answer,
    admin_get_user_info,
)
from services.auth.auth_gateway import (
    check_otp,
    send_otp,
    sign_in,
    sign_out,
    sign_up,
    student_sign_in,
)
from services.other.other_gateway import (
    add_comment,
    add_payment_order,
    apply_discount,
    check_student_access,
    get_comments,
    get_report_data,
    get_transactions,
    mark_notification_read,
)
from services.quiz.quiz_gateway import get_quiz_info, get_quiz_setting, student_get_quiz_setting
from services.student.student_gateway import (
    student_change_password,
    student_change_quiz_answer,
    student_change_user_info,
    student_get_access_product,
    student_get_dashboard,
    student_get_quiz_info,
    student_get_quiz_table_info,
)
from services.gateway_helpers import (
    service_response as _service_response,
)
from services.management_gateway import (
    change_comment,
    change_consultant,
    change_password,
    change_setting,
    change_student,
    change_student_access,
    change_user_info,
    change_user_quiz_setting,
    get_consultants,
    get_dashboard,
    get_management_report,
    get_report,
    get_students,
)


def service_response(method_type, tracking_token, response_data=None, response_message="", error_message=None,
                     **extra_response):
    return _service_response(method_type, tracking_token, response_data, response_message, error_message,
                             **extra_response)
