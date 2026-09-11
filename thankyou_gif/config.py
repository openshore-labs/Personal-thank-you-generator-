"""
All the tunable geometry and timing for the thank-you GIF pipeline lives here.

The bounding boxes below were measured automatically (connected-component
analysis against the maroon leather backdrop) from the source photos in
assets/source/. They're stored as fractions of each source image's pixel
size, so a retaken photo at a different resolution still works as long as
the framing (object roughly centered, same backdrop) stays similar.

Run `python calibrate.py` after changing anything here -- it draws the boxes
and the note quad on top of the source photos so you can eyeball whether
they still line up before generating a full GIF.
"""

SOURCE_DIR = "assets/source"
NOTES_DIR = "assets/notes"
OUTPUT_DIR = "output"

SOURCE_IMAGE_SIZE = (1932, 2576)  # (width, height) of every photo as shot

# --- Source files -----------------------------------------------------------

FILES = {
    "envelope_front": "envelope_front.jpg",
    "envelope_back": "envelope_back.jpg",   # flap closed, PAPYRUS embossed
    "card_cover": "card_cover.jpg",         # closed card, "THANK YOU" face up
    "card_open": "card_open_blank.jpg",     # fully open card, both halves blank
}

# --- Measured bounding boxes --------------------------------------------------
# (x0_frac, y0_frac, x1_frac, y1_frac) of the object within its source photo,
# as fractions of SOURCE_IMAGE_SIZE. Measured via connected-component
# thresholding against the maroon backdrop -- good starting points, not
# hand-perfect, tune in calibrate.py's output if something looks off.

BBOX_FRAC = {
    "envelope_front": (0.1072, 0.3482, 0.8734, 0.7295),
    "envelope_back": (0.1605, 0.3506, 0.8737, 0.7027),
    "card_cover": (0.1356, 0.3398, 0.8505, 0.6953),
    "card_open": (0.1734, 0.1712, 0.8318, 0.8308),
}

# Horizontal fold line inside card_open, as a fraction of the card's own
# bbox height (0 = top edge of card, 1 = bottom edge).
CARD_FOLD_FRAC = 0.498

# The envelope's flap triangle within envelope_back, as fractions of the
# envelope's own bbox (0,0 = bbox top-left, 1,1 = bbox bottom-right).
# Base runs along the top edge, apex points down.
FLAP_TRIANGLE_FRAC = (
    (0.010, -0.015),  # top-left
    (0.980, -0.015),  # top-right
    (0.510, 0.790),  # apex
)

# --- Handwriting (note + envelope address) ------------------------------------
# The note and the envelope address are supplied as photos of real handwriting
# on paper. compositing.extract_ink lifts just the pen strokes off the paper so
# they can be written onto the card / envelope as if penned there (the card's
# and envelope's own paper grain then shows through the strokes). These tune
# that extraction; defaults were validated on the founder's own note photos.
INK_MAX_RADIUS = 7     # px; max-filter radius used to estimate the paper tone
INK_BG_BLUR = 60       # px; blur of that paper-tone estimate
INK_FLOOR = 0.30       # darkness below this (relative to local paper) is ignored
INK_GAIN = 1.7         # multiplies stroke opacity after the floor
INK_CUTOFF = 28        # final alpha below this is zeroed (kills faint ghosts)
INK_BBOX_THRESH = 95   # alpha above this counts toward the ink's tight bbox

# Where the note is written on the open card, as a fraction of the card's own
# bbox. The letter is a full page, so it fills most of the interior (the fold
# crease runs through it, exactly as it would on a real folded card) rather
# than being confined to the bottom half. Fit preserves the handwriting's
# aspect ratio; alignment is (horizontal, vertical).
CARD_WRITE_RECT_FRAC = (0.10, 0.07, 0.90, 0.94)
CARD_WRITE_ALIGN = ("center", "center")

# Where the address is written on the envelope front: centered, middle-aligned.
ENVELOPE_ADDRESS_RECT_FRAC = (0.12, 0.33, 0.88, 0.67)
ENVELOPE_ADDRESS_ALIGN = ("center", "center")

# --- Canvas & look ------------------------------------------------------------

CANVAS_SIZE = (640, 900)  # output GIF pixel size (width, height)
BG_COLOR = (61, 16, 16)   # flat fallback tone, only used if the leather sample can't load
GIF_COLORS = 160          # palette size for the single shared GIF palette (see pipeline.py)

# Real leather backdrop for the canvas, instead of a flat fill -- the objects
# then sit on the same textured surface they were photographed on, so their
# edges don't read as a hard texture-to-flat seam. This names a clean,
# object-free leather band in one source photo (fractions of that photo);
# background.py tiles + vignettes it to canvas size. Re-pick if a retake
# moves the objects.
LEATHER_SAMPLE_SOURCE = "envelope_front"
LEATHER_SAMPLE_FRAC = (0.0, 0.0, 1.0, 0.318)  # full-width band above the envelope
LEATHER_VIGNETTE = 0.28  # 0 = none, 1 = strong corner darkening

# Width objects are scaled to on canvas, and duration to fit within before
# padding to keep frames visually consistent across stages that mix
# landscape (envelope, closed card) and portrait (open card) subjects.
ENVELOPE_TARGET_WIDTH = 560
CARD_TARGET_WIDTH = 560

# How far the rectangular object crops are feathered into the leather
# background when pasted (px), so the thin real-leather ring around each
# crop dissolves into the canvas leather instead of ending at a hard edge.
PASTE_FEATHER_PX = 4

# Soft contact shadow under objects on the leather, so they sit on the
# surface instead of looking stamped onto it. During the flip transitions the
# strength is scaled by the object's squash factor (full when flat/facing the
# viewer, fading to none when edge-on) so it doesn't pop at stage boundaries.
OBJECT_SHADOW_STRENGTH = 0.30  # 0 = none
OBJECT_SHADOW_OFFSET = (7, 11)  # (dx, dy) px on the output canvas
OBJECT_SHADOW_BLUR = 16         # px

# Foreshortening shear on the flip transitions (envelope turn, card open):
# a small shear that peaks at mid-flip and returns to 0 at the flat ends, so
# the motion reads as a rotation through space rather than a flat squash.
# Shipped OFF: its peak lands where the object is edge-on (a thin strip, so
# the shear is barely visible), while it adds ~1.5 MB to the file and nudges
# it toward email size caps -- and the grounded pure-squash on real leather
# already reads clean and calm. It's a tested, alpha-correct knob: set a
# small value like 0.06 to turn the 3D turn/open on. 0 = off (pure squash).
FLIP_SHEAR = 0.0  # peak shear as a fraction of the object's cross-axis length

# Vertical staging, as fractions of CANVAS_SIZE height. The envelope scenes
# sit higher on the canvas; the card docks with its top edge (its hinge,
# since the card is top-folded) at CARD_HINGE_Y_FRAC and opens from there.
ENVELOPE_CENTER_Y_FRAC = 0.34
CARD_HINGE_Y_FRAC = 0.50

# --- Timing -------------------------------------------------------------------
# Each stage: (frame_count, ms_per_frame). Slow + eased, per "smooth and
# slow feels premium" -- nothing here is snappy on purpose.

TIMING = {
    "hold_envelope_front": (16, 60),
    "turn_envelope": (26, 45),
    "hold_envelope_back": (10, 60),
    "flap_open": (18, 45),
    "hold_envelope_open": (8, 60),
    "card_slide_out": (20, 45),
    "hold_card_cover": (12, 70),
    "card_open": (24, 45),
    "hold_final": (30, 80),
}

LOOP = None  # None = play once, freeze on the final still (no GIF loop extension written)
