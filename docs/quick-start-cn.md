# Quick Start (Chinese)

## 1. 准备运行环境
- Windows 10 或更高版本
- Python 3.11 / 3.12 推荐
- ffmpeg 放到 `bin/`
- 需要时准备 `cookies.txt`

## 2. 安装依赖
```bat
pip install -r requirements.txt
```

## 3. 启动
双击 `Start.vbs`

## 4. 基本流程
1. 输入 YouTube 链接或选择本地视频
2. 点击“准备素材”
3. 点击“开始 AI 分析”
4. 勾选建议片段
5. 预览
6. 导出选中片段

## 5. 模式说明
- `heuristic`：本地分析，不消耗 API
- `llm`：使用你的 API 配置，可能消耗 API 额度
