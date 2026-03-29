# Windows 10 命令行版使用说明

## 1. 环境准备

建议安装：

- Python 3.11+
- ffmpeg（可选；如果没有，脚本会尝试使用 imageio-ffmpeg）
- yt-dlp（推荐安装到 PATH；也可以把 `yt-dlp.exe` 放到项目根目录下的 `bin/`）

安装依赖：

```bash
pip install -r requirements.txt
```

## 2. 最简单的运行方式

```bash
python app.py --url "https://www.youtube.com/watch?v=oo5v64aL2zQ"
```

默认行为：

- 下载视频和字幕到 `work/<slug>/source/`
- 解析字幕到 `work/<slug>/analysis/transcript.json`
- 用启发式规则生成候选片段到 `selected_clips.json`
- 自动导出前 6 个片段
- 如果源字幕不是中文，则使用 `offline` 模式翻译为简体中文
- 为每个片段生成 `clip.hardsub.mp4`

## 3. 使用 OpenAI 兼容接口翻译

```bash
python app.py ^
  --url "https://www.youtube.com/watch?v=oo5v64aL2zQ" ^
  --translator openai_compatible ^
  --api-base "https://api.openai.com/v1" ^
  --api-key "你的API_KEY" ^
  --model "gpt-4.1-mini"
```

## 4. 使用 OpenAI 兼容接口做候选分析

```bash
python app.py ^
  --url "https://www.youtube.com/watch?v=oo5v64aL2zQ" ^
  --selection-mode llm ^
  --candidate-api-base "https://api.openai.com/v1" ^
  --candidate-api-key "你的API_KEY" ^
  --candidate-model "gpt-4.1-mini" ^
  --translator openai_compatible ^
  --api-base "https://api.openai.com/v1" ^
  --api-key "你的API_KEY"
```

## 5. 指定只导出某几个 clip id

先跑一次查看候选列表，然后：

```bash
python app.py --url "https://www.youtube.com/watch?v=oo5v64aL2zQ" --export-ids "clip-01,clip-03,clip-07"
```

## 6. 目录结构

```text
work/<slug>/
  source/
  analysis/
  clips/
```

## 7. 常见问题

### yt-dlp not found

做法之一：

- 直接安装 yt-dlp 到系统 PATH
- 或把 `yt-dlp.exe` 放到项目根目录下的 `bin/`

### 字幕翻译失败

- `offline` 模式需要 `argostranslate`
- `openai_compatible` 模式需要正确的 `--api-key`

### 中文标题显示乱码

可显式指定字体：

```bash
python app.py --url "..." --fontfile "C:\\Windows\\Fonts\\msyh.ttc"
```
