import json
import logging
from typing import Any, Optional
from kavenegar import KavenegarAPI, APIException, HTTPException

from config import KAVENEGAR_API_KEY, KAVENEGAR_OTP_TEMPLATE
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.otp import create_otp_log


logger = logging.getLogger(__name__)


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
        if not KAVENEGAR_API_KEY:
            logger.error("AG_KAVENEGAR_API_KEY is not configured")
            return None
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
        except Exception:
            logger.exception("otp_logs failed")
        return response
    except APIException:
        logger.exception("Kavenegar API error")
        return None
    except HTTPException:
        logger.exception("Kavenegar HTTP error")
        return None
    except Exception:
        logger.exception("Kavenegar unexpected error")
        return None
