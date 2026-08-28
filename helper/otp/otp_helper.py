import json
from typing import Any, Optional
from kavenegar import KavenegarAPI, APIException, HTTPException

from config import KAVENEGAR_API_KEY, KAVENEGAR_OTP_TEMPLATE
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.otp import create_otp_log


def send_otp_message(code: str | int, phone: str, type: str) -> Optional[dict[str, Any]]:
    """
    Send an OTP code via Kavenegar SMS service.

    Args:
        code: The OTP code to send.
        phone: The recipient phone number.

    Returns:
        Response dictionary from Kavenegar API on success, None on failure.
    """
    try:
        api = KavenegarAPI(KAVENEGAR_API_KEY)
        params = {
            'receptor': phone,
            'token': code,
            'template': KAVENEGAR_OTP_TEMPLATE
        }
        response = api.verify_lookup(params=params)
        try:
            with session_scope() as session:
                create_otp_log(
                    session=session,
                    phone=phone,
                    code=code,
                    provider_resp=json.dumps(response, ensure_ascii=False),
                    type_otp=type,
                )
        except Exception as e:
            print(f"[Logging Error] otp_logs failed: {e}")
        return response
    except APIException as e:
        print(f"[Kavenegar API Error] {e}")
        return None
    except HTTPException as e:
        print(f"[Kavenegar HTTP Error] {e}")
        return None
    except Exception as e:
        print(f"[Kavenegar Unexpected Error] {e}")
        return None
