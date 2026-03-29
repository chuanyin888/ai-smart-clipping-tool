#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import requests


def seconds_to_srt(seconds: float) -> str:
    ms = round((seconds - int(seconds)) * 1000)
    total = int(seconds)
    s = total % 60
    total //= 60
    m = total % 60
    h = total // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def clean_title(text: str, limit: int = 28) -> str:
    text = re.sub(r"\s+", " ", text).strip(" -–—,.;:!?\"'")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def heuristic_score(text: str) -> float:
    score = 0.0
    words = re.findall(r"[A-Za-z']+", text)
    n = len(words)
    if 35 <= n <= 150:
        score += 3
    score += min(3, n / 40)
    if re.search(r"\b(I think|the truth is|the problem is|what changed|the reason|we learned|surprising|actually)\b", text, re.I):
        score += 2.5
    if "?" in text:
        score += 1
    if re.search(r"\bnever|always|nobody|everybody|biggest|worst|best|impossible|future\b", text, re.I):
        score += 1.5
    if re.search(r"\b(um|uh|thanks for having me|welcome back|subscribe|sponsor)\b", text, re.I):
        score -= 2
    return score


def summarize_two_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    clauses = re.split(r"(?<=[.!?])\s+", cleaned)
    clauses = [c.strip() for c in clauses if c.strip()]
    if len(clauses) >= 2:
        s1 = clauses[0]
        s2 = clauses[1]
    else:
        words = cleaned.split()
        mid = max(8, min(len(words) - 1, len(words) // 2)) if len(words) > 16 else len(words)
        s1 = " ".join(words[:mid]).strip()
        s2 = " ".join(words[mid:]).strip() or s1
    def normalize_sentence(s: str) -> str:
        s = s.strip().rstrip("。.!? ")
        return s + "。"
    return [normalize_sentence(s1), normalize_sentence(s2)]


def build_windows(cues: list[dict[str, Any]], min_sec: float = 20, max_sec: float = 35) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    n = len(cues)
    for i in range(n):
        start = cues[i]["start_seconds"]
        text_parts = []
        for j in range(i, min(n, i + 32)):
            end = cues[j]["end_seconds"]
            duration = end - start
            if duration < min_sec:
                text_parts.append(cues[j]["text"])
                continue
            if duration > max_sec:
                break
            text_parts.append(cues[j]["text"])
            text = " ".join(text_parts).strip()
            windows.append(
                {
                    "start_seconds": start,
                    "end_seconds": end,
                    "duration_seconds": round(duration, 3),
                    "text": text,
                    "score": heuristic_score(text),
                }
            )
    windows.sort(key=lambda x: x["score"], reverse=True)
    return windows


def dedupe_windows(windows: list[dict[str, Any]], out_count: int) -> list[dict[str, Any]]:
    picked: list[dict[str, Any]] = []
    for w in windows:
        overlap = False
        for p in picked:
            inter = max(0.0, min(w["end_seconds"], p["end_seconds"]) - max(w["start_seconds"], p["start_seconds"]))
            denom = min(w["duration_seconds"], p["duration_seconds"])
            if denom > 0 and inter / denom > 0.55:
                overlap = True
                break
        if not overlap:
            picked.append(w)
        if len(picked) >= out_count:
            break
    return sorted(picked, key=lambda x: x["start_seconds"])


def heuristic_candidates(cues: list[dict[str, Any]], out_count: int, min_sec: float = 20, max_sec: float = 35) -> list[dict[str, Any]]:
    windows = dedupe_windows(build_windows(cues, min_sec=min_sec, max_sec=max_sec), out_count)
    results = []
    for idx, w in enumerate(windows, start=1):
        snippet = w["text"]
        title = clean_title(snippet.split(".")[0] or snippet.split("?")[0] or snippet)
        summary = summarize_two_sentences(snippet)
        results.append(
            {
                "id": f"clip-{idx:02d}",
                "start": seconds_to_srt(w["start_seconds"]),
                "end": seconds_to_srt(w["end_seconds"]),
                "start_seconds": w["start_seconds"],
                "end_seconds": w["end_seconds"],
                "duration_seconds": w["duration_seconds"],
                "title": title,
                "summary": summary[:2],
                "reason": "Heuristic standout moment with a self-contained claim or explanation.",
            }
        )
    return results


def llm_candidates(cues: list[dict[str, Any]], video_title: str, out_count: int, api_base: str, api_key: str, model: str, min_sec: float = 20, max_sec: float = 35) -> list[dict[str, Any]]:
    if not api_key:
        raise RuntimeError("selection-mode=llm requires an API key")
    transcript = "\n".join(
        f"[{c['start']} - {c['end']}] {c['text']}" for c in cues[:2500]
    )
    prompt = f"""
You are selecting strong short-video candidates from a YouTube interview transcript.
Return JSON only, as an array following this schema:
- id
- start
- end
- start_seconds
- end_seconds
- duration_seconds
- title
- summary (exactly 2 Chinese sentences)
- reason
Rules:
- Generate {out_count} candidates.
- Prefer clips between {min_sec} and {max_sec} seconds.
- Each clip must be self-contained.
- Title should be short and provocative in Chinese.
- summary must contain exactly 2 Chinese sentences.
- Use exact timestamps from the transcript.
- Reject greetings, sponsor reads, filler, and fragments ending mid-thought.
Video title: {video_title}
Transcript:
{transcript}
""".strip().format(out_count=out_count, video_title=video_title, transcript=transcript, min_sec=min_sec, max_sec=max_sec)
    url = api_base.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        for key in ("clips", "items", "data", "candidates"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
    if isinstance(parsed, list):
        return parsed
    raise RuntimeError("LLM did not return a usable clip list")


def generate_candidates(cues: list[dict[str, Any]], video_title: str, out_count: int, mode: str, api_base: str, api_key: str, model: str, min_sec: float = 20, max_sec: float = 35) -> list[dict[str, Any]]:
    if mode == "llm":
        return llm_candidates(cues, video_title, out_count, api_base, api_key, model, min_sec=min_sec, max_sec=max_sec)
    return heuristic_candidates(cues, out_count, min_sec=min_sec, max_sec=max_sec)


def write_candidate_review(candidates: list[dict[str, Any]], path: Path) -> None:
    lines = []
    for c in candidates:
        lines.extend(
            [
                f"{c['id']}",
                f"时间: {c['start']} -> {c['end']}",
                f"时长: {c['duration_seconds']} 秒",
                f"标题: {c['title']}",
                f"简介1: {c['summary'][0]}",
                f"简介2: {c['summary'][1]}",
                "",
            ]
        )
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_packaging(items: list[dict[str, str]], path: Path) -> None:
    lines = []
    for item in items:
        lines.extend([f"{item['id']}", f"标题: {item['title']}", f"描述: {item['description']}", ""])
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
