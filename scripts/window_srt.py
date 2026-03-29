#!/usr/bin/env python3
import re
import sys
from pathlib import Path

try:
    from scripts.srt_to_json import parse_srt
except ModuleNotFoundError:
    from srt_to_json import parse_srt


def fmt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = round((seconds - int(seconds)) * 1000)
    total = int(seconds)
    s = total % 60
    total //= 60
    m = total % 60
    h = total // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    if len(sys.argv) != 5:
        print("Usage: window_srt.py input.srt start_sec end_sec output.srt", file=sys.stderr)
        return 1
    src = Path(sys.argv[1])
    start_sec = float(sys.argv[2])
    end_sec = float(sys.argv[3])
    dst = Path(sys.argv[4])

    cues = parse_srt(src.read_text(encoding="utf-8", errors="ignore"))
    selected = []
    for cue in cues:
        if cue["end_seconds"] <= start_sec or cue["start_seconds"] >= end_sec:
            continue
        selected.append(
            (
                max(0.0, cue["start_seconds"] - start_sec),
                max(0.0, min(end_sec, cue["end_seconds"]) - start_sec),
                cue["text"],
            )
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, (s, e, text) in enumerate(selected, start=1):
        lines.extend([str(i), f"{fmt_time(s)} --> {fmt_time(e)}", text, ""])
    dst.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
