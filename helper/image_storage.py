from helper import file_helper
from helper.tracking import get_tracking_code


def save_base64_image(pic_value: str | None, last_pic: str | None, storage_dir: str) -> str | None:
    if not pic_value:
        return None

    if not pic_value.startswith("data:image"):
        return pic_value

    image_bytes, extension = file_helper.decode_base64_image(pic_value)
    new_file_name = f"{get_tracking_code()}{extension}"
    file_helper.write_storage_file(storage_dir, new_file_name, image_bytes)
    file_helper.remove_storage_file(storage_dir, last_pic)

    return new_file_name
