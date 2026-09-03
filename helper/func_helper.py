from helper.account_passwords import update_user_and_role_password
from helper.auth_context import authorizer
from helper.constants import (
    AG_QUIZ_NAME_TITLE,
    PACKAGES_DATA,
    PROVINCES,
    SCL_QUIZ_NAME_TITLE,
    get_kind_name,
)
from helper.health import health_payload, liveness_payload, readiness_payload
from helper.image_storage import save_base64_image
from helper.password_helper import (
    decrypt_password,
    encrypt_password,
    hash_password,
    is_password_hash,
    verify_password,
    verify_password_hash,
)
from helper.payments import get_payment_id, get_price_payment
from helper.quiz_metadata import get_quiz_name
from helper.random_generators import (
    random_generate_otp_code,
    random_generate_password,
    random_generate_phone,
    random_phone_candidate,
)
from helper.request_validation import validate_request_data_fields
from helper.service_errors import (
    exception_error_logging,
    exception_error_message_return,
    key_error_logging,
    key_error_message_return,
    not_auth_return,
    not_data_return,
    not_method_access_return,
    service_exception_error_logging,
)
from helper.student_access import (
    get_student_package_access_counts,
    update_student_access_and_capacity,
    upsert_student_package_access,
)
from helper.tracking import get_tracking_code
from helper.validators import check_security_code, is_valid_mobile, password_format_check
