#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.srt_to_json import parse_srt
from scripts.select_clips import generate_candidates, write_candidate_review, write_packaging

VIDEO_EXTS = {'.mp4', '.webm', '.mkv', '.mov', '.m4v'}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or 'video'


def run(cmd: list[str], check: bool = True) -> int:
    print('\n>>>', ' '.join(map(str, cmd)))
    proc = subprocess.run(cmd)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc.returncode


def find_source_files(source_dir: Path) -> dict[str, Path | None]:
    files = list(source_dir.iterdir()) if source_dir.exists() else []
    videos = [p for p in files if p.suffix.lower() in VIDEO_EXTS]
    srts = [p for p in files if p.suffix.lower() == '.srt']
    thumbs = [p for p in files if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]

    def rank_srt(path: Path) -> tuple[int, int]:
        name = path.name.lower()
        if any(k in name for k in ['.en.', '.en-', '.en_', 'en-orig']):
            return (0, len(name))
        if any(k in name for k in ['zh-hans', 'zh-cn', '.zh.', '.zh-', '.zh_']):
            return (1, len(name))
        return (2, len(name))

    def rank_video(path: Path) -> tuple[int, int]:
        ext_order = {'.mp4': 0, '.webm': 1, '.mkv': 2, '.mov': 3, '.m4v': 4}
        return (ext_order.get(path.suffix.lower(), 9), len(path.name))

    video = sorted(videos, key=rank_video)[0] if videos else None
    srt = sorted(srts, key=rank_srt)[0] if srts else None
    thumb = thumbs[0] if thumbs else None
    return {'video': video, 'srt': srt, 'thumbnail': thumb}


def choose_clip_ids(candidates: list[dict[str, Any]], requested: str | None, max_exports: int) -> list[str]:
    if requested:
        requested = requested.strip()
        if requested.lower() == 'all':
            return [c['id'] for c in candidates]
        chosen = [x.strip() for x in requested.split(',') if x.strip()]
        normalized = set()
        for x in chosen:
            normalized.add(x)
            if x.isdigit():
                normalized.add(f'clip-{int(x):02d}')
            elif x.lower().startswith('clip-'):
                normalized.add(x.lower())
        picked = []
        for c in candidates:
            cid = c['id']
            if cid in normalized or cid.lower() in normalized or cid.replace('clip-', '') in normalized:
                picked.append(cid)
        return picked
    return [c['id'] for c in candidates[: min(max_exports, len(candidates))]]


def read_title(video_path: Path) -> str:
    stem = video_path.stem
    stem = re.sub(r'\s*\[[^\]]+\]$', '', stem).strip()
    return stem or video_path.stem


def is_chinese_subtitle(path: Path) -> bool:
    name = path.name.lower()
    return any(x in name for x in ['zh-hans', 'zh-cn', '.zh.', '.zh-', '.zh_', 'chinese'])


def copy_into_source(src: str, dst_dir: Path) -> Path:
    src_path = Path(src).expanduser().resolve()
    dst = dst_dir / src_path.name
    if src_path != dst:
        shutil.copy2(src_path, dst)
    return dst


