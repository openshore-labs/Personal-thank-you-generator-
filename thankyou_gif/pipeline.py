import os

from PIL import Image

from . import config, stages


def _shared_palette(frames):
    """One palette for the whole GIF. Quantizing each frame independently
    gives every frame its own slightly different palette, which reads as a
    faint dither shimmer across the photographed paper/leather grain. Deriving
    a single palette from a montage of frames sampled across the sequence and
    reusing it for all of them keeps the texture stable frame-to-frame."""
    step = max(1, len(frames) // 12)
    sampled = frames[::step]
    w, h = frames[0].size
    montage = Image.new("RGB", (w, h * len(sampled)))
    for i, f in enumerate(sampled):
        montage.paste(f, (0, i * h))
    return montage.quantize(colors=config.GIF_COLORS, method=Image.Quantize.MEDIANCUT)


def render(note_path=None, address_path=None, output_path=None):
    frames_with_timing = stages.build_frames(note_path, address_path)
    frames = [f for f, _ in frames_with_timing]
    durations = [ms for _, ms in frames_with_timing]

    palette = _shared_palette(frames)
    # No dithering: Floyd-Steinberg's error-diffusion noise both shimmers
    # frame-to-frame on the photographed grain and roughly doubles the file
    # size (LZW can't pack the noise). At GIF_COLORS the soft paper/leather
    # gradients quantize cleanly enough without it.
    quantized = [
        f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames
    ]

    output_path = output_path or os.path.join(config.OUTPUT_DIR, "thank_you.gif")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    save_kwargs = dict(
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        optimize=True,
    )
    if config.LOOP is not None:
        save_kwargs["loop"] = config.LOOP  # omitted entirely = plays once, freezes on last frame
    quantized[0].save(output_path, **save_kwargs)
    return output_path
