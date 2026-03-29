#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def find_font(preferred: str = "") -> str:
    if preferred and Path(preferred).exists():
        return str(Path(preferred).resolve())

    candidates = []
    win_dir = os.environ.get("WINDIR", r"C:\\Windows")
    fonts = Path(win_dir) / "Fonts"
    candidates.extend(
        [
            fonts / "msyh.ttc",
            fonts / "msyhbd.ttc",
            fonts / "simhei.ttf",
            fonts / "simsun.ttc",
            fonts / "simkai.ttf",
            fonts / "STZHONGS.TTF",
            fonts / "arialuni.ttf",
        ]
    )
    candidates.extend(
        [
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        ]
    )
    for c in candidates:
        if c.exists():
            return str(c.resolve())
    return ""
