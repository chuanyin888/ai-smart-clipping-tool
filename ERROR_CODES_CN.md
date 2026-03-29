# 错误码对照表

## ERR_YT_BOT_VERIFY_BLOCK
- 中文名称：YouTube 风控验证拦截
- 典型特征：`Sign in to confirm you're not a bot`
- 影响：无法获取视频格式、无法下载视频或字幕
- 处理建议：更新 `cookies.txt`，或改用本地视频模式

## ERR_YT_VIDEO_DOWNLOAD_FAILED
- 中文名称：视频下载失败
- 典型特征：视频文件未生成，日志含 `video download failed`
- 处理建议：检查链接、网络、cookies 和 ffmpeg 路径

## ERR_YT_SUBTITLE_NOT_FOUND
- 中文名称：未找到可用字幕
- 典型特征：`There are no subtitles for the requested languages`
- 处理建议：自动转录，或手动提供字幕文件

## ERR_ENV_COOKIES_INVALID
- 中文名称：cookies 无效或过期
- 典型特征：导出 cookies 后仍被风控拦截
- 处理建议：重新导出最新 `cookies.txt`

## ERR_ENV_FFMPEG_MISSING
- 中文名称：未找到 ffmpeg
- 典型特征：`ffmpeg not found`
- 处理建议：检查 `bin/ffmpeg.exe` 是否存在

## ERR_TR_DEPENDENCY_MISSING
- 中文名称：自动转录依赖缺失
- 典型特征：`No module named 'faster_whisper'` 或 `No module named 'whisper'`
- 处理建议：安装或自动安装转录依赖

## ERR_TR_TRANSCRIBE_FAILED
- 中文名称：自动转录失败
- 典型特征：已生成 wav，但没有生成 `.auto.srt`
- 处理建议：查看日志、切换 CPU 模式、检查模型下载

## ERR_AI_ANALYSIS_FAILED
- 中文名称：AI 热点分析失败
- 典型特征：未生成 `transcript.json` 或候选片段列表为空
- 处理建议：检查字幕/转录结果和模型配置

## ERR_EXP_CLIP_FAILED
- 中文名称：片段裁剪失败
- 典型特征：`clip.mp4` 未生成
- 处理建议：检查时间范围、源视频和 ffmpeg

## ERR_EXP_HARDSUB_FAILED
- 中文名称：硬字幕烧录失败
- 典型特征：`clip.hardsub.mp4` 未生成，日志含 ffmpeg filter 报错
- 处理建议：检查字幕文件、特殊字符、字体与 ffmpeg 参数
