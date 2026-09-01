import base64
import binascii
import os
from pathlib import Path
from typing import BinaryIO


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VOICE_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".webm", ".aac", ".mp4"}
VOICE_CONTENT_TYPES = {
    "application/octet-stream",
    "audio/aac",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/x-aac",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/ogg",
    "audio/webm",
    "video/webm",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_VOICE_BYTES = 20 * 1024 * 1024


class FileValidationError(ValueError):
    pass


def normalize_storage_filename(filename: str | None) -> str:
    if not filename:
        raise FileValidationError("File name is empty.")

    clean_name = Path(str(filename)).name
    if clean_name != filename or clean_name in {"", ".", ".."} or "\\" in clean_name:
        raise FileValidationError("File name is not valid.")
    return clean_name


def safe_storage_path(storage_dir: str, filename: str) -> str:
    clean_name = normalize_storage_filename(filename)
    base_path = Path(storage_dir).resolve()
    file_path = (base_path / clean_name).resolve()
    try:
        file_path.relative_to(base_path)
    except ValueError as exc:
        raise FileValidationError("File path is outside storage directory.") from exc
    return str(file_path)


def get_extension(filename: str | None, allowed_extensions: set[str]) -> str:
    clean_name = normalize_storage_filename(filename)
    extension = Path(clean_name).suffix.lower()
    if extension not in allowed_extensions:
        raise FileValidationError("File extension is not allowed.")
    return extension


def validate_content_type(content_type: str | None, allowed_content_types: set[str]) -> None:
    if content_type and content_type.lower() not in allowed_content_types:
        raise FileValidationError("File content type is not allowed.")


def read_limited_file(file_obj: BinaryIO, max_bytes: int) -> bytes:
    content = file_obj.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise FileValidationError("File is too large.")
    if not content:
        raise FileValidationError("File is empty.")
    return content


def write_storage_file(storage_dir: str, filename: str, content: bytes) -> str:
    os.makedirs(storage_dir, exist_ok=True)
    file_path = safe_storage_path(storage_dir, filename)
    with open(file_path, "wb") as file_object:
        file_object.write(content)
    return file_path


def remove_storage_file(storage_dir: str, filename: str | None) -> None:
    if not filename:
        return
    try:
        file_path = safe_storage_path(storage_dir, filename)
    except FileValidationError:
        return
    if os.path.isfile(file_path):
        os.remove(file_path)


def decode_base64_image(pic_value: str, max_bytes: int = MAX_IMAGE_BYTES) -> tuple[bytes, str]:
    if "," not in pic_value:
        raise FileValidationError("Image data URL is not valid.")

    header, encoded_data = pic_value.split(",", 1)
    media_type = header.split(";", 1)[0].lower()
    if not media_type.startswith("data:image/"):
        raise FileValidationError("Image media type is not valid.")

    extension = media_type.replace("data:image/", ".", 1)
    if extension == ".jpeg":
        extension = ".jpg"
    if extension not in IMAGE_EXTENSIONS:
        raise FileValidationError("Image extension is not allowed.")

    compact_data = "".join(encoded_data.split())
    if len(compact_data) > (max_bytes * 4 // 3) + 8:
        raise FileValidationError("Image is too large.")

    try:
        image_bytes = base64.b64decode(compact_data, validate=True)
    except binascii.Error as exc:
        raise FileValidationError("Image base64 payload is not valid.") from exc

    if len(image_bytes) > max_bytes:
        raise FileValidationError("Image is too large.")
    if not _image_bytes_match_extension(image_bytes, extension):
        raise FileValidationError("Image bytes do not match extension.")

    return image_bytes, extension


def _image_bytes_match_extension(image_bytes: bytes, extension: str) -> bool:
    if extension == ".jpg":
        return image_bytes.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"
    return False
