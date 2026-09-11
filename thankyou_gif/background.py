"""Builds the canvas background from a real leather patch sampled out of one
of the source photos, so objects sit on the same textured surface they were
shot on rather than a flat color (which reads as a hard seam around every
object). Cached -- the same leather field is reused for every frame so the
backdrop is stable across the whole animation.
"""

import os

import numpy as np
from PIL import Image

from . import config

_cache = None


def _load_sample():
    src = config.FILES[config.LEATHER_SAMPLE_SOURCE]
    img = Image.open(os.path.join(config.SOURCE_DIR, src)).convert("RGB")
    w, h = img.size
    x0f, y0f, x1f, y1f = config.LEATHER_SAMPLE_FRAC
    return img.crop((round(x0f * w), round(y0f * h), round(x1f * w), round(y1f * h)))


def _mirror_tile(patch, size):
    """Fill `size` by repeating `patch`, flipping alternate copies so the
    repeat seams fall on mirrored (continuous) edges instead of hard cuts."""
    cw, ch = size
    patch = patch.resize((cw, round(cw * patch.height / patch.width)), Image.LANCZOS)
    pw, ph = patch.size
    flipped_v = patch.transpose(Image.FLIP_TOP_BOTTOM)
    field = Image.new("RGB", size)
    y = 0
    row = 0
    while y < ch:
        field.paste(patch if row % 2 == 0 else flipped_v, (0, y))
        y += ph
        row += 1
    return field


def _apply_vignette(img, strength):
    if strength <= 0:
        return img
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    cx, cy = w / 2, h / 2
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (cx ** 2 + cy ** 2)  # 0 center -> 1 corners
    factor = (1 - strength * d2)[..., None]
    arr = np.asarray(img, dtype=float) * factor
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8"), "RGB")


def leather_canvas():
    global _cache
    if _cache is None:
        try:
            field = _mirror_tile(_load_sample(), config.CANVAS_SIZE)
            _cache = _apply_vignette(field, config.LEATHER_VIGNETTE)
        except (FileNotFoundError, OSError):
            _cache = Image.new("RGB", config.CANVAS_SIZE, config.BG_COLOR)
    return _cache
