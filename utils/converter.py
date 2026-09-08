import base64
import io
from PIL import Image, ImageOps

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

SUPPORTED_MIME_TYPES = {
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/gif": "GIF",
    "image/bmp": "BMP",
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def process_image_bytes(image_bytes: bytes, original_filename: str = None) -> dict:
    """
    Validates, detects metadata, and encodes image bytes to Base64 and Data URI formats.
    """
    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError("SIZE_EXCEEDED")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        image = Image.open(io.BytesIO(image_bytes))
    except Exception:
        raise ValueError("INVALID_IMAGE")

    img_format = image.format.upper() if image.format else None
    if img_format == "JPEG":
        mime_type = "image/jpeg"
        ext = "jpg"
    elif img_format == "PNG":
        mime_type = "image/png"
        ext = "png"
    elif img_format == "WEBP":
        mime_type = "image/webp"
        ext = "webp"
    elif img_format == "GIF":
        mime_type = "image/gif"
        ext = "gif"
    elif img_format == "BMP":
        mime_type = "image/bmp"
        ext = "bmp"
    else:
        raise ValueError("UNSUPPORTED_FORMAT")

    base64_str = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{base64_str}"

    filename = original_filename if original_filename else f"converted_image.{ext}"

    return {
        "filename": filename,
        "size_bytes": len(image_bytes),
        "mime_type": mime_type,
        "format_name": img_format,
        "base64": base64_str,
        "data_uri": data_uri,
    }


def format_txt_export(data: dict) -> bytes:
    """
    Formats metadata and base64 strings into a downloadable text file buffer.
    """
    content = (
        f"File Name: {data['filename']}\n"
        f"MIME Type: {data['mime_type']}\n"
        f"Format: {data['format_name']}\n"
        f"Size: {data['size_bytes']} bytes\n"
        f"{'='*50}\n\n"
        f"--- DATA URI ---\n"
        f"{data['data_uri']}\n\n"
        f"--- RAW BASE64 STRING ---\n"
        f"{data['base64']}\n"
    )
    return content.encode("utf-8")
