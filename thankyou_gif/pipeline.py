import os

from PIL import Image

from . import config, stages


def render(note_path=None, output_path=None):
    frames_with_timing = stages.build_frames(note_path)
    frames = [f for f, _ in frames_with_timing]
    durations = [ms for _, ms in frames_with_timing]

    quantized = [
        f.convert("P", palette=Image.Palette.ADAPTIVE, colors=config.GIF_COLORS) for f in frames
    ]

    output_path = output_path or os.path.join(config.OUTPUT_DIR, "thank_you.gif")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    quantized[0].save(
        output_path,
        save_all=True,
        append_images=quantized[1:],
        duration=durations,
        loop=config.LOOP,
        optimize=False,
    )
    return output_path
