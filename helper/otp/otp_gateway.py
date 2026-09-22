from config import OTP_TTL_SECONDS, REDIS_CACHE_OTP
from helper.otp import otp_helper
from helper.otp.otp_cache import consume_otp, store_otp
from helper.random_generators import random_generate_otp_code


class OtpGateway:
    def __init__(self, redis_db):
        self.cache = redis_db.cache(REDIS_CACHE_OTP)

    def issue(self, phone, purpose):
        code = random_generate_otp_code(5)
        if otp_helper.send_otp_message(code=code, phone=phone, type=purpose.upper()) is None:
            return False
        store_otp(self.cache, phone, code, purpose, OTP_TTL_SECONDS)
        return True

    def consume(self, phone, code, purpose):
        return consume_otp(self.cache, phone, code, purpose)
