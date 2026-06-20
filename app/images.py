"""Image preparation helpers for vision model requests."""

from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image

JPEG_DATA_URL_PREFIX = "data:image/jpeg;base64,"


def prepare_image_data_url(
    image_bytes: bytes,
    *,
    max_dimension: int,
    rotate_degrees: int = 0,
) -> str:
    """Resize and optionally rotate image bytes, returning a JPEG data URL."""
    with Image.open(BytesIO(image_bytes)) as image:
        if rotate_degrees:
            image = image.rotate(-rotate_degrees, expand=True)

        width, height = image.size
        longest_side = max(width, height)
        if longest_side > max_dimension:
            scale = max_dimension / longest_side
            image = image.resize(
                (int(width * scale), int(height * scale)),
                Image.Resampling.LANCZOS,
            )

        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=85)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return f"{JPEG_DATA_URL_PREFIX}{encoded}"
