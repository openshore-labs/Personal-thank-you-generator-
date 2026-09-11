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

# Where the handwritten note gets composited, as a quad (TL, TR, BR, BL) in
# fractions of card_open's own bbox. Starts as an axis-aligned rectangle in
# the bottom half (below the fold); edit individual corners here to true up
# perspective once real note photos are in and something looks skewed.
NOTE_QUAD_FRAC = (
    (0.10, 0.560),  # top-left
    (0.90, 0.560),  # top-right
    (0.90, 0.960),  # bottom-right
    (0.10, 0.960),  # bottom-left
)

# --- Canvas & look ------------------------------------------------------------

CANVAS_SIZE = (400, 560)  # output GIF pixel size (width, height) -- kept modest, GIF/LZW compresses photo texture poorly
BG_COLOR = (61, 16, 16)   # sampled from the leather backdrop, used for letterboxing
GIF_COLORS = 96           # palette size passed to Pillow's GIF quantizer

# Width objects are scaled to on canvas, and duration to fit within before
# padding to keep frames visually consistent across stages that mix
# landscape (envelope, closed card) and portrait (open card) subjects.
ENVELOPE_TARGET_WIDTH = 350
CARD_TARGET_WIDTH = 350

# Vertical staging, as fractions of CANVAS_SIZE height. The envelope scenes
# sit higher on the canvas; the card docks with its top edge (its hinge,
# since the card is top-folded) at CARD_HINGE_Y_FRAC and opens from there.
ENVELOPE_CENTER_Y_FRAC = 0.30
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
