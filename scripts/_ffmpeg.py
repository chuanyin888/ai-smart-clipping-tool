#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path


def ffmpeg_exe() -> str:
    root = Path(__file__).resolve().parents[1]
    local_candidates = [
        root / 'bin' / 'ffmpeg.exe',
        root / 'bin' / 'ffmpeg',
        Path.cwd() / 'bin' / 'ffmpeg.exe',
        Path.cwd() / 'bin' / 'ffmpeg',
    ]
    for path in local_candidates:
        if path.exists():
            return str(path)

    direct = shutil.which('ffmpeg')
    if direct:
        return direct

    try:
        out = subprocess.check_output(
            [sys.executable, '-c', 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'],
            text=True,
        ).strip()
    except Exception as exc:
        raise RuntimeError('ffmpeg not available; place ffmpeg.exe under ./bin or install imageio-ffmpeg/system ffmpeg') from exc

    if not out or not Path(out).exists():
        raise RuntimeError('ffmpeg executable path not found')
    return out
