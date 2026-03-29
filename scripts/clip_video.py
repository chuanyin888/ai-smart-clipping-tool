#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

try:
    from scripts._ffmpeg import ffmpeg_exe
except ModuleNotFoundError:
    from _ffmpeg import ffmpeg_exe


def main() -> int:
    if len(sys.argv) != 5:
        print("Usage: clip_video.py input.mp4 start_sec end_sec output.mp4", file=sys.stderr)
        return 1
    src = Path(sys.argv[1])
    start = float(sys.argv[2])
    end = float(sys.argv[3])
    dst = Path(sys.argv[4])
    duration = max(0.01, end - start)

    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-ss",
        str(start),
        "-i",
        str(src),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
