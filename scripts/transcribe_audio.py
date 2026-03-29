#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from scripts._ffmpeg import ffmpeg_exe
except ModuleNotFoundError:
    from _ffmpeg import ffmpeg_exe




def ensure_package(import_name: str, pip_name: str) -> None:
    try:
        __import__(import_name)
        return
    except Exception:
        pass
    print(f"Installing missing dependency: {pip_name}", file=sys.stderr)
    cmd = [sys.executable, '-m', 'pip', 'install', '-U', pip_name]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        raise RuntimeError(f'Failed to install {pip_name}')


def ensure_transcription_backends() -> None:
    errors: list[str] = []
    for import_name, pip_name in [('faster_whisper', 'faster-whisper'), ('whisper', 'openai-whisper')]:
        try:
            __import__(import_name)
            return
        except Exception:
            try:
                ensure_package(import_name, pip_name)
                return
            except Exception as exc:
                errors.append(f'{pip_name}: {exc}')
    raise RuntimeError(' / '.join(errors) if errors else 'No transcription backend available')

def format_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ensure_wav(input_media: Path, wav_path: Path) -> None:
    cmd = [
        ffmpeg_exe(), '-y', '-i', str(input_media), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(wav_path)
    ]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        raise SystemExit(rc)


def transcribe_with_faster_whisper(wav_path: Path, model: str, language: str | None):
    from faster_whisper import WhisperModel

        # Force CPU on Windows portable builds. `device='auto'` may try CUDA and fail with
    # missing cublas DLLs on machines without a full CUDA runtime.
    model_obj = WhisperModel(model, device='cpu', compute_type='int8')
    segments, info = model_obj.transcribe(str(wav_path), vad_filter=True, beam_size=5, language=language)
    return list(segments), getattr(info, 'language', language)


def transcribe_with_whisper(wav_path: Path, model: str, language: str | None):
    import whisper

    model_obj = whisper.load_model(model if model in {'tiny', 'base', 'small', 'medium', 'large', 'turbo'} else 'small')
    result = model_obj.transcribe(str(wav_path), language=language, verbose=False)

    class Seg:
        def __init__(self, d):
            self.start = float(d['start'])
            self.end = float(d['end'])
            self.text = d['text']

    return [Seg(x) for x in result.get('segments', [])], result.get('language', language)


def main() -> int:
    parser = argparse.ArgumentParser(description='Auto transcribe a local video/audio into SRT.')
    parser.add_argument('input_media')
    parser.add_argument('output_srt')
    parser.add_argument('--model', default='base')
    parser.add_argument('--language', default='')
    args = parser.parse_args()

    try:
        ensure_transcription_backends()
    except Exception as exc:
        print(f'Unable to prepare transcription backend: {exc}', file=sys.stderr)
        return 2

    src = Path(args.input_media).resolve()
    dst = Path(args.output_srt).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    wav = dst.with_suffix('.16k.wav')
    ensure_wav(src, wav)

    segments = None
    detected_lang = args.language or None
    errors: list[str] = []
    try:
        segments, detected_lang = transcribe_with_faster_whisper(wav, args.model, args.language or None)
    except Exception as exc:
        errors.append(f'faster-whisper failed: {exc}')
        try:
            segments, detected_lang = transcribe_with_whisper(wav, args.model, args.language or None)
        except Exception as exc2:
            errors.append(f'whisper failed: {exc2}')
            print('\n'.join(errors), file=sys.stderr)
            return 2
    finally:
        try:
            wav.unlink()
        except OSError:
            pass

    lines: list[str] = []
    idx = 1
    for seg in segments or []:
        text = (getattr(seg, 'text', '') or '').strip()
        if not text:
            continue
        start = max(0.0, float(getattr(seg, 'start', 0.0)))
        end = max(start + 0.1, float(getattr(seg, 'end', start + 0.1)))
        lines.extend([str(idx), f"{format_ts(start)} --> {format_ts(end)}", text, ''])
        idx += 1

    dst.write_text('\n'.join(lines).strip() + '\n', encoding='utf-8')
    print(dst)
    if detected_lang:
        print(f'DETECTED_LANGUAGE={detected_lang}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
