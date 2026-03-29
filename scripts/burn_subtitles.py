#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

try:
    from scripts._ffmpeg import ffmpeg_exe
except ModuleNotFoundError:
    from _ffmpeg import ffmpeg_exe

try:
    from scripts.windows_fonts import find_font
except ModuleNotFoundError:
    from windows_fonts import find_font


def escape_subtitles_path(path: Path) -> str:
    # ffmpeg subtitles filter on Windows is happiest with forward slashes and escaped drive colon.
    raw = path.resolve().as_posix()
    raw = raw.replace(':', '\\:').replace("'", r"\'")
    return raw


def escape_drawtext_text(text: str) -> str:
    # Escape characters significant to ffmpeg filtergraph / drawtext parsing.
    return (
        text.replace('\\', r'\\')
        .replace(':', r'\:')
        .replace("'", r"\'")
        .replace(',', r'\,')
        .replace('[', r'\[')
        .replace(']', r'\]')
        .replace('%', r'\%')
        .replace(';', r'\;')
    )


def escape_drawtext_font(path: Path) -> str:
    raw = path.resolve().as_posix()
    return raw.replace(':', '\\:').replace("'", r"\'")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('input_video')
    parser.add_argument('input_srt')
    parser.add_argument('output_video')
    parser.add_argument('--title', default='')
    parser.add_argument('--fontfile', default='')
    args = parser.parse_args()

    src = Path(args.input_video)
    srt = Path(args.input_srt)
    dst = Path(args.output_video)
    dst.parent.mkdir(parents=True, exist_ok=True)

    vf_parts = [f"subtitles=filename='{escape_subtitles_path(srt)}'"]
    if args.title:
        resolved_font = find_font(args.fontfile)
        fontfile = Path(resolved_font) if resolved_font else Path(args.fontfile) if args.fontfile else None
        safe_title = escape_drawtext_text(args.title)
        drawtext = (
            'drawtext='
            + (f"fontfile='{escape_drawtext_font(fontfile)}':" if fontfile else '')
            + f"text='{safe_title}':"
            + 'fontcolor=white:fontsize=48:borderw=3:bordercolor=black:'
            + 'x=(w-text_w)/2:y=(h-text_h)/2:enable=between(t\\,0\\,1)'
        )
        vf_parts.append(drawtext)

    cmd = [
        ffmpeg_exe(),
        '-y',
        '-i',
        str(src),
        '-vf',
        ','.join(vf_parts),
        '-c:v',
        'libx264',
        '-preset',
        'medium',
        '-crf',
        '18',
        '-c:a',
        'aac',
        '-movflags',
        '+faststart',
        str(dst),
    ]
    return subprocess.run(cmd).returncode


if __name__ == '__main__':
    raise SystemExit(main())
