"""
Create a demonstration GIF from generated mission snapshot PNG files.
This avoids FFmpeg and works on Windows using Pillow.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse


def make_gif(snapshot_dir: str, output_file: str, duration_ms: int = 1200):
    source_dir = Path(snapshot_dir)
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Snapshot directory not found: {source_dir}. "
            "Run: python generate_demo_snapshots.py 3"
        )

    png_files = sorted(source_dir.glob("snapshot_*.png"))
    if not png_files:
        raise FileNotFoundError(
            f"No snapshot_*.png files found in {source_dir}. "
            "Run: python generate_demo_snapshots.py 3"
        )

    frames = []
    target_size = None

    for idx, png_path in enumerate(png_files, start=1):
        img = Image.open(png_path).convert("RGB")

        # Resize to a judge-friendly GIF size while preserving aspect ratio.
        if target_size is None:
            max_width = 1200
            if img.width > max_width:
                ratio = max_width / img.width
                target_size = (max_width, int(img.height * ratio))
            else:
                target_size = img.size

        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        # Add a small caption overlay with frame number and source file.
        draw = ImageDraw.Draw(img)
        caption = f"AeroMesh-Swarm Demo | Frame {idx}/{len(png_files)} | {png_path.stem}"
        padding = 12
        box_height = 42
        draw.rectangle(
            [(0, img.height - box_height), (img.width, img.height)],
            fill=(10, 15, 30),
        )
        draw.text((padding, img.height - 30), caption, fill=(255, 255, 255))

        frames.append(img)

    output_path = Path(output_file)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print("[+] Demo GIF created successfully")
    print(f"    Input snapshots : {source_dir}")
    print(f"    Frames          : {len(frames)}")
    print(f"    Output          : {output_path}")
    print(f"    Size            : {size_mb:.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create AeroMesh-Swarm demonstration GIF from PNG snapshots")
    parser.add_argument("--snapshot-dir", default="scenario_3_snapshots", help="Directory containing snapshot_*.png files")
    parser.add_argument("--output", default="scenario_3_demo.gif", help="Output GIF file")
    parser.add_argument("--duration", type=int, default=1200, help="Frame duration in milliseconds")
    args = parser.parse_args()

    make_gif(args.snapshot_dir, args.output, args.duration)
