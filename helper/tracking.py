import uuid


def get_tracking_code() -> str:
    return str(uuid.uuid4())
