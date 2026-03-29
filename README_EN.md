# AI Smart Clipping Tool

AI Smart Clipping Tool is a Windows-first local desktop workflow for turning a long YouTube video or a local video into short clips with optional Chinese hard subtitles.

It supports:
- YouTube URL mode and local file mode
- Subtitle download when available
- Automatic transcription fallback when subtitles are missing
- AI-assisted hotspot candidate analysis
- Manual review, preview, and selection of candidate clips
- Optional subtitle translation and hard-sub export
- A Windows launcher with `Start.vbs` as the main entry

## Main features

- **Two input modes**: YouTube URL or local video/subtitle files
- **Hotspot analysis**: generate candidate clips before exporting
- **Selectable export**: export only the checked clips
- **Preview workflow**: preview a candidate clip before final export
- **Optional hard subtitles**: export with or without hard subtitles
- **Local-first mode**: heuristic analysis and offline translation do not consume API credits
- **LLM mode**: optional cloud model analysis when you choose `llm`

## Project name

- Product name: **AI Smart Clipping Tool**
- Suggested GitHub repository name: **ai-smart-clipping-tool**

## Folder structure

```text
ai-smart-clipping-tool/
├─ Start.vbs                # Main launcher for end users
├─ Start.bat                # Helper launcher used by Start.vbs
├─ launcher.py              # Desktop UI entry
├─ app.py                   # CLI / workflow entry
├─ scripts/                 # Processing scripts
├─ references/              # Prompt and schema references
├─ docs/                    # Project documentation
├─ bin/                     # ffmpeg / ffprobe / ffplay
├─ work/                    # Runtime workspace, generated locally
├─ README.md
├─ README_CN.md
├─ requirements.txt
└─ LICENSE
```

## Quick start on Windows

1. Extract the project.
2. Put `ffmpeg.exe`, `ffprobe.exe`, and optionally `ffplay.exe` under `bin/`.
3. Add your own `cookies.txt` if you want to download YouTube videos that require authenticated access.
4. Install Python dependencies:

```bat
pip install -r requirements.txt
```

5. Double-click `Start.vbs`.

## Runtime requirements

For the source version in GitHub, users will typically need:
- Windows 10 or later
- Python 3.11 or 3.12 recommended
- ffmpeg binaries in `bin/`
- Deno for some YouTube extraction scenarios
- Network access for YouTube download
- A valid `cookies.txt` for some videos blocked by YouTube bot verification

## Modes and API usage

### Heuristic mode
When `AI Engine = heuristic`:
- hotspot analysis runs locally
- no cloud LLM API is used
- no API credits are consumed

### LLM mode
When `AI Engine = llm`:
- the app uses the configured API provider and model
- API usage depends on your own API key and provider billing

## Common workflow

1. Prepare source material
   - download from YouTube, or
   - load local video and subtitle files
2. Analyze hotspot candidates
3. Review and edit candidate clips
4. Preview selected candidates
5. Export selected clips
6. Optionally burn subtitles

## Main launcher rule

- **Use `Start.vbs` as the main user-facing launcher**
- `Start.bat` is only a helper launcher

## YouTube limitations

Some YouTube videos may fail with bot verification or require login cookies. When this happens, update `cookies.txt` or switch to local file mode.

See `docs/error-codes.md` for details.
