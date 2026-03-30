[中文](./README.md) | [English](./README_EN.md)


[查看「内容方向」详细说明](./CONTENT_DIRECTION_GUIDE_CN.md)
> 重要提示：下载并解压压缩包后，请先运行 `EnvCheck.exe` 检测当前电脑环境。
> 若检测结果存在缺失项，请先按提示完成安装或配置，再启动主程序。
> 主程序为：Start.vbs
> <img width="982" height="732" alt="image" src="https://github.com/user-attachments/assets/094f6ede-3a0d-4aaa-aeed-3b309473ae7c" />

# AI智能剪辑工具

AI智能剪辑工具是一个以 Windows 为主的本地桌面工作流，用于把长视频、YouTube 视频处理成多个短片，并支持可选的中文字幕硬字幕导出。

## 主要功能

- YouTube 链接模式 / 本地文件模式
- 有字幕时优先下载字幕
- 无字幕时自动转录兜底
- AI 热点片段分析
- 手动勾选、预览、修改候选片段
- 可选翻译与硬字幕烧录
- `Start.vbs` 作为主启动入口



## Windows 快速开始

1. 解压项目
2. 将 `ffmpeg.exe`、`ffprobe.exe`、`ffplay.exe` 放到 `bin/` 目录
3. 如需处理被风控的 YouTube 视频，请准备自己的 `cookies.txt`
4. 安装依赖：

```bat
pip install -r requirements.txt
```

5. 双击 `Start.vbs`

## 运行说明

### heuristic 模式
- 本地启发式分析
- 不调用云端大模型
- 不消耗 API 额度

### llm 模式
- 调用你自己配置的 API Base / API Key / Model
- 是否收费取决于你的接口提供商

## 主启动规则

- 普通用户请直接使用 `Start.vbs`
- `Start.bat` 仅作为内部辅助启动脚本

## 常见限制

部分 YouTube 视频会触发风控校验，导致无法直接下载。这种情况下请：
- 更新 `cookies.txt`
- 或改用本地视频模式

详细错误说明见：`docs/error-codes.md`
> 感谢抖音：洛克AI 提供的 skill 支持与思路参考。
> ![3d2847f7ce6258c752215105f1fd3876](https://github.com/user-attachments/assets/2db4e9be-0b83-4607-ad93-d62024344f23)