def prepare_sources(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    work_root = Path(args.work_dir).expanduser().resolve()
    seed = args.slug or (args.url.split('v=')[-1].split('&')[0] if args.url else Path(args.input_video).stem)
    slug = slugify(seed)
    base = work_root / slug
    source_dir = base / 'source'
    analysis_dir = base / 'analysis'
    clips_dir = base / 'clips'
    preview_dir = base / 'preview'
    source_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    if args.input_video and args.input_srt:
        copy_into_source(args.input_video, source_dir)
        copy_into_source(args.input_srt, source_dir)
    else:
        existing = find_source_files(source_dir)
        if existing['video'] and existing['srt']:
            print('Found existing source assets. Skipping YouTube download.')
        else:
            cmd = [
                sys.executable,
                str(Path('scripts') / 'download_youtube.py'),
                args.url,
                str(source_dir),
            ]
            if args.cookies_file:
                cmd += ['--cookies-file', args.cookies_file]
            if args.ffmpeg_location:
                cmd += ['--ffmpeg-location', args.ffmpeg_location]
            if args.subtitle_lang:
                cmd += ['--subtitle-lang', args.subtitle_lang]
            run(cmd)
    return work_root, base, source_dir, analysis_dir, clips_dir, preview_dir, base


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    _, base, source_dir, analysis_dir, clips_dir, preview_dir, _ = prepare_sources(args)
    sources = find_source_files(source_dir)
    if not sources['video']:
        print('Missing source video after prepare/download.', file=sys.stderr)
        print(json.dumps({k: str(v) if v else None for k, v in sources.items()}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    if not sources['srt']:
        auto_srt = Path(sources['video']).with_suffix('.auto.srt')
        print(f'No subtitle found. Running auto transcription -> {auto_srt}')
        tcmd = [sys.executable, str(Path('scripts') / 'transcribe_audio.py'), str(sources['video']), str(auto_srt)]
        run(tcmd)
        sources = find_source_files(source_dir)
    if not sources['srt']:
        print('Missing source subtitle even after auto transcription.', file=sys.stderr)
        print(json.dumps({k: str(v) if v else None for k, v in sources.items()}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    transcript_json = analysis_dir / 'transcript.json'
    run([sys.executable, str(Path('scripts') / 'srt_to_json.py'), str(sources['srt']), str(transcript_json)])
    cues = parse_srt(Path(sources['srt']).read_text(encoding='utf-8', errors='ignore'))
    video_title = read_title(Path(sources['video']))
    candidates = generate_candidates(
        cues=cues,
        video_title=video_title,
        out_count=max(1, min(args.num_candidates, 10)),
        mode=args.selection_mode,
        api_base=args.candidate_api_base or args.api_base,
        api_key=args.candidate_api_key or args.api_key,
        model=args.candidate_model or args.model,
        min_sec=args.min_duration,
        max_sec=args.max_duration,
    )
    selected_path = analysis_dir / 'selected_clips.json'
    selected_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding='utf-8')
    review_path = analysis_dir / 'candidate-review.txt'
    write_candidate_review(candidates, review_path)
    print(f'ANALYSIS_JSON={selected_path}')
    print(f'SOURCE_VIDEO={sources["video"]}')
    print(f'SOURCE_SRT={sources["srt"]}')
    print(f'CLIPS_DIR={clips_dir}')
    return {
        'base': base,
        'source_dir': source_dir,
        'analysis_dir': analysis_dir,
        'clips_dir': clips_dir,
        'preview_dir': preview_dir,
        'video': Path(sources['video']),
        'srt': Path(sources['srt']),
        'transcript_json': transcript_json,
        'selected_path': selected_path,
        'candidates': candidates,
    }


def export_clips(args: argparse.Namespace, analyzed: dict[str, Any] | None = None) -> int:
    if analyzed is None:
        if not args.analysis_file:
            raise SystemExit('export mode requires --analysis-file')
        base = Path(args.analysis_file).resolve().parents[1]
        source_dir = base / 'source'
        clips_dir = base / 'clips'
        selected_path = Path(args.analysis_file)
        candidates = json.loads(selected_path.read_text(encoding='utf-8'))
        sources = find_source_files(source_dir)
        if not sources['video'] or not sources['srt']:
            raise SystemExit('source assets missing')
        analyzed = {
            'base': base,
            'source_dir': source_dir,
            'analysis_dir': base / 'analysis',
            'clips_dir': clips_dir,
            'video': Path(sources['video']),
            'srt': Path(sources['srt']),
            'selected_path': selected_path,
            'candidates': candidates,
        }

    candidates: list[dict[str, Any]] = analyzed['candidates']
    chosen_ids = choose_clip_ids(candidates, args.export_ids, args.max_exports)
    chosen = [c for c in candidates if c['id'] in chosen_ids]
    if not chosen:
        print('No clips selected for export.', file=sys.stderr)
        return 1

    source_video: Path = analyzed['video']
    source_srt: Path = analyzed['srt']
    clips_dir: Path = analyzed['clips_dir']
    failures: list[str] = []
    packaging = []
    source_is_chinese = is_chinese_subtitle(source_srt)

    for idx, clip in enumerate(chosen, start=1):
        clip_slug = slugify(clip['title'])[:40] or f'clip-{idx:02d}'
        clip_dir = clips_dir / f'{idx:02d}-{clip_slug}'
        clip_dir.mkdir(parents=True, exist_ok=True)
        clip_mp4 = clip_dir / 'clip.mp4'
        local_srt = clip_dir / ('clip.src.srt' if not source_is_chinese else 'clip.zh.srt')
        zh_srt = clip_dir / 'clip.zh.srt'
        out_mp4 = clip_dir / 'clip.hardsub.mp4'
        metadata_txt = clip_dir / 'metadata.txt'
        try:
            run([sys.executable, str(Path('scripts') / 'clip_video.py'), str(source_video), str(clip['start_seconds']), str(clip['end_seconds']), str(clip_mp4)])
            run([sys.executable, str(Path('scripts') / 'window_srt.py'), str(source_srt), str(clip['start_seconds']), str(clip['end_seconds']), str(local_srt if not source_is_chinese else zh_srt)])
            if not source_is_chinese and args.translator != 'none':
                run([
                    sys.executable,
                    str(Path('scripts') / 'translate_srt.py'),
                    str(local_srt),
                    str(zh_srt),
                    '--provider',
                    args.translator,
                    '--api-base',
                    args.api_base,
                    '--api-key',
                    args.api_key,
                    '--model',
                    args.model,
                ])
            elif not source_is_chinese and args.translator == 'none':
                shutil.copy2(local_srt, zh_srt)

            short_title = clip['title']
            short_desc = ' '.join(clip['summary'])[:140]
            metadata = (
                f"id: {clip['id']}\n"
                f"title: {short_title}\n"
                f"description: {short_desc}\n"
                f"start: {clip['start']}\n"
                f"end: {clip['end']}\n"
                f"duration_seconds: {clip['duration_seconds']}\n"
            )
            metadata_txt.write_text(metadata, encoding='utf-8')
            packaging.append({'id': clip['id'], 'title': short_title, 'description': short_desc})

            if args.burn_subtitles:
                burn_cmd = [sys.executable, str(Path('scripts') / 'burn_subtitles.py'), str(clip_mp4), str(zh_srt), str(out_mp4)]
                if args.fontfile:
                    burn_cmd.extend(['--fontfile', args.fontfile])
                # safer: don't overlay title on video in v7
                run(burn_cmd)
        except SystemExit as exc:
            msg = f"{clip['id']} failed with code {exc.code}"
            print(msg)
            failures.append(msg)
            if not args.continue_on_error:
                raise
        except Exception as exc:
            msg = f"{clip['id']} failed: {exc}"
            print(msg)
            failures.append(msg)
            if not args.continue_on_error:
                raise

    write_packaging(packaging, analyzed['analysis_dir'] / 'clip-packaging.txt')
    if failures:
        (clips_dir / 'failures.txt').write_text('\n'.join(failures) + '\n', encoding='utf-8')
        print(f'FAILURES={clips_dir / "failures.txt"}')
        return 1
    print(f'CLIPS_DIR={clips_dir}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Windows-friendly CLI for YouTube interview shorts with Chinese hard subtitles.')
    parser.add_argument('--mode', choices=['full', 'analyze', 'export'], default='full')
    parser.add_argument('--url', default='', help='YouTube URL')
    parser.add_argument('--input-video', default='', help='Existing local video path')
    parser.add_argument('--input-srt', default='', help='Existing local subtitle path')
    parser.add_argument('--analysis-file', default='', help='Existing selected_clips.json for export mode')
    parser.add_argument('--cookies-file', default='', help='Optional Netscape cookies.txt path')
    parser.add_argument('--ffmpeg-location', default=str(Path('bin').resolve()) if Path('bin').exists() else '', help='Optional ffmpeg folder or executable path')
    parser.add_argument('--subtitle-lang', default='auto', help='Subtitle preference: auto / en / zh-Hans')
    parser.add_argument('--work-dir', default='work', help='Base work directory')
    parser.add_argument('--slug', default='', help='Optional custom work folder slug')
    parser.add_argument('--translator', choices=['openai_compatible', 'offline', 'none'], default='offline')
    parser.add_argument('--api-base', default=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'))
    parser.add_argument('--api-key', default=os.getenv('OPENAI_API_KEY', ''))
    parser.add_argument('--model', default=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    parser.add_argument('--selection-mode', choices=['heuristic', 'llm'], default='heuristic')
    parser.add_argument('--candidate-model', default=os.getenv('CANDIDATE_MODEL', 'gpt-4.1-mini'))
    parser.add_argument('--candidate-api-base', default=os.getenv('CANDIDATE_API_BASE', ''))
    parser.add_argument('--candidate-api-key', default=os.getenv('CANDIDATE_API_KEY', ''))
    parser.add_argument('--num-candidates', type=int, default=3)
    parser.add_argument('--min-duration', type=float, default=20)
    parser.add_argument('--max-duration', type=float, default=35)
    parser.add_argument('--export-ids', default='', help='Comma-separated clip ids to export.')
    parser.add_argument('--max-exports', type=int, default=3)
    parser.add_argument('--continue-on-error', action='store_true', default=True)
    parser.add_argument('--fontfile', default='', help='Optional font file for Chinese title burn-in')
    parser.add_argument('--burn-subtitles', action='store_true', default=False)
    args = parser.parse_args()

    if args.mode in {'full', 'analyze'} and not args.url and not (args.input_video and args.input_srt):
        print('Provide either --url or both --input-video and --input-srt', file=sys.stderr)
        return 2

    if args.mode == 'analyze':
        analyze(args)
        return 0
    if args.mode == 'export':
        return export_clips(args)

    analyzed = analyze(args)
    return export_clips(args, analyzed)


if __name__ == '__main__':
    raise SystemExit(main())
