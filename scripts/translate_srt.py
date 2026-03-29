#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests

try:
    from scripts.srt_to_json import parse_srt
except ModuleNotFoundError:
    from srt_to_json import parse_srt


TIME_LINE_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}$")


def rebuild_srt(cues: list[dict]) -> str:
    lines = []
    for i, cue in enumerate(cues, start=1):
        lines.extend([str(i), f"{cue['start']} --> {cue['end']}", cue['text'], ""])
    return "\n".join(lines).strip() + "\n"


def translate_openai_compatible(texts: list[str], api_base: str, api_key: str, model: str) -> list[str]:
    if not api_key:
        raise RuntimeError("OpenAI-compatible translation requires --api-key or OPENAI_API_KEY")
    prompt = {
        "role": "user",
        "content": (
            "Translate the following English subtitle lines into natural spoken Simplified Chinese. "
            "Preserve names, products, numbers, and meaning. Return JSON only as {\"translations\":[...]}.\n\n"
            + json.dumps(texts, ensure_ascii=False)
        ),
    }
    resp = requests.post(
        api_base.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a subtitle translator. Return strict JSON only."},
                prompt,
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    translations = parsed.get("translations") if isinstance(parsed, dict) else None
    if not isinstance(translations, list) or len(translations) != len(texts):
        raise RuntimeError("Translator returned malformed JSON or wrong item count")
    return [str(x).strip() for x in translations]


def translate_offline_argos(texts: list[str]) -> list[str]:
    try:
        from argostranslate import package, translate
    except Exception as exc:
        raise RuntimeError(
            "Offline translation requires argostranslate. Install it with: pip install argostranslate"
        ) from exc

    installed = translate.get_installed_languages()
    en = next((x for x in installed if x.code == "en"), None)
    zh = next((x for x in installed if x.code in {"zh", "zh_CN"}), None)
    if en is None or zh is None:
        available = package.get_available_packages()
        pkg = next((p for p in available if p.from_code == "en" and p.to_code == "zh"), None)
        if pkg is None:
            raise RuntimeError("No en->zh Argos package available")
        package.install_from_path(pkg.download())
        installed = translate.get_installed_languages()
        en = next((x for x in installed if x.code == "en"), None)
        zh = next((x for x in installed if x.code in {"zh", "zh_CN"}), None)
    if en is None or zh is None:
        raise RuntimeError("Argos en->zh translator is unavailable after install")
    translator = en.get_translation(zh)
    return [translator.translate(text).strip() for text in texts]


def translate_texts(texts: list[str], provider: str, api_base: str, api_key: str, model: str) -> list[str]:
    if provider == "none":
        return texts
    if provider == "openai_compatible":
        return translate_openai_compatible(texts, api_base, api_key, model)
    if provider == "offline":
        return translate_offline_argos(texts)
    raise RuntimeError(f"Unknown provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate an SRT file to Simplified Chinese while preserving timestamps.")
    parser.add_argument("input_srt")
    parser.add_argument("output_srt")
    parser.add_argument("--provider", choices=["openai_compatible", "offline", "none"], default="offline")
    parser.add_argument("--api-base", default="https://api.openai.com/v1")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    src = Path(args.input_srt)
    dst = Path(args.output_srt)
    cues = parse_srt(src.read_text(encoding="utf-8", errors="ignore"))
    texts = [cue["text"] for cue in cues]

    translated: list[str] = []
    for i in range(0, len(texts), args.batch_size):
        batch = texts[i : i + args.batch_size]
        translated.extend(translate_texts(batch, args.provider, args.api_base, args.api_key, args.model))

    for cue, zh in zip(cues, translated):
        cue["text"] = zh

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(rebuild_srt(cues), encoding="utf-8")
    print(dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
