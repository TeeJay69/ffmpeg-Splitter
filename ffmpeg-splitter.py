import subprocess
import os
import json

CHUNK_SIZE = 250_000_000_000  # 250 GB in bytes
MAX_DURATION = (12 * 60 * 60) - 60  # 11h 59m safety margin for YouTube


def get_video_duration(path):
    """Return duration in seconds via ffprobe JSON."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-i", path
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        info = json.loads(proc.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0


def split_file(input_path):
    inp = input_path.strip().strip('"').strip("'")
    full = os.path.abspath(inp)

    if not os.path.exists(full):
        print("ERROR: File does not exist.")
        return

    base, ext = os.path.splitext(full)

    size = os.path.getsize(full)
    total_dur = get_video_duration(full)

    print(f"\nFile: {full}")
    print(f"Size: {size:,} bytes")
    print(f"Max size per part: {CHUNK_SIZE:,} bytes (~250 GB)")
    print(f"Duration: {total_dur / 3600:.2f} hours")
    print(f"Max duration per part: {MAX_DURATION / 3600:.2f} hours\n")

    if total_dur <= 0:
        print("WARNING: Could not read total duration.")

    # Skip splitting if BOTH conditions are below limit
    if size <= CHUNK_SIZE and (total_dur <= 0 or total_dur <= MAX_DURATION):
        print("→ Under size and duration limits, no split needed.")
        return

    offset = 0.0
    part = 1

    while True:
        out_name = f"{base}_Part-{part}{ext}"

        if os.path.exists(out_name):
            os.remove(out_name)

        print(f"→ Generating part {part} at seek {offset:.1f}s...")

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "info",
            "-ss", str(offset),
            "-i", full,

            # stop at 11h59m max
            "-t", str(MAX_DURATION),

            # no re-encode
            "-c", "copy",

            # copy all streams
            "-map", "0",

            # stop at 250GB max
            "-fs", str(CHUNK_SIZE),

            out_name
        ]

        subprocess.run(cmd, check=True)

        if not os.path.exists(out_name):
            print("ERROR: Failed to create segment.")
            break

        part_dur = get_video_duration(out_name)
        part_size = os.path.getsize(out_name)

        print(
            f"   → Produced {out_name}\n"
            f"      Size: {part_size:,} bytes\n"
            f"      Duration: {part_dur / 3600:.2f} hours"
        )

        # Empty output protection
        if part_dur < 0.5:
            print("   → Part is effectively empty; stopping.")
            break

        offset += part_dur
        part += 1

        # Finished source
        if total_dur > 0 and offset >= total_dur - 1:
            print("   → Reached end of source.")
            break

    print("\nDone splitting.")


if __name__ == "__main__":
    path = input("Enter path to MKV file: ")
    split_file(path)