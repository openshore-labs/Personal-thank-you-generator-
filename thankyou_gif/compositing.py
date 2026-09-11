"""Photo compositing: lifting the ink off a photo of handwriting so it can be
written onto the card interior / envelope front as if penned there.
"""

import numpy as np
from PIL import Image, ImageFilter

from . import config, imaging


def extract_ink(source):
    """Lift the handwriting off a photo of it on paper: returns an RGBA image
    where the pen strokes keep their natural colour and everything else (paper,
    lighting gradients, and the embossed show-through from writing on the pages
    above) is transparent, plus the tight bounding box of the ink.

    Works by dividing the photo by a local estimate of the paper tone (a
    max-filtered, heavily blurred copy), so only marks meaningfully darker
    than their surrounding paper survive -- faint embossing divides out to
    ~1.0 and drops away.
    """
    img = (source if isinstance(source, Image.Image) else Image.open(source)).convert("RGB")
    gray = img.convert("L")
    paper = gray.filter(
        ImageFilter.MaxFilter(2 * config.INK_MAX_RADIUS + 1)
    ).filter(ImageFilter.GaussianBlur(config.INK_BG_BLUR))

    darkness = np.clip(1 - np.asarray(gray, float) / np.clip(np.asarray(paper, float), 1, None), 0, 1)
    alpha = np.clip((darkness - config.INK_FLOOR) / (1 - config.INK_FLOOR) * config.INK_GAIN, 0, 1)
    a = (alpha * 255).astype("uint8")
    a[a < config.INK_CUTOFF] = 0  # kill faint embossing/noise so it leaves no ghost

    rgba = Image.fromarray(np.dstack([np.asarray(img), a]), "RGBA")
    ys, xs = np.where(a > config.INK_BBOX_THRESH)
    if not len(xs):
        return rgba, (0, 0, img.width, img.height)
    return rgba, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _rect_in_bbox(base_img, bbox_name, rect_frac):
    """Absolute px rect (x0,y0,x1,y1) from a fraction-of-object-bbox rect."""
    x0, y0, x1, y1 = imaging.bbox_px(bbox_name, base_img.size)
    bw, bh = x1 - x0, y1 - y0
    fx0, fy0, fx1, fy1 = rect_frac
    return (x0 + fx0 * bw, y0 + fy0 * bh, x0 + fx1 * bw, y0 + fy1 * bh)


def place_handwriting(base_img, photo_source, dst_rect, align):
    """Extract the ink from photo_source and write it onto base_img, scaled to
    fit within dst_rect (preserving the handwriting's aspect ratio) and aligned
    within it. align is (horizontal, vertical) from {left/center/right} x
    {top/center/bottom}."""
    ink, bbox = extract_ink(photo_source)
    crop = ink.crop(bbox)

    dw, dh = dst_rect[2] - dst_rect[0], dst_rect[3] - dst_rect[1]
    scale = min(dw / crop.width, dh / crop.height)
    nw, nh = max(1, round(crop.width * scale)), max(1, round(crop.height * scale))
    resized = crop.resize((nw, nh), Image.LANCZOS)

    ax = {"left": 0.0, "center": 0.5, "right": 1.0}[align[0]]
    ay = {"top": 0.0, "center": 0.5, "bottom": 1.0}[align[1]]
    x = round(dst_rect[0] + ax * (dw - nw))
    y = round(dst_rect[1] + ay * (dh - nh))

    out = base_img.convert("RGBA")
    out.alpha_composite(resized, (x, y))
    return out.convert("RGB")


def write_note(card_img, note_source):
    """Write the extracted note onto the open card's interior."""
    rect = _rect_in_bbox(card_img, "card_open", config.CARD_WRITE_RECT_FRAC)
    return place_handwriting(card_img, note_source, rect, config.CARD_WRITE_ALIGN)


def write_address(envelope_front_img, address_source):
    """Write the extracted address onto the envelope front."""
    rect = _rect_in_bbox(envelope_front_img, "envelope_front", config.ENVELOPE_ADDRESS_RECT_FRAC)
    return place_handwriting(envelope_front_img, address_source, rect, config.ENVELOPE_ADDRESS_ALIGN)
