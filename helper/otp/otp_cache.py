import json

from redis.exceptions import WatchError


def store_otp(cache, phone, code, purpose, ttl_seconds):
    cache.set(phone, json.dumps({"code": code, "type": purpose}), ttl_seconds)


def consume_otp(cache, phone, code, purpose):
    key = cache.make_key(phone)
    try:
        with cache.database.pipeline() as pipeline:
            pipeline.watch(key)
            cached_value = cache.get(phone)
            if cached_value is None:
                return "missing"

            record = json.loads(cached_value)
            if record.get("type") is None:
                return "missing"
            if record.get("type") != purpose or not str(code).isdecimal() or int(code) != record.get("code"):
                return "invalid"

            pipeline.multi()
            pipeline.delete(key)
            pipeline.execute()
            return "consumed"
    except WatchError:
        return "missing"
