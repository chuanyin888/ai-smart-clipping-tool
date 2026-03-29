# Changelog

## Final corrected GitHub package
- Based on the final working local package
- Keeps `Start.vbs` disclaimer launcher and `Start.bat` helper launcher
- Adds `DISCLAIMER_CN.md` and `ERROR_CODES_CN.md`
- Sets repository homepage to Chinese README and keeps an English README entry
- Merges historical version notes into this changelog

## README_V4_CN
# Windows 便携版 V4 说明

## V4 新增
- 自动识别本地 `bin/ffmpeg.exe`
- 支持 `cookies.txt` 文件
- 支持本地视频 + 本地字幕模式
- 下载时优先尝试英文字幕，没有英文时自动回退到简体中文字幕
- 如果源字幕已经是中文，会自动跳过翻译
- 如果 `work/<slug>/source` 里已经有视频和字幕，会自动跳过重复下载

## 推荐目录
- `bin/ffmpeg.exe`
- `bin/ffprobe.exe`
- `cookies.txt`（可选）

## 链接模式
1. 准备 `cookies.txt`（推荐）
2. 双击 `启动.bat`
3. 选择“链接模式”
4. 粘贴 YouTube 地址
5. 选择翻译方式
6. 开始处理

## 本地文件模式
1. 双击 `启动.bat`
2. 选择“本地视频 + 本地字幕”
3. 选择本地视频文件
4. 选择本地 `.srt` 字幕文件
5. 开始处理

## 当前注意事项
- 第一次处理 YouTube 时，仍可能需要有效的 `cookies.txt`
- 某些公开视频也可能受到地区、网络或风控影响
- 如果源字幕已经是中文，建议把翻译方式设为 `none`

## README_V5_CN
# V5 测试说明

这版修了两个重点：

1. 修复 Windows 下 `burn_subtitles.py` 的 ffmpeg 滤镜转义问题，重点处理标题中的逗号、冒号、百分号、方括号等字符。
2. 某个 clip 导出失败时，不再让整个任务中断；失败会记录到 `work/<slug>/clips/failures.txt`，其他片段继续导出。

## 选择剪几个热点

默认导出前 4 个候选。

你也可以自己选：

```bat
python app.py --url "https://www.youtube.com/watch?v=xxxx" --export-ids "1,3,5"
```

或者：

```bat
python app.py --url "https://www.youtube.com/watch?v=xxxx" --export-ids "clip-01,clip-03"
```

全部导出：

```bat
python app.py --url "https://www.youtube.com/watch?v=xxxx" --export-ids all
```

## README_V6_CN
# V6 说明

- 新增“输出几个视频”菜单，可选前 N 个或指定编号。
- 运行日志改成右侧面板，可打开/关闭。
- 处理完成后直接显示完整输出目录，并提供打开/关闭目录显示按钮。
- 双击 `启动.bat` 后，CMD 会隐藏，只显示图形界面。

## README_V7_CN
# V7 说明

- 先“准备素材 / 开始 AI 分析”，再在候选片段列表中勾选要导出的热点。
- 热点数量默认 3 个，可选 1 到 10。
- 单条热点默认时长 20 到 35 秒。
- 每条候选支持手动修改开始时间、结束时间、标题、两句简介。
- 点击“预览”会生成不带字幕的临时预览片段并调用系统播放器打开。
- 生成时可选择是否烧录字幕；勾选多少就导出多少。
- 运行日志默认在右侧面板，可打开或隐藏。
- 处理完成后会显示输出目录，并可直接打开。

## README_V9_CN
# V9 自动转录修正版

- 自动转录依赖改为运行时自动检查并按需安装。
- 当视频无字幕时，会优先尝试 faster-whisper，其次回退到 openai-whisper。
- 保留 V8 的界面改进与日志面板。

## README_V10_CN
# V10 自动转录稳定修正版

- 修复 Windows 便携版自动转录优先误走 CUDA，导致缺少 `cublas64_12.dll` 的问题。
- `faster-whisper` 现在强制使用 CPU，并按 `int8 -> int8_float32 -> float32` 依次回退。
- 自动转录默认模型调整为 `base`，更适合首次使用时的速度与稳定性。
- 保留 V9 的自动安装依赖逻辑与 V8 的界面改进。

## README_V11_CN
# V11
- 候选片段区新增原文/中文参考对照显示。
- 非中文字幕候选会自动生成中文参考翻译；原语言为中文时不显示中文参考区。

## README_V12_CN
# V12
- 新增顶部运行状态步骤条
- 新增动画进度条，运行时持续显示
- 新增当前阶段/当前说明文本
- 运行中自动禁用主按钮，避免误触
- 通过日志自动识别大环节：准备素材、获取字幕/视频、自动转录、AI分析、导出、完成
