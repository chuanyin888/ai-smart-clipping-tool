#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<sh>\d{2}):(?P<sm>\d{2}):(?P<ss>\d{2}),(?P<sms>\d{3})\s+-->\s+"
    r"(?P<eh>\d{2}):(?P<em>\d{2}):(?P<es>\d{2}),(?P<ems>\d{3})"
)


def to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(text: str):
    blocks = re.split(r"\n\s*\n", text.strip(), flags=re.M)
    cues = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        idx = lines[0]
        match = TIME_RE.match(lines[1])
        text_lines = lines[2:] if match else lines[1:]
        if not match:
            continue
        cues.append(
            {
                "index": int(idx) if idx.isdigit() else idx,
                "start": f"{match['sh']}:{match['sm']}:{match['ss']},{match['sms']}",
                "end": f"{match['eh']}:{match['em']}:{match['es']},{match['ems']}",
                "start_seconds": to_seconds(match["sh"], match["sm"], match["ss"], match["sms"]),
                "end_seconds": to_seconds(match["eh"], match["em"], match["es"], match["ems"]),
                "text": " ".join(text_lines).strip(),
            }
        )
    return cues


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: srt_to_json.py input.srt output.json", file=sys.stderr)
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    cues = parse_srt(src.read_text(encoding="utf-8", errors="ignore"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8")
    print(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
