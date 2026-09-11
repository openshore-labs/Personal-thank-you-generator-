"""Low-level image helpers: loading, cropping to a measured bbox, easing,
and the generic pivoted "flip" transition used for both the envelope
turning around and the card lid opening (same squash-and-swap trick, just
on different axes with different pivot points).
"""

import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import background, config


def load_source(name):
    path = os.path.join(config.SOURCE_DIR, config.FILES[name])
    return Image.open(path).convert("RGB")


def bbox_px(name, img_size):
    """Pixel bbox (x0, y0, x1, y1) for a named asset, scaled to img_size."""
    w, h = img_size
    x0f, y0f, x1f, y1f = config.BBOX_FRAC[name]
    return (round(x0f * w), round(y0f * h), round(x1f * w), round(y1f * h))


def crop_to_bbox(img, name, pad_frac=0.015):
    """Crop img to its measured object bbox, with a little breathing room."""
    x0, y0, x1, y1 = bbox_px(name, img.size)
    pw, ph = round((x1 - x0) * pad_frac), round((y1 - y0) * pad_frac)
    x0, y0 = max(0, x0 - pw), max(0, y0 - ph)
    x1, y1 = min(img.width, x1 + pw), min(img.height, y1 + ph)
    return img.crop((x0, y0, x1, y1))


def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def fit_width(img, target_width):
    w, h = img.size
    scale = target_width / w
    return img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


def blank_canvas():
    return background.leather_canvas().copy()


def _feathered_mask(size, feather_px):
    """Solid-white mask the size of an object crop, with its border feathered
    inward so the paste dissolves into the background over `feather_px`."""
    w, h = size
    mask = Image.new("L", (w, h), 0)
    inset = feather_px
    ImageDraw.Draw(mask).rectangle(
        (inset, inset, w - 1 - inset, h - 1 - inset), fill=255
    )
    return mask.filter(ImageFilter.GaussianBlur(feather_px / 2))


def _object_mask(img, feather_px):
    """The paste mask for an object: its own alpha if it carries one (e.g. a
    sheared image with transparent corners), otherwise a solid rectangle,
    with the outer edge feathered so it dissolves into the background."""
    if img.mode == "RGBA":
        base = img.getchannel("A")
    else:
        base = Image.new("L", img.size, 255)
    if feather_px:
        feather = _feathered_mask(img.size, feather_px)
        base = ImageChops.multiply(base, feather)
    return base


def _draw_contact_shadow(frame, obj_mask, topleft, strength):
    """Darken `frame` (in place) with a soft blurred shadow the shape of the
    object (obj_mask), offset by config.OBJECT_SHADOW_OFFSET, so the object
    reads as resting on the leather rather than stamped on it."""
    if strength <= 0:
        return
    dx, dy = config.OBJECT_SHADOW_OFFSET
    x, y = topleft
    sil = Image.new("L", frame.size, 0)
    sil.paste(obj_mask, (x + dx, y + dy))
    sil = sil.filter(ImageFilter.GaussianBlur(config.OBJECT_SHADOW_BLUR))
    sil = sil.point(lambda a: int(a * strength))
    frame.paste(Image.new("RGB", frame.size, (0, 0, 0)), (0, 0), sil)


def paste_with_pivot(
    canvas, img, anchor_point, pivot_frac=(0.5, 0.5), feather_px=None, shadow=0.0
):
    """Paste img onto a copy of canvas such that the point at
    (pivot_frac[0]*img.width, pivot_frac[1]*img.height) lands on
    anchor_point (x, y) in canvas coordinates. When feather_px is set, the
    object's rectangular edge is softened into the background over that many
    px (defaults to config.PASTE_FEATHER_PX; pass 0 to disable). When shadow
    > 0, a soft contact shadow at that strength is drawn under the object.
    Respects the image's own alpha when it has one."""
    frame = canvas.copy()
    px_frac, py_frac = pivot_frac
    ax, ay = anchor_point
    x = round(ax - px_frac * img.width)
    y = round(ay - py_frac * img.height)
    fp = config.PASTE_FEATHER_PX if feather_px is None else feather_px
    fp = fp if (fp and img.width > 2 * fp and img.height > 2 * fp) else 0
    mask = _object_mask(img, fp)
    if shadow:
        _draw_contact_shadow(frame, mask, (x, y), shadow)
    frame.paste(img.convert("RGB"), (x, y), mask)
    return frame


def hold(img, n_frames, anchor_point, pivot_frac=(0.5, 0.5)):
    frame = paste_with_pivot(
        blank_canvas(), img, anchor_point, pivot_frac, shadow=config.OBJECT_SHADOW_STRENGTH
    )
    return [frame.copy() for _ in range(n_frames)]


