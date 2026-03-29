# Error Code Reference

## ERR_YT_BOT_VERIFY_BLOCK
- 中文名称：YouTube 风控验证拦截
- 触发特征：`Sign in to confirm you’re not a bot`
- 影响：视频和字幕下载失败，流程中断
- 处理建议：更新 `cookies.txt`，或改用本地视频模式

## ERR_YT_VIDEO_DOWNLOAD_FAILED
- 中文名称：视频下载失败
- 触发特征：源视频未生成
- 处理建议：检查链接、网络、cookies、YouTube 可访问性

## ERR_YT_SUBTITLE_NOT_FOUND
- 中文名称：未找到可用字幕
- 触发特征：无字幕、无自动字幕
- 处理建议：进入自动转录流程，或手动提供字幕

## ERR_ENV_COOKIES_INVALID
- 中文名称：cookies 已失效
- 触发特征：YouTube 访问需要验证，旧 cookies 不可用
- 处理建议：重新导出最新的 `cookies.txt`

## ERR_ENV_FFMPEG_MISSING
- 中文名称：未找到 ffmpeg
- 触发特征：字幕转换、裁剪、硬字幕失败并提示 ffmpeg 缺失
- 处理建议：将 ffmpeg 二进制放到 `bin/`

## ERR_ENV_DENO_MISSING
- 中文名称：未找到 Deno
- 触发特征：YouTube 提取阶段无法完成 JS challenge
- 处理建议：安装 Deno

## ERR_TR_DEPENDENCY_MISSING
- 中文名称：自动转录依赖缺失
- 触发特征：`No module named 'faster_whisper'` 或 `No module named 'whisper'`
- 处理建议：安装转录依赖或切换到有字幕视频

## ERR_TR_TRANSCRIBE_FAILED
- 中文名称：自动转录失败
- 触发特征：音频已提取，但 `.auto.srt` 未生成
- 处理建议：查看日志，检查模型下载、CPU 模式和音频提取

## ERR_AI_ANALYSIS_FAILED
- 中文名称：AI 热点分析失败
- 触发特征：未生成候选片段
- 处理建议：检查 `transcript.json`、候选分析配置、API 设置

## ERR_EXP_CLIP_FAILED
- 中文名称：片段裁剪失败
- 触发特征：单个 clip 未导出
- 处理建议：检查时间范围和 ffmpeg

## ERR_EXP_HARDSUB_FAILED
- 中文名称：硬字幕烧录失败
- 触发特征：烧录阶段失败
- 处理建议：检查字幕文件、标题特殊字符、ffmpeg filter 转义
