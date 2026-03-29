---
name: youtube-interview-shorts-zh
description: Use when the user wants to turn a long YouTube interview, talk, or podcast into 5 to 8 short clips with Chinese hard subtitles. This skill downloads the source video and subtitles, analyzes the transcript, selects strong standalone moments, cuts clips under 3 minutes, prepares Chinese packaging copy, and burns subtitles plus a first-second title into the exported videos.
---

# Youtube Interview Shorts Zh

## Overview

Use this skill to convert one long YouTube interview into multiple short Chinese-subbed clips that are ready to review or post. It bundles the download, transcript parsing, clip cutting, subtitle windowing, and subtitle/title burn-in helpers.

## When To Use

- The user gives a YouTube interview, talk, keynote, or podcast URL and wants multiple short clips.
- The user wants Chinese hard subtitles burned into each final clip.
- The user wants review-friendly candidate clip suggestions before export, or explicitly wants you to pick the best set yourself.

## Workflow

1. Confirm prerequisites.
Check `yt-dlp` and `ffmpeg` availability first. The helper scripts can use system `ffmpeg` or the `imageio-ffmpeg` binary fallback.

2. Create a work layout.
Use a layout like:

```text
work/<video-slug>/
  source/
  analysis/
  clips/
```

3. Download source assets.
Run [download_youtube.py](./scripts/download_youtube.py) with the YouTube URL and the `source/` directory. This downloader prefers browser cookies, falls back from English subtitles to `zh-Hans`, and uses the more reliable Android client path for the MP4 download.

4. Inspect the downloaded files.
Identify:
- the source `.mp4`
- the subtitle `.srt`
- any sidecar files such as `.ytdl`

5. Parse the subtitle file into JSON.
Use [srt_to_json.py](./scripts/srt_to_json.py) and save the artifact into `analysis/transcript.json`.

6. Analyze before cutting.
Read [clip-schema.md](./references/clip-schema.md) and [analysis-prompt.md](./references/analysis-prompt.md). Generate a generous candidate list, then write `analysis/selected_clips.json` and `analysis/candidate-review.txt`.

7. Candidate rules.
- Target 5 to 8 exported clips unless the user asks for another count.
- Prefer clips between 20 and 180 seconds.
- Favor one clear idea per clip.
- Favor strong opening lines, complete endings, and minimal dependency on missing context.
- Reject filler, greetings, sponsor reads, and fragments that end mid-thought.

8. Export each chosen clip.
- Cut the video with [clip_video.py](./scripts/clip_video.py)
- Window the subtitle file with [window_srt.py](./scripts/window_srt.py)
- If the source subtitle is English, translate the local clip SRT into simplified Chinese while preserving timestamps as closely as possible
- If the source subtitle is already Chinese, keep it and lightly clean only obvious duplication or noise
- Burn subtitles and a first-second title with [burn_subtitles.py](./scripts/burn_subtitles.py)

9. Packaging copy.
For each exported clip, create:
- one short, sharp Chinese title
- one Chinese description under 140 characters

Write per-clip metadata into each clip folder and also compile a combined `analysis/clip-packaging.txt`.

## File Layout

Use:

```text
work/<video-slug>/
  source/
    original.mp4
    original.<lang>.srt
  analysis/
    transcript.json
    selected_clips.json
    candidate-review.txt
    clip-packaging.txt
  clips/
    01-<slug>/
      clip.mp4
      clip.zh.srt
      clip.hardsub.mp4
      metadata.txt
```

## Script Notes

- Run the helper scripts from the skill root with `PYTHONPATH="$PWD"` when using `python3 -m scripts.<name>`.
- Prefer `PingFang` or another local Chinese font when burning titles and subtitles. If no better font is available, let the script fall back to the system default.
- The downloader uses Chrome cookies when available. If download fails because cookies are stale, refresh browser login state before changing the workflow.

## Resources

- Scripts:
  [download_youtube.py](./scripts/download_youtube.py),
  [srt_to_json.py](./scripts/srt_to_json.py),
  [window_srt.py](./scripts/window_srt.py),
  [clip_video.py](./scripts/clip_video.py),
  [burn_subtitles.py](./scripts/burn_subtitles.py)
- References:
  [clip-schema.md](./references/clip-schema.md),
  [analysis-prompt.md](./references/analysis-prompt.md)

## Output Contract

Return:
- the source asset folder
- the candidate clip list with timestamps, duration, title, and two-sentence summaries
- the packaging text file path
- the final `clip.hardsub.mp4` path for each exported short

If the workflow cannot finish, report the exact blocker, such as stale cookies, failed download, missing subtitles, missing `ffmpeg`, or unusable transcript quality.
