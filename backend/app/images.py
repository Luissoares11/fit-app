from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()  # lets Pillow open HEIC photos from phones


class InvalidImage(Exception):
    pass


def save_photo(source: BinaryIO, folder: Path, angle: str) -> None:
    """Re-encode as JPEG (drops EXIF/GPS), fix rotation, write full size + thumbnail."""
    try:
        img = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
    except Exception as exc:
        raise InvalidImage("Not a valid image") from exc

    img.thumbnail((2000, 2000))
    folder.mkdir(parents=True, exist_ok=True)
    img.save(folder / f"{angle}.jpg", "JPEG", quality=88)

    thumb = img.copy()
    thumb.thumbnail((400, 400))
    thumb.save(folder / f"{angle}_thumb.jpg", "JPEG", quality=80)