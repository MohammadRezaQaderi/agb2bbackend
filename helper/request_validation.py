from typing import Any, Mapping

from helper.service_errors import key_error_message_return


def validate_request_data_fields(
        request_data: Mapping[str, Any],
        required_fields: list[str],
        method_type: str,
):
    """
    Validate that all fields exist and are not empty in request_data.

    Returns:
        (True, None) if all fields are present,
        (False, error_response_dict) if any field is missing.
    """
    for field in required_fields:
        if field not in request_data or request_data[field] in (None, ''):
            return False, key_error_message_return(field, method_type)
    return True, None