def _shear_about_pivot(img, axis, shear_k, pivot):
    """Shear img along the cross-axis about its pivot line, expanding the
    canvas so nothing clips. Returns (sheared_img, new_pivot_frac) where the
    pivot point is preserved. shear_k is signed slope. For a 'y' (lid) flip
    this is a horizontal shear about the hinge row; for an 'x' (turn) flip a
    vertical shear about the seam column."""
    w, h = img.size
    if axis == "y":
        yp = pivot * h
        pad = int(abs(shear_k) * h) + 1
        canvas = Image.new("RGBA", (w + 2 * pad, h), (0, 0, 0, 0))
        canvas.paste(img.convert("RGBA"), (pad, 0))
        # output_x samples input at x - k*(y - yp); +pad keeps content in frame
        out = canvas.transform(
            canvas.size, Image.AFFINE,
            (1, -shear_k, shear_k * yp, 0, 1, 0), resample=Image.BICUBIC,
        )
        new_pivot = ((pad + w * 0.5) / out.width, pivot)
        return out, new_pivot
    else:
        xp = pivot * w
        pad = int(abs(shear_k) * w) + 1
        canvas = Image.new("RGBA", (w, h + 2 * pad), (0, 0, 0, 0))
        canvas.paste(img.convert("RGBA"), (0, pad))
        out = canvas.transform(
            canvas.size, Image.AFFINE,
            (1, 0, 0, -shear_k, 1, shear_k * xp), resample=Image.BICUBIC,
        )
        new_pivot = (pivot, (pad + h * 0.5) / out.height)
        return out, new_pivot


def flip_transition(
    img_a, img_b, axis, n_frames, anchor_point,
    pivot_frac_a=0.5, pivot_frac_b=0.5, cross_pivot=0.5, ease=ease_in_out_cubic,
):
    """Frames of img_a squashing flat and un-squashing into img_b, mimicking
    a card/envelope flipping over.

    axis: 'x' scales width (turning left/right around a vertical seam),
          'y' scales height (opening like a lid around a horizontal hinge).
    anchor_point: canvas (x, y) that stays fixed as the scaling axis pivots.
    pivot_frac_a / pivot_frac_b: where, along the scaling axis (0=leading
        edge, 0.5=center, 1=trailing edge) of img_a / img_b, the anchor
        point sits. E.g. for a lid hinged at its top edge, pivot_frac=0.
    cross_pivot: where the anchor sits on the OTHER axis (the one not being
        scaled). 0.5 centers; 1.0 bottom-aligns a 'y' flip / right-aligns an
        'x' flip. Used to keep an envelope's bottom edge fixed while its flap
        grows upward.
    """
    frames = []
    for i in range(n_frames):
        t = i / (n_frames - 1) if n_frames > 1 else 1.0
        te = ease(t)
        scale = max(abs(math.cos(math.pi * te)), 0.01)
        use_b = te > 0.5
        src = img_b if use_b else img_a
        pivot = pivot_frac_b if use_b else pivot_frac_a
        w, h = src.size
        if axis == "x":
            new_w, new_h = max(1, round(w * scale)), h
            pivot_frac = (pivot, cross_pivot)
        else:
            new_w, new_h = w, max(1, round(h * scale))
            pivot_frac = (cross_pivot, pivot)
        resized = src.resize((new_w, new_h), Image.LANCZOS)

        # Foreshortening shear, peaking mid-flip and zero at the flat ends so
        # it blends into the neighbouring holds. Applied to the already-squashed
        # image about its pivot line.
        if config.FLIP_SHEAR:
            k = config.FLIP_SHEAR * math.sin(math.pi * te)
            resized, pivot_frac = _shear_about_pivot(resized, axis, k, pivot)

        # Fade the contact shadow with the squash factor: full at the flat
        # start/end (matching the neighbouring holds, so no pop), gone when
        # the object is edge-on and casts no footprint.
        frames.append(paste_with_pivot(
            blank_canvas(), resized, anchor_point, pivot_frac,
            shadow=config.OBJECT_SHADOW_STRENGTH * scale,
        ))
    return frames


def slide_reveal(img, n_frames, x, y_start, y_end, bg_start, bg_end=None, ease=ease_in_out_cubic):
    """img's top edge translates from y_start to y_end (horizontally centered
    on x), mimicking the card sliding up out of the envelope. The background
    crossfades from bg_start (the open envelope) to bg_end (plain leather) over
    the slide, so the tall open envelope dissolves away as the card emerges
    rather than popping out at the following hold. bg_end defaults to
    bg_start (no fade)."""
    if bg_end is None:
        bg_end = bg_start
    frames = []
    for i in range(n_frames):
        t = i / (n_frames - 1) if n_frames > 1 else 1.0
        te = ease(t)
        y = round(y_start + (y_end - y_start) * te)
        background = Image.blend(bg_start, bg_end, te)
        frame = paste_with_pivot(
            background, img, (x, y), pivot_frac=(0.5, 0.0),
            shadow=config.OBJECT_SHADOW_STRENGTH,
        )
        frames.append(frame)
    return frames


def feather_alpha(mask_img, radius):
    return mask_img.filter(ImageFilter.GaussianBlur(radius))
