import subprocess
import os
import glob
import re
import json
from tqdm import tqdm

CHUNK_SIZE = 250_000_000_000  # 250 GB in bytes

def get_video_duration(path):
    """Return duration (seconds) via ffprobe JSON."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-i", path
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        info = json.loads(proc.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0

def split_file(input_path):
    # strip quotes, resolve abs path
    inp = input_path.strip().strip('"').strip("'")
    full = os.path.abspath(inp)
    base, ext = os.path.splitext(full)
    size = os.path.getsize(full)

    print(f"\nFile:  {full}")
    print(f"Size:  {size} bytes")
    print(f"Limit: {CHUNK_SIZE} bytes (~250 GB)\n")

    if size <= CHUNK_SIZE:
        print("→ Under 250 GB, no split needed.")
        return

    total_dur = get_video_duration(full)
    if total_dur <= 0:
        print("WARNING: Could not read total duration; proceeding by size only.")

    offset = 0.0
    part = 1

    # Loop until we've covered the whole file
    while True:
        out_name = f"{base}_Part-{part}{ext}"
        if os.path.exists(out_name):
            os.remove(out_name)

        print(f"→ Generating part {part} (seek {offset:.1f}s)…")
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "info",
            "-ss", str(offset),
            "-i", full,
            "-c", "copy",
            "-map", "0",
            "-fs", str(CHUNK_SIZE),
            out_name
        ]
        subprocess.run(cmd, check=True)

        if not os.path.exists(out_name):
            print("ERROR: failed to create segment; aborting.")
            break

        part_dur = get_video_duration(out_name)
        part_size = os.path.getsize(out_name)
        print(f"   → Produced {out_name}: {part_size} bytes, {part_dur:.1f}s")

        # If we got nothing or no duration, stop
        if part_dur < 0.5:
            print("   → Part is effectively empty; stopping.")
            break

        offset += part_dur
        part += 1

        # If we know total duration and have covered it, stop
        if total_dur > 0 and offset >= total_dur - 1:
            print("   → Reached end of source.")
            break

    print("\nDone splitting.")

if __name__ == "__main__":
    path = input("Enter path to MKV file: ")
    split_file(path)
