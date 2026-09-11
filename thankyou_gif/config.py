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
    "envelope_open": "envelope_open.jpg",    # flap lifted up, grey liner + mouth open
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
    "envelope_open": (0.1253, 0.1972, 0.8546, 0.8560),
    "card_cover": (0.1356, 0.3398, 0.8505, 0.6953),
    "card_open": (0.1734, 0.1712, 0.8318, 0.8308),
}

# In the open-envelope photo the flap lifts up, so the object is much taller
# than the closed envelope. The card slides out of the mouth (the envelope's
# widest point / shoulders, where the grey liner opening is); this is that
# mouth's height above the envelope's bottom edge, as a fraction of the open
# bbox height. Measured at ~0.315 (shoulders sit ~0.685 down from the top).
ENVELOPE_MOUTH_FROM_BOTTOM_FRAC = 0.315

# Horizontal fold line inside card_open, as a fraction of the card's own
# bbox height (0 = top edge of card, 1 = bottom edge).
CARD_FOLD_FRAC = 0.498

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

CANVAS_SIZE = (544, 765)  # output GIF pixel size (width, height); sized to keep the file well under corporate email caps
BG_COLOR = (255, 255, 255)  # plain white background (no leather)
GIF_COLORS = 132          # palette size for the single shared GIF palette (see pipeline.py)

# The card and envelope are photographed on maroon leather; to sit them on a
# clean white background they're cut out of their photos (imaging.extract_object)
# by thresholding the bright paper off the dark leather, filling interior holes
# (so dark ink strokes inside stay opaque), and keeping the largest piece.
OBJECT_MASK_THRESHOLD = 118  # luminance above this is object, below is leather
OBJECT_MASK_ERODE = 4        # px pulled in from the mask edge to drop leather fringe
OBJECT_EDGE_FEATHER = 1.2    # px softening on the cutout edge (anti-aliasing)

# Width objects are scaled to on canvas, and duration to fit within before
# padding to keep frames visually consistent across stages that mix
# landscape (envelope, closed card) and portrait (open card) subjects.
ENVELOPE_TARGET_WIDTH = 500
CARD_TARGET_WIDTH = 480

# Objects are cut out as RGBA and carry their own alpha edge, so no rectangle
# feather is applied on paste.
PASTE_FEATHER_PX = 0

# Contact shadow under objects. Off (0) -- the pieces sit flat on plain white,
# per the founder's call. The machinery stays so it can be re-enabled.
OBJECT_SHADOW_STRENGTH = 0.0   # 0 = none
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
# are bottom-aligned at ENVELOPE_BOTTOM_Y_FRAC so the flap lifts upward from a
# fixed base when it opens (the open envelope is much taller than the closed
# one). The card docks with its top edge (its hinge, since the card is
# top-folded) at CARD_HINGE_Y_FRAC and opens from there.
ENVELOPE_BOTTOM_Y_FRAC = 0.82
CARD_HINGE_Y_FRAC = 0.46

# --- Timing -------------------------------------------------------------------
# Each stage: (frame_count, ms_per_frame). Slow + eased, per "smooth and
# slow feels premium" -- nothing here is snappy on purpose.

# Holds are effectively free -- consecutive identical frames are collapsed by
# the GIF optimizer into one long-duration frame -- so their frame counts are
# just how long to dwell. The transition frame counts are the whole file-size
# cost (every frame differs), so they're kept lean while staying smooth.
TIMING = {
    "hold_envelope_front": (16, 60),
    "turn_envelope": (20, 50),
    "hold_envelope_back": (10, 60),
    "flap_open": (16, 52),
    "hold_envelope_open": (10, 60),
    "card_pull": (12, 55),      # card rises out of the envelope mouth, envelope fixed
    "card_settle": (10, 55),    # crossfades envelope away, card drifts to its rest spot
    "hold_card_cover": (12, 70),
    "card_open": (22, 55),      # cover lifts away, note unfolds in beneath it
    "hold_final": (30, 80),
}

# How far above the envelope's mouth the card rests once fully pulled clear,
# before settling into its final cover-hold position (px on canvas).
CARD_CLEAR_MARGIN = 22

LOOP = None  # None = play once, freeze on the final still (no GIF loop extension written)
