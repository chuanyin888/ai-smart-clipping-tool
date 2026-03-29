#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PREFERRED_SUBS = [
    'en,en-US,en-orig',
    'zh-Hans,zh-CN,zh',
]


def run(cmd: list[str]) -> int:
    print('Running:', ' '.join(cmd))
    return subprocess.run(cmd).returncode


def ensure_yt_dlp_cmd() -> list[str] | None:
    candidates = [
        shutil.which('yt-dlp'),
        shutil.which('yt-dlp.exe'),
        str(Path.cwd() / 'bin' / 'yt-dlp.exe'),
        str(Path.cwd() / 'bin' / 'yt-dlp'),
        str(Path.home() / 'AppData/Local/Microsoft/WinGet/Links/yt-dlp.exe'),
    ]
    direct = next((c for c in candidates if c and (shutil.which(c) or Path(c).exists())), None)
    if direct:
        return [direct]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, '-m', 'yt_dlp']
    except Exception:
        pass
    print('yt-dlp not found; attempting automatic install via pip ...')
    code = subprocess.run([sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp', 'yt-dlp-ejs']).returncode
    if code != 0:
        return None
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, '-m', 'yt_dlp']
    except Exception:
        return None


def with_auth(cmd: list[str], cookies_file: str = '') -> list[str]:
    if cookies_file:
        return cmd + ['--cookies', cookies_file]
    return cmd


def with_ffmpeg(cmd: list[str], ffmpeg_location: str = '') -> list[str]:
    if ffmpeg_location:
        return cmd + ['--ffmpeg-location', ffmpeg_location]
    return cmd


def build_subtitle_cmd(yt_dlp_cmd: list[str], output_tpl: str, langs: str, url: str, cookies_file: str = '', ffmpeg_location: str = '') -> list[str]:
    cmd = yt_dlp_cmd + [
        '--no-playlist',
        '--skip-download',
        '--ignore-no-formats-error',
        '--write-auto-sub',
        '--write-sub',
        '--convert-subs',
        'srt',
        '-o',
        output_tpl,
        '--sub-langs',
        langs,
        url,
    ]
    cmd = with_auth(cmd, cookies_file)
    cmd = with_ffmpeg(cmd, ffmpeg_location)
    return cmd


def build_video_cmd(yt_dlp_cmd: list[str], output_tpl: str, url: str, cookies_file: str = '', ffmpeg_location: str = '') -> list[str]:
    cmd = yt_dlp_cmd + [
        '-f',
        'bv*+ba/b',
        '-o',
        output_tpl,
        url,
    ]
    cmd = with_auth(cmd, cookies_file)
    cmd = with_ffmpeg(cmd, ffmpeg_location)
    return cmd


def list_subs(yt_dlp_cmd: list[str], url: str, cookies_file: str = '') -> str:
    cmd = yt_dlp_cmd + ['--list-subs', url]
    cmd = with_auth(cmd, cookies_file)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    text = (proc.stdout or '') + '\n' + (proc.stderr or '')
    print(text)
    return text.lower()


def decide_lang_groups(listing: str, requested: str = 'auto') -> list[str]:
    if requested and requested != 'auto':
        return [requested]
    chosen: list[str] = []
    if any(k in listing for k in ['\nen ', 'english', 'en-orig', 'en-us']):
        chosen.append('en,en-US,en-orig')
    if any(k in listing for k in ['zh-hans', 'zh-cn', 'chinese (simplified)', ' chinese']):
        chosen.append('zh-Hans,zh-CN,zh')
    for item in PREFERRED_SUBS:
        if item not in chosen:
            chosen.append(item)
    return chosen


def try_download_subtitles(yt_dlp_cmd: list[str], url: str, output_tpl: str, cookies_file: str = '', ffmpeg_location: str = '', subtitle_lang: str = 'auto') -> int:
    listing = list_subs(yt_dlp_cmd, url, cookies_file)
    lang_sets = decide_lang_groups(listing, subtitle_lang)
    last_code = 1
    for langs in lang_sets:
        print(f'Trying subtitle download, languages={langs}')
        code = run(build_subtitle_cmd(yt_dlp_cmd, output_tpl, langs, url, cookies_file, ffmpeg_location))
        if code == 0:
            return 0
        last_code = code
    return last_code


def try_download_video(yt_dlp_cmd: list[str], url: str, output_tpl: str, cookies_file: str = '', ffmpeg_location: str = '') -> int:
    return run(build_video_cmd(yt_dlp_cmd, output_tpl, url, cookies_file, ffmpeg_location))


def main() -> int:
    parser = argparse.ArgumentParser(description='Download a YouTube video and subtitles.')
    parser.add_argument('url', help='YouTube URL')
    parser.add_argument('output_dir', help='Directory to save source assets')
    parser.add_argument('--cookies-file', default='', help='Optional Netscape cookies.txt path')
    parser.add_argument('--ffmpeg-location', default='', help='Optional ffmpeg folder or executable path')
    parser.add_argument('--subtitle-lang', default='auto', help='Subtitle language preference. auto / en / zh-Hans etc.')
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    yt_dlp_cmd = ensure_yt_dlp_cmd()
    if not yt_dlp_cmd:
        print('yt-dlp unavailable. Please install it or check pip/network access.', file=sys.stderr)
        return 1

    output_tpl = str(output_dir / '%(title)s [%(id)s].%(ext)s')
    sub_code = try_download_subtitles(yt_dlp_cmd, args.url, output_tpl, args.cookies_file, args.ffmpeg_location, args.subtitle_lang)
    if sub_code != 0:
        print('subtitle download failed; continuing with video-only flow', file=sys.stderr)

    video_code = try_download_video(yt_dlp_cmd, args.url, output_tpl, args.cookies_file, args.ffmpeg_location)
    if video_code != 0:
        print('video download failed', file=sys.stderr)
        return video_code
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
