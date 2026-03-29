from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import re
from pathlib import Path

from scripts.translate_srt import translate_texts
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent
WORK_ROOT = ROOT / 'work'


def seconds_to_hms(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total = total_ms // 1000
    s = total % 60
    total //= 60
    m = total % 60
    h = total // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def hms_to_seconds(text: str) -> float:
    text = text.strip().replace(',', '.')
    if not text:
        return 0.0
    parts = text.split(':')
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = '0', parts[0], parts[1]
    else:
        raise ValueError('时间格式应为 HH:MM:SS.mmm')
    return int(h) * 3600 + int(m) * 60 + float(s)


def looks_chinese(text: str) -> bool:
    s = text or ''
    if not s.strip():
        return False
    cjk = len(re.findall(r"[\u4e00-\u9fff]", s))
    letters = len(re.findall(r"[A-Za-z]", s))
    return cjk >= max(2, letters // 2)


def candidate_is_chinese(clip: dict) -> bool:
    parts = [clip.get('title', '')]
    parts.extend(clip.get('summary') or [])
    joined = ' '.join(str(x) for x in parts if x)
    return looks_chinese(joined)


PROVIDER_BASES = {
    'OpenAI Compatible': 'https://api.openai.com/v1',
    'DeepSeek Compatible': 'https://api.deepseek.com/v1',
    '自定义接口': '',
}

PROVIDER_MODELS = {
    'OpenAI Compatible': ['gpt-4.1-mini', 'gpt-4.1', 'gpt-4o-mini', 'gpt-4o', '自定义'],
    'DeepSeek Compatible': ['deepseek-chat', 'deepseek-reasoner', '自定义'],
    '自定义接口': ['自定义'],
}

ERROR_MAP = [
    ("ERR_YT_BOT_VERIFY_BLOCK", "YouTube 风控验证拦截", ["sign in to confirm you're not a bot", "no video formats found", "requested format is not available"]),
    ("ERR_ENV_COOKIES_INVALID", "cookies 已失效或不可用", ["cookies are no longer valid", "cookies invalid"]),
    ("ERR_YT_SUBTITLE_NOT_FOUND", "未找到可用字幕", ["has no subtitles", "has no automatic captions", "there are no subtitles for the requested languages"]),
    ("ERR_TR_DEPENDENCY_MISSING", "自动转录依赖缺失", ["no module named 'faster_whisper'", "no module named 'whisper'", "installing missing dependency"]),
    ("ERR_TR_TRANSCRIBE_FAILED", "自动转录失败", ["whisper failed", "faster-whisper failed", "no subtitle found. running auto transcription"]),
    ("ERR_EXP_HARDSUB_FAILED", "硬字幕烧录失败", ["error opening output files: filter not found", "no such filter"]),
]

def detect_error(text: str):
    low = (text or '').lower()
    for code, zh, patterns in ERROR_MAP:
        if any(p in low for p in patterns):
            return code, zh
    return None


class ClipRow:
    def __init__(self, app: 'App', parent: tk.Widget, clip: dict, index: int) -> None:
        self.app = app
        self.clip = dict(clip)
        self.default = dict(clip)
        self.selected_var = tk.BooleanVar(value=True)
        self.start_var = tk.StringVar(value=seconds_to_hms(float(clip['start_seconds'])))
        self.end_var = tk.StringVar(value=seconds_to_hms(float(clip['end_seconds'])))
        self.title_var = tk.StringVar(value=clip.get('title', ''))
        self.summary1_var = tk.StringVar(value=(clip.get('summary') or ['',''])[0])
        self.summary2_var = tk.StringVar(value=(clip.get('summary') or ['',''])[1])
        self.title_zh_var = tk.StringVar(value=clip.get('title_zh', ''))
        self.summary1_zh_var = tk.StringVar(value=(clip.get('summary_zh') or ['',''])[0])
        self.summary2_zh_var = tk.StringVar(value=(clip.get('summary_zh') or ['',''])[1])
        self.show_zh = bool(self.title_zh_var.get().strip() or self.summary1_zh_var.get().strip() or self.summary2_zh_var.get().strip())

        outer = ttk.Frame(parent)
        outer.grid_columnconfigure(1, weight=1)
        self.frame = outer

        ttk.Checkbutton(outer, variable=self.selected_var).grid(row=0, column=0, padx=(6, 8), pady=8, sticky='n')

        content = ttk.Frame(outer)
        content.grid(row=0, column=1, sticky='ew', pady=4)
        content.grid_columnconfigure(0, weight=1)
        if self.show_zh:
            content.grid_columnconfigure(1, weight=1)

        left_box = ttk.LabelFrame(content, text='原文')
        left_box.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        left_box.grid_columnconfigure(4, weight=1)
        ttk.Label(left_box, text=f"片段 {index:02d} / {clip.get('id','')}", font=('', 10, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(6, 2), padx=6)
        ttk.Button(left_box, text='预览', command=self.preview).grid(row=0, column=3, sticky='e', padx=6, pady=(6, 2))
        ttk.Button(left_box, text='恢复默认', command=self.reset).grid(row=0, column=4, sticky='e', padx=(0, 6), pady=(6, 2))

        ttk.Label(left_box, text='开始').grid(row=1, column=0, sticky='w', padx=(6, 4))
        ttk.Entry(left_box, textvariable=self.start_var, width=14).grid(row=1, column=1, sticky='w', padx=(0, 8))
        ttk.Label(left_box, text='结束').grid(row=1, column=2, sticky='w', padx=(0, 4))
        ttk.Entry(left_box, textvariable=self.end_var, width=14).grid(row=1, column=3, sticky='w', padx=(0, 8))

        ttk.Label(left_box, text='标题').grid(row=2, column=0, sticky='w', padx=(6, 4), pady=(0, 6))
        ttk.Entry(left_box, textvariable=self.title_var).grid(row=2, column=1, columnspan=4, sticky='ew', padx=(0, 6), pady=(0, 6))
        ttk.Label(left_box, text='简介1').grid(row=3, column=0, sticky='w', padx=(6, 4), pady=(0, 6))
        ttk.Entry(left_box, textvariable=self.summary1_var).grid(row=3, column=1, columnspan=4, sticky='ew', padx=(0, 6), pady=(0, 6))
        ttk.Label(left_box, text='简介2').grid(row=4, column=0, sticky='w', padx=(6, 4), pady=(0, 8))
        ttk.Entry(left_box, textvariable=self.summary2_var).grid(row=4, column=1, columnspan=4, sticky='ew', padx=(0, 6), pady=(0, 8))

        if self.show_zh:
            right_box = ttk.LabelFrame(content, text='中文参考')
            right_box.grid(row=0, column=1, sticky='nsew')
            right_box.grid_columnconfigure(1, weight=1)
            ttk.Label(right_box, text='标题').grid(row=0, column=0, sticky='w', padx=(6, 4), pady=(6, 6))
            title_zh = ttk.Entry(right_box, textvariable=self.title_zh_var)
            title_zh.grid(row=0, column=1, sticky='ew', padx=(0, 6), pady=(6, 6))
            ttk.Label(right_box, text='简介1').grid(row=1, column=0, sticky='w', padx=(6, 4), pady=(0, 6))
            summary1_zh = ttk.Entry(right_box, textvariable=self.summary1_zh_var)
            summary1_zh.grid(row=1, column=1, sticky='ew', padx=(0, 6), pady=(0, 6))
            ttk.Label(right_box, text='简介2').grid(row=2, column=0, sticky='w', padx=(6, 4), pady=(0, 8))
            summary2_zh = ttk.Entry(right_box, textvariable=self.summary2_zh_var)
            summary2_zh.grid(row=2, column=1, sticky='ew', padx=(0, 6), pady=(0, 8))
            for widget in (title_zh, summary1_zh, summary2_zh):
                widget.state(['readonly'])

        ttk.Separator(outer, orient='horizontal').grid(row=1, column=0, columnspan=2, sticky='ew', padx=4, pady=(0, 4))

    def pack_into(self, row: int) -> None:
        self.frame.grid(row=row, column=0, sticky='ew', padx=4, pady=2)


    def update_translation(self, title_zh: str, summary_zh: list[str]) -> None:
        self.title_zh_var.set(title_zh or '')
        self.summary1_zh_var.set((summary_zh or ['', ''])[0])
        self.summary2_zh_var.set((summary_zh or ['', ''])[1])

    def to_dict(self) -> dict:
        start_seconds = hms_to_seconds(self.start_var.get())
        end_seconds = hms_to_seconds(self.end_var.get())
        if end_seconds <= start_seconds:
            raise ValueError(f"{self.clip.get('id')} 的结束时间必须大于开始时间")
        duration = round(end_seconds - start_seconds, 3)
        start = seconds_to_hms(start_seconds).replace('.', ',')
        end = seconds_to_hms(end_seconds).replace('.', ',')
        return {
            'id': self.clip.get('id'),
            'start': start,
            'end': end,
            'start_seconds': start_seconds,
            'end_seconds': end_seconds,
            'duration_seconds': duration,
            'title': self.title_var.get().strip() or self.default.get('title', ''),
            'summary': [self.summary1_var.get().strip(), self.summary2_var.get().strip()],
            'reason': self.clip.get('reason', ''),
        }

    def reset(self) -> None:
        self.start_var.set(seconds_to_hms(float(self.default['start_seconds'])))
        self.end_var.set(seconds_to_hms(float(self.default['end_seconds'])))
        self.title_var.set(self.default.get('title', ''))
        summ = self.default.get('summary') or ['', '']
        self.summary1_var.set(summ[0])
        self.summary2_var.set(summ[1])

    def preview(self) -> None:
        self.app.preview_row(self)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title('AI 智能剪辑工具 / AI Smart Clipping Tool VX:lsf343634352')
        self.geometry('1520x980')
        self.minsize(1260, 820)

        self.input_mode_var = tk.StringVar(value='url')
        self.url_var = tk.StringVar()
        self.cookies_var = tk.StringVar(value=str(ROOT / 'cookies.txt') if (ROOT / 'cookies.txt').exists() else '')
        self.local_video_var = tk.StringVar()
        self.local_srt_var = tk.StringVar()

        self.engine_var = tk.StringVar(value='heuristic')
        self.num_candidates_var = tk.IntVar(value=3)
        self.min_duration_var = tk.IntVar(value=20)
        self.max_duration_var = tk.IntVar(value=35)
        self.direction_var = tk.StringVar(value='')

        self.translator_var = tk.StringVar(value='offline')
        self.burn_subtitles_var = tk.BooleanVar(value=True)
        self.provider_var = tk.StringVar(value='OpenAI Compatible')
        self.api_base_var = tk.StringVar(value=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'))
        self.api_key_var = tk.StringVar(value=os.getenv('OPENAI_API_KEY', ''))
        self.model_var = tk.StringVar(value=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
        self.custom_model_var = tk.StringVar(value='')

        self.status_var = tk.StringVar(value='就绪')
        self.stage_var = tk.StringVar(value='当前阶段：就绪')
        self.stage_message_var = tk.StringVar(value='等待开始')
        self.busy = False
        self.current_stage_key = 'idle'
        self.stage_order = ['prepare', 'subtitle', 'transcribe', 'analyze', 'export', 'done']
        self.stage_titles = {
            'idle': '就绪',
            'prepare': '准备素材',
            'subtitle': '获取字幕/视频',
            'transcribe': '自动转录',
            'analyze': 'AI 分析热点',
            'export': '导出选中片段',
            'done': '处理完成',
            'error': '处理失败',
        }
        self.step_labels = {}
        self.output_path_var = tk.StringVar(value='')
        self.analysis_json_path: Path | None = None
        self.source_video_path: Path | None = None
        self.source_srt_path: Path | None = None
        self.current_base_dir: Path | None = None
        self.proc: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.clip_rows: list[ClipRow] = []
        self.preview_proc: subprocess.Popen[str] | None = None
        self.translating_candidates = False

        self._build_ui()
        self.hide_log_panel()
        self.after(120, self._drain_log_queue)
        self._switch_input_mode()
        self._on_provider_change()
        self._update_api_frame()

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill='x', padx=12, pady=10)
        self.prepare_btn = ttk.Button(top, text='准备素材', command=self.prepare_assets)
        self.prepare_btn.pack(side='left')
        self.analyze_btn = ttk.Button(top, text='开始 AI 分析', command=self.analyze_only)
        self.analyze_btn.pack(side='left', padx=(8, 0))
        self.export_btn = ttk.Button(top, text='生成选中片段', command=self.export_selected)
        self.export_btn.pack(side='left', padx=(8, 0))
        ttk.Label(top, textvariable=self.status_var).pack(side='right')

        status_frame = ttk.LabelFrame(self, text='运行状态')
        status_frame.pack(fill='x', padx=12, pady=(0, 10))
        step_bar = ttk.Frame(status_frame)
        step_bar.pack(fill='x', padx=12, pady=(8, 4))
        for idx, key in enumerate(['prepare', 'subtitle', 'transcribe', 'analyze', 'export', 'done']):
            lbl = ttk.Label(step_bar, text=f"{idx+1}. {self.stage_titles[key]}", relief='groove', anchor='center')
            lbl.grid(row=0, column=idx, sticky='ew', padx=(0 if idx == 0 else 6, 0))
            step_bar.grid_columnconfigure(idx, weight=1)
            self.step_labels[key] = lbl
        msg_row = ttk.Frame(status_frame)
        msg_row.pack(fill='x', padx=12, pady=(4, 8))
        ttk.Label(msg_row, textvariable=self.stage_var).pack(side='left')
        ttk.Label(msg_row, text='｜').pack(side='left', padx=8)
        ttk.Label(msg_row, textvariable=self.stage_message_var).pack(side='left', fill='x', expand=True)
        self.progress = ttk.Progressbar(msg_row, mode='indeterminate', length=220)
        self.progress.pack(side='right')

        self.paned = ttk.Panedwindow(self, orient='horizontal')
        self.paned.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        left = ttk.Frame(self.paned)
        self.right_panel = ttk.Frame(self.paned)
        self.paned.add(left, weight=5)
        self.paned.add(self.right_panel, weight=2)

        left_outer = ttk.Frame(left)
        left_outer.pack(fill='both', expand=True)
        self.left_canvas = tk.Canvas(left_outer, highlightthickness=0)
        self.left_canvas.pack(side='left', fill='both', expand=True)
        left_scroll = ttk.Scrollbar(left_outer, orient='vertical', command=self.left_canvas.yview)
        left_scroll.pack(side='right', fill='y')
        self.left_canvas.configure(yscrollcommand=left_scroll.set)
        self.left_inner = ttk.Frame(self.left_canvas)
        self.left_window = self.left_canvas.create_window((0, 0), window=self.left_inner, anchor='nw')
        self.left_inner.bind('<Configure>', lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox('all')))
        self.left_canvas.bind('<Configure>', lambda e: self.left_canvas.itemconfigure(self.left_window, width=e.width))

        def _on_mousewheel(event):
            try:
                self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
            except tk.TclError:
                pass

        self.left_canvas.bind_all('<MouseWheel>', _on_mousewheel)

        mode_frame = ttk.LabelFrame(self.left_inner, text='素材输入')
        mode_frame.pack(fill='x', pady=6)
        mode_row = ttk.Frame(mode_frame)
        mode_row.pack(fill='x', padx=12, pady=10)
        ttk.Radiobutton(mode_row, text='YouTube 链接', variable=self.input_mode_var, value='url', command=self._switch_input_mode).pack(side='left')
        ttk.Radiobutton(mode_row, text='本地视频 + 字幕', variable=self.input_mode_var, value='local', command=self._switch_input_mode).pack(side='left', padx=(12, 0))

        self.url_frame = ttk.Frame(mode_frame)
        self.url_frame.pack(fill='x', padx=12, pady=(0, 10))
        ttk.Label(self.url_frame, text='YouTube 地址').grid(row=0, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(self.url_frame, textvariable=self.url_var).grid(row=0, column=1, sticky='ew', padx=8, pady=(0, 6))
        ttk.Label(self.url_frame, text='cookies.txt').grid(row=1, column=0, sticky='w')
        ttk.Entry(self.url_frame, textvariable=self.cookies_var).grid(row=1, column=1, sticky='ew', padx=8)
        ttk.Button(self.url_frame, text='浏览', command=self.pick_cookies).grid(row=1, column=2, padx=(0, 6))
        self.url_frame.columnconfigure(1, weight=1)

        self.local_frame = ttk.Frame(mode_frame)
        ttk.Label(self.local_frame, text='视频文件').grid(row=0, column=0, sticky='w', pady=(0, 6))
        ttk.Entry(self.local_frame, textvariable=self.local_video_var).grid(row=0, column=1, sticky='ew', padx=8, pady=(0, 6))
        ttk.Button(self.local_frame, text='浏览', command=self.pick_video).grid(row=0, column=2, padx=(0, 6), pady=(0, 6))
        ttk.Label(self.local_frame, text='字幕文件').grid(row=1, column=0, sticky='w')
        ttk.Entry(self.local_frame, textvariable=self.local_srt_var).grid(row=1, column=1, sticky='ew', padx=8)
        ttk.Button(self.local_frame, text='浏览', command=self.pick_srt).grid(row=1, column=2, padx=(0, 6))
        self.local_frame.columnconfigure(1, weight=1)

        ai_frame = ttk.LabelFrame(self.left_inner, text='AI 分析')
        ai_frame.pack(fill='x', pady=6)
        row = ttk.Frame(ai_frame)
        row.pack(fill='x', padx=12, pady=10)
        ttk.Label(row, text='AI 引擎').pack(side='left')
        engine = ttk.Combobox(row, textvariable=self.engine_var, values=['heuristic', 'llm'], state='readonly', width=14)
        engine.pack(side='left', padx=(6, 12))
        engine.bind('<<ComboboxSelected>>', lambda _e: self._update_api_frame())
        ttk.Label(row, text='热点数').pack(side='left')
        tk.Spinbox(row, from_=1, to=10, textvariable=self.num_candidates_var, width=5).pack(side='left', padx=(6, 12))
        ttk.Label(row, text='时长').pack(side='left')
        tk.Spinbox(row, from_=5, to=120, textvariable=self.min_duration_var, width=5).pack(side='left', padx=(6, 2))
        ttk.Label(row, text='到').pack(side='left')
        tk.Spinbox(row, from_=5, to=180, textvariable=self.max_duration_var, width=5).pack(side='left', padx=(2, 6))
        ttk.Label(row, text='秒').pack(side='left')

        row2 = ttk.Frame(ai_frame)
        row2.pack(fill='x', padx=12, pady=(0, 10))
        ttk.Label(row2, text='内容方向').pack(side='left')
        ttk.Entry(row2, textvariable=self.direction_var).pack(side='left', fill='x', expand=True, padx=(8, 0))

        self.mode_config_wrap = ttk.Frame(self.left_inner)
        self.mode_config_wrap.pack(fill='x', pady=6)

        self.local_mode_note = ttk.LabelFrame(self.mode_config_wrap, text='当前模式说明')
        self.local_mode_label = ttk.Label(
            self.local_mode_note,
            text='当前模式：本地启发式分析\n该模式在本机完成热点分析，不调用云端大模型接口，不会消耗您的 API 额度。\n适合快速分析、离线使用和无接口配置场景。',
            justify='left'
        )
        self.local_mode_label.pack(fill='x', padx=12, pady=10)

        self.api_frame = ttk.LabelFrame(self.mode_config_wrap, text='LLM 配置（仅 llm 分析或 openai_compatible 翻译）')
        ttk.Label(self.api_frame, text='提供商').grid(row=0, column=0, sticky='w', padx=12, pady=(10, 6))
        self.provider_combo = ttk.Combobox(self.api_frame, textvariable=self.provider_var, values=list(PROVIDER_BASES.keys()), state='readonly', width=24)
        self.provider_combo.grid(row=0, column=1, sticky='ew', padx=12, pady=(10, 6))
        self.provider_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_provider_change())
        ttk.Label(self.api_frame, text='模型').grid(row=1, column=0, sticky='w', padx=12, pady=6)
        self.model_combo = ttk.Combobox(self.api_frame, textvariable=self.model_var, values=PROVIDER_MODELS['OpenAI Compatible'], state='readonly', width=24)
        self.model_combo.grid(row=1, column=1, sticky='ew', padx=12, pady=6)
        self.model_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_model_change())
        self.custom_model_entry = ttk.Entry(self.api_frame, textvariable=self.custom_model_var)
        ttk.Label(self.api_frame, text='API Base').grid(row=2, column=0, sticky='w', padx=12, pady=6)
        self.api_base_entry = ttk.Entry(self.api_frame, textvariable=self.api_base_var)
        self.api_base_entry.grid(row=2, column=1, sticky='ew', padx=12, pady=6)
        ttk.Label(self.api_frame, text='API Key').grid(row=3, column=0, sticky='w', padx=12, pady=(6, 10))
        self.api_key_entry = ttk.Entry(self.api_frame, textvariable=self.api_key_var, show='*')
        self.api_key_entry.grid(row=3, column=1, sticky='ew', padx=12, pady=(6, 10))
        self.api_hint_var = tk.StringVar(value='当前模式：大模型分析\n该模式会调用您配置的接口进行热点分析，可能消耗对应 API 额度。\n请确认 API Base、API Key 和模型配置正确。')
        self.api_hint_label = ttk.Label(self.api_frame, textvariable=self.api_hint_var, justify='left')
        self.api_hint_label.grid(row=4, column=0, columnspan=2, sticky='ew', padx=12, pady=(0, 10))
        self.api_frame.columnconfigure(1, weight=1)

        suggestions = ttk.LabelFrame(self.left_inner, text='AI 建议片段')
        suggestions.pack(fill='both', expand=True, pady=6)
        toolbar = ttk.Frame(suggestions)
        toolbar.pack(fill='x', padx=12, pady=(10, 6))
        ttk.Button(toolbar, text='全选', command=self.select_all).pack(side='left')
        ttk.Button(toolbar, text='取消全选', command=self.deselect_all).pack(side='left', padx=(8, 0))
        ttk.Button(toolbar, text='反选', command=self.invert_select).pack(side='left', padx=(8, 0))
        ttk.Button(toolbar, text='清空预览缓存', command=self.clear_preview_cache).pack(side='right')

        canvas_wrap = ttk.Frame(suggestions)
        canvas_wrap.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.cards_canvas = tk.Canvas(canvas_wrap, highlightthickness=0)
        self.cards_canvas.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(canvas_wrap, orient='vertical', command=self.cards_canvas.yview)
        scroll.pack(side='right', fill='y')
        self.cards_canvas.configure(yscrollcommand=scroll.set)
        self.cards_inner = ttk.Frame(self.cards_canvas)
        self.cards_window = self.cards_canvas.create_window((0, 0), window=self.cards_inner, anchor='nw')
        self.cards_inner.bind('<Configure>', lambda e: self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox('all')))
        self.cards_canvas.bind('<Configure>', lambda e: self.cards_canvas.itemconfigure(self.cards_window, width=e.width))

        gen_frame = ttk.LabelFrame(self.left_inner, text='生成')
        gen_frame.pack(fill='x', pady=6)
        gen_row = ttk.Frame(gen_frame)
        gen_row.pack(fill='x', padx=12, pady=10)
        ttk.Label(gen_row, text='翻译方式').pack(side='left')
        trans_combo = ttk.Combobox(gen_row, textvariable=self.translator_var, values=['none', 'offline', 'openai_compatible'], state='readonly', width=20)
        trans_combo.pack(side='left', padx=(8, 12))
        trans_combo.bind('<<ComboboxSelected>>', lambda _e: self._update_api_frame())
        ttk.Checkbutton(gen_row, text='是否烧录字幕', variable=self.burn_subtitles_var).pack(side='left')

        output_frame = ttk.LabelFrame(self.left_inner, text='结果')
        output_frame.pack(fill='x', pady=6)
        self.output_text = tk.Text(output_frame, height=5, wrap='none')
        self.output_text.pack(fill='x', padx=12, pady=(10, 8))
        self.output_text.configure(state='disabled')
        out_scroll = ttk.Scrollbar(output_frame, orient='horizontal', command=self.output_text.xview)
        out_scroll.pack(fill='x', padx=12, pady=(0, 8))
        self.output_text.configure(xscrollcommand=out_scroll.set)
        acts = ttk.Frame(output_frame)
        acts.pack(fill='x', padx=12, pady=(0, 10))
        ttk.Button(acts, text='打开目录', width=14, command=self.open_output_dir).pack(side='left')
        ttk.Button(acts, text='关闭目录显示', width=14, command=self.clear_output_dir).pack(side='left', padx=(8, 0))

        right_header = ttk.Frame(self.right_panel)
        right_header.pack(fill='x', padx=12, pady=(12, 8))
        ttk.Label(right_header, text='运行日志', font=('', 11, 'bold')).pack(side='left')
        ttk.Button(right_header, text='关闭日志', width=12, command=self.hide_log_panel).pack(side='right')
        log_frame = ttk.Frame(self.right_panel)
        log_frame.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self.log_text = tk.Text(log_frame, wrap='word')
        self.log_text.pack(side='left', fill='both', expand=True)
        yscroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        yscroll.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=yscroll.set)
        btns = ttk.Frame(self.left_inner)
        btns.pack(fill='x', pady=(0, 6))
        ttk.Button(btns, text='打开日志', width=12, command=self.show_log_panel).pack(side='left')
        ttk.Button(btns, text='隐藏日志', width=12, command=self.hide_log_panel).pack(side='left', padx=(8, 0))


    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = 'disabled' if busy else 'normal'
        for btn in (self.prepare_btn, self.analyze_btn, self.export_btn):
            try:
                btn.configure(state=state)
            except tk.TclError:
                pass
        if busy:
            try:
                self.progress.start(7)
            except tk.TclError:
                pass
        else:
            try:
                self.progress.stop()
            except tk.TclError:
                pass

    def _set_stage(self, key: str, message: str | None = None) -> None:
        self.current_stage_key = key
        title = self.stage_titles.get(key, key)
        self.stage_var.set(f'当前阶段：{title}')
        if message is not None:
            self.stage_message_var.set(message)
        active_seen = False
        for stage in ['prepare', 'subtitle', 'transcribe', 'analyze', 'export', 'done']:
            lbl = self.step_labels.get(stage)
            if not lbl:
                continue
            if key == 'error':
                lbl.configure(style='TLabel')
                continue
            if stage == key:
                lbl.configure(background='#fff3cd', foreground='#7a4b00')
                active_seen = True
            elif not active_seen:
                lbl.configure(background='#e8f5e9', foreground='#1b5e20')
            else:
                lbl.configure(background='#f3f3f3', foreground='#666666')

    def _update_stage_from_log(self, line: str) -> None:
        s = line.strip()
        low = s.lower()
        if not s:
            return
        if '开始执行：' in s:
            self._set_stage('prepare', '开始执行任务')
        elif 'extracting url' in low or 'downloading webpage' in low or 'running:' in low and 'yt_dlp' in low:
            self._set_stage('subtitle', '正在获取视频与字幕资源…')
        elif '[download]' in low or '[merger]' in low:
            self._set_stage('subtitle', s[:120])
        elif 'no subtitle found. running auto transcription' in low or 'installing missing dependency' in low or 'faster-whisper' in low or 'whisper' in low or '.auto.16k.wav' in low:
            self._set_stage('transcribe', s[:120])
        elif 'analysis_json=' in low or 'candidate clips:' in low or 'analysis completed' in low or 'ai 热点分析完成' in s:
            self._set_stage('analyze', '已生成候选热点片段')
        elif 'scripts\clip_video.py' in low or 'scripts\burn_subtitles.py' in low or 'scripts\translate_srt.py' in low or '导出' in s:
            self._set_stage('export', s[:120])
        elif '任务结束，退出码：0' in s:
            self._set_stage('done', '全部任务已完成')
        elif '任务结束，退出码：' in s and '0' not in s.split('：')[-1].strip():
            self._set_stage('error', s)

    def _on_provider_change(self) -> None:
        provider = (self.provider_var.get() or 'OpenAI Compatible').strip()
        models = PROVIDER_MODELS.get(provider, ['自定义'])
        self.model_combo.configure(values=models)
        current_base = self.api_base_var.get().strip()
        known_bases = set(PROVIDER_BASES.values())
        if provider != '自定义接口' and (not current_base or current_base in known_bases):
            self.api_base_var.set(PROVIDER_BASES.get(provider, ''))

        current_model = (self.model_var.get() or '').strip()
        if current_model not in models:
            self.model_var.set(models[0])
        self._on_model_change()

    def _on_model_change(self) -> None:
        selected = (self.model_var.get() or '').strip()
        if selected == '自定义':
            self.custom_model_entry.grid(row=1, column=2, sticky='ew', padx=(0, 12), pady=6)
        else:
            self.custom_model_entry.grid_forget()
            self.custom_model_var.set('')

    def _effective_model(self) -> str:
        selected = (self.model_var.get() or '').strip()
        if selected == '自定义':
            return self.custom_model_var.get().strip()
        return selected

    def _update_api_frame(self) -> None:
        need_api = self.engine_var.get() == 'llm' or self.translator_var.get() == 'openai_compatible'
        if need_api:
            if self.local_mode_note.winfo_ismapped():
                self.local_mode_note.pack_forget()
            if not self.api_frame.winfo_ismapped():
                self.api_frame.pack(fill='x')
        else:
            if self.api_frame.winfo_ismapped():
                self.api_frame.pack_forget()
            if not self.local_mode_note.winfo_ismapped():
                self.local_mode_note.pack(fill='x')
        state = 'readonly' if need_api else 'disabled'
        entry_state = 'normal' if need_api else 'disabled'
        self.provider_combo.configure(state=state)
        self.model_combo.configure(state=state)
        self.api_base_entry.configure(state=entry_state)
        self.api_key_entry.configure(state=entry_state)
        self.custom_model_entry.configure(state=entry_state)
        self._on_provider_change()

    def _switch_input_mode(self) -> None:
        if self.input_mode_var.get() == 'url':
            self.local_frame.pack_forget()
            self.url_frame.pack(fill='x', padx=12, pady=(0, 10))
        else:
            self.url_frame.pack_forget()
            self.local_frame.pack(fill='x', padx=12, pady=(0, 10))

    def pick_cookies(self) -> None:
        path = filedialog.askopenfilename(title='选择 cookies.txt', filetypes=[('Text Files', '*.txt'), ('All Files', '*.*')])
        if path:
            self.cookies_var.set(path)

    def pick_video(self) -> None:
        path = filedialog.askopenfilename(title='选择本地视频', filetypes=[('Video Files', '*.mp4 *.webm *.mkv *.mov *.m4v'), ('All Files', '*.*')])
        if path:
            self.local_video_var.set(path)

    def pick_srt(self) -> None:
        path = filedialog.askopenfilename(title='选择本地字幕', filetypes=[('SRT Files', '*.srt'), ('All Files', '*.*')])
        if path:
            self.local_srt_var.set(path)

    def set_output_display(self, text: str) -> None:
        self.output_text.configure(state='normal')
        self.output_text.delete('1.0', 'end')
        if text:
            self.output_text.insert('1.0', text)
        self.output_text.configure(state='disabled')

    def append_log(self, text: str) -> None:
        self.log_text.insert('end', text)
        self.log_text.see('end')
        for line in text.splitlines():
            self._update_stage_from_log(line)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                self.append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def show_log_panel(self) -> None:
        panes = self.paned.panes()
        if str(self.right_panel) not in panes:
            self.paned.add(self.right_panel, weight=2)

    def hide_log_panel(self) -> None:
        try:
            self.paned.forget(self.right_panel)
        except tk.TclError:
            pass

    def _build_common_cmd(self) -> list[str] | None:
        cmd = [sys.executable, str(ROOT / 'app.py')]
        if self.input_mode_var.get() == 'url':
            url = self.url_var.get().strip()
            if not url:
                messagebox.showwarning('提示', '请先输入 YouTube 地址。')
                return None
            cmd += ['--url', url]
            cookies = self.cookies_var.get().strip()
            if cookies:
                cmd += ['--cookies-file', cookies]
        else:
            video = self.local_video_var.get().strip()
            srt = self.local_srt_var.get().strip()
            if not video or not srt:
                messagebox.showwarning('提示', '请选择本地视频和本地字幕。')
                return None
            cmd += ['--input-video', video, '--input-srt', srt]
        if (ROOT / 'bin').exists():
            cmd += ['--ffmpeg-location', str(ROOT / 'bin')]
        cmd += [
            '--selection-mode', self.engine_var.get(),
            '--num-candidates', str(self.num_candidates_var.get()),
            '--min-duration', str(self.min_duration_var.get()),
            '--max-duration', str(self.max_duration_var.get()),
        ]
        if self.api_key_var.get().strip():
            cmd += ['--api-key', self.api_key_var.get().strip()]
        if self.api_base_var.get().strip():
            cmd += ['--api-base', self.api_base_var.get().strip()]
        if self._effective_model().strip():
            cmd += ['--model', self._effective_model().strip()]
            cmd += ['--candidate-model', self._effective_model().strip()]
        return cmd

    def _run_command(self, cmd: list[str], on_finish=None) -> None:
        if self.proc is not None:
            messagebox.showinfo('提示', '当前已有任务正在运行。')
            return
        self.show_log_panel()
        self.log_queue.put('\n==============================\n')
        self.log_queue.put('开始执行：\n' + ' '.join(cmd) + '\n\n')
        self.status_var.set('运行中')

        def worker() -> None:
            env = os.environ.copy()
            env.setdefault('PYTHONUTF8', '1')
            self.proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env)
            lines: list[str] = []
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                lines.append(line)
                self.log_queue.put(line)
            code = self.proc.wait()
            self.proc = None
            self.log_queue.put(f'\n任务结束，退出码：{code}\n')
            if on_finish:
                self.after(0, lambda: on_finish(code, ''.join(lines)))
            else:
                self.after(0, lambda: self._after_generic(code))

        threading.Thread(target=worker, daemon=True).start()

    def _after_generic(self, code: int) -> None:
        self._set_busy(False)
        self.status_var.set('完成' if code == 0 else f'失败（{code}）')
        self._set_stage('done' if code == 0 else 'error', '任务已结束')

    def _parse_output_markers(self, text: str) -> None:
        for line in text.splitlines():
            if line.startswith('ANALYSIS_JSON='):
                self.analysis_json_path = Path(line.split('=', 1)[1].strip())
                self.current_base_dir = self.analysis_json_path.parents[1]
            elif line.startswith('SOURCE_VIDEO='):
                self.source_video_path = Path(line.split('=', 1)[1].strip())
            elif line.startswith('SOURCE_SRT='):
                self.source_srt_path = Path(line.split('=', 1)[1].strip())
            elif line.startswith('CLIPS_DIR='):
                self.output_path_var.set(line.split('=', 1)[1].strip())
                self.set_output_display(self.output_path_var.get())

    def _show_error_popup(self, text: str, fallback_title: str) -> None:
        info = detect_error(text)
        if info:
            code, zh = info
            advice = {
                'ERR_YT_BOT_VERIFY_BLOCK': '请更新 cookies.txt，或改用本地视频模式。',
                'ERR_ENV_COOKIES_INVALID': '请重新导出最新 cookies.txt 后重试。',
                'ERR_YT_SUBTITLE_NOT_FOUND': '当前视频没有可用字幕，将尝试自动转录；若失败请改用本地字幕。',
                'ERR_TR_DEPENDENCY_MISSING': '自动转录依赖未准备完成，请稍后重试或检查网络。',
                'ERR_TR_TRANSCRIBE_FAILED': '自动转录未成功生成字幕，请查看日志或改用本地字幕。',
                'ERR_EXP_HARDSUB_FAILED': '硬字幕烧录失败，请检查标题特殊字符或字幕文件。',
            }.get(code, '请查看右侧日志。')
            messagebox.showerror(f'错误：{code}', f'{zh}\n\n处理建议：{advice}')
        else:
            messagebox.showwarning('提示', fallback_title)

    def prepare_assets(self) -> None:
        cmd = self._build_common_cmd()
        if not cmd:
            return
        cmd += ['--mode', 'analyze']
        self._run_command(cmd, self._after_analyze)

    def analyze_only(self) -> None:
        self.prepare_assets()

    def _after_analyze(self, code: int, text: str) -> None:
        self._set_busy(False)
        self.status_var.set('分析完成' if code == 0 else f'分析失败（{code}）')
        self._parse_output_markers(text)
        self._set_stage('analyze' if code == 0 else 'error', '分析阶段已结束' if code == 0 else '分析失败，请查看右侧日志')
        if code != 0:
            self._show_error_popup(text, '分析失败，请查看右侧日志。')
            return
        if not self.analysis_json_path or not self.analysis_json_path.exists():
            messagebox.showwarning('提示', '未找到分析结果文件。')
            return
        candidates = json.loads(self.analysis_json_path.read_text(encoding='utf-8'))
        self.populate_candidates(candidates)
        self.maybe_translate_candidate_cards(candidates)
        messagebox.showinfo('完成', 'AI 热点分析完成，请勾选需要生成的片段。')


    def maybe_translate_candidate_cards(self, candidates: list[dict]) -> None:
        if not candidates:
            return
        if all(candidate_is_chinese(c) for c in candidates):
            return
        provider = self.translator_var.get().strip() or 'offline'
        if provider == 'none':
            provider = 'offline'
        api_base = self.api_base_var.get().strip() or 'https://api.openai.com/v1'
        api_key = self.api_key_var.get().strip()
        model = self._effective_model().strip() or 'gpt-4.1-mini'
        if provider == 'openai_compatible' and not api_key:
            self.log_queue.put('未提供 API Key，跳过候选片段中文参考翻译。\n')
            return
        self.translating_candidates = True
        self.status_var.set('候选中文参考翻译中')

        def worker() -> None:
            try:
                payload = []
                indexes = []
                for i, clip in enumerate(candidates):
                    if candidate_is_chinese(clip):
                        continue
                    payload.extend([clip.get('title', ''), *(clip.get('summary') or ['', ''])])
                    indexes.append(i)
                if not payload:
                    self.after(0, lambda: self.status_var.set('分析完成'))
                    return
                translated = translate_texts(payload, provider, api_base, api_key, model)
                pos = 0
                updates = []
                for i in indexes:
                    title_zh = translated[pos].strip(); pos += 1
                    s1 = translated[pos].strip(); pos += 1
                    s2 = translated[pos].strip(); pos += 1
                    updates.append((i, title_zh, [s1, s2]))
                def apply_updates() -> None:
                    for i, title_zh, summary_zh in updates:
                        candidates[i]['title_zh'] = title_zh
                        candidates[i]['summary_zh'] = summary_zh
                        if i < len(self.clip_rows):
                            # no dynamic relayout; update only existing vars when field exists
                            self.clip_rows[i].update_translation(title_zh, summary_zh)
                    # refresh rows if zh area absent
                    self.populate_candidates(candidates)
                    self.status_var.set('分析完成')
                self.after(0, apply_updates)
            except Exception as exc:
                self.log_queue.put(f'候选中文参考翻译失败: {exc}\n')
                self.after(0, lambda: self.status_var.set('分析完成'))
            finally:
                self.translating_candidates = False

        threading.Thread(target=worker, daemon=True).start()

    def populate_candidates(self, candidates: list[dict]) -> None:
        for child in self.cards_inner.winfo_children():
            child.destroy()
        self.clip_rows.clear()
        for idx, clip in enumerate(candidates, start=1):
            row = ClipRow(self, self.cards_inner, clip, idx)
            row.pack_into(idx - 1)
            self.clip_rows.append(row)

    def select_all(self) -> None:
        for row in self.clip_rows:
            row.selected_var.set(True)

    def deselect_all(self) -> None:
        for row in self.clip_rows:
            row.selected_var.set(False)

    def invert_select(self) -> None:
        for row in self.clip_rows:
            row.selected_var.set(not row.selected_var.get())

    def clear_preview_cache(self) -> None:
        if not self.current_base_dir:
            return
        preview = self.current_base_dir / 'preview'
        if preview.exists():
            for p in preview.iterdir():
                try:
                    if p.is_file():
                        p.unlink()
                except OSError:
                    pass
        messagebox.showinfo('提示', '预览缓存已清空。')

    def preview_row(self, row: ClipRow) -> None:
        if not self.source_video_path or not self.source_video_path.exists() or not self.current_base_dir:
            messagebox.showwarning('提示', '请先完成素材准备与分析。')
            return
        try:
            start = hms_to_seconds(row.start_var.get())
            end = hms_to_seconds(row.end_var.get())
        except ValueError as exc:
            messagebox.showwarning('提示', str(exc))
            return
        preview_dir = self.current_base_dir / 'preview'
        preview_dir.mkdir(parents=True, exist_ok=True)
        out = preview_dir / f"{row.clip.get('id','preview')}.mp4"
        cmd = [sys.executable, str(ROOT / 'scripts' / 'clip_video.py'), str(self.source_video_path), str(start), str(end), str(out)]
        self.status_var.set('生成预览中')
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        self.status_var.set('就绪')
        if rc != 0:
            messagebox.showwarning('提示', '预览生成失败，请查看日志。')
            return
        try:
            os.startfile(str(out))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showwarning('提示', f'打开预览失败：{exc}')

    def export_selected(self) -> None:
        if not self.analysis_json_path or not self.analysis_json_path.exists():
            messagebox.showwarning('提示', '请先完成 AI 分析。')
            return
        selected = [row for row in self.clip_rows if row.selected_var.get()]
        if not selected:
            messagebox.showwarning('提示', '请先勾选要生成的热点片段。')
            return
        try:
            edited = [row.to_dict() for row in self.clip_rows]
        except ValueError as exc:
            messagebox.showwarning('提示', str(exc))
            return
        edited_path = self.analysis_json_path.with_name('selected_clips.edited.json')
        edited_path.write_text(json.dumps(edited, ensure_ascii=False, indent=2), encoding='utf-8')
        export_ids = ','.join([row.clip.get('id') for row in selected])
        cmd = [sys.executable, str(ROOT / 'app.py'), '--mode', 'export', '--analysis-file', str(edited_path), '--translator', self.translator_var.get(), '--export-ids', export_ids]
        if (ROOT / 'bin').exists():
            cmd += ['--ffmpeg-location', str(ROOT / 'bin')]
        if self.burn_subtitles_var.get():
            cmd += ['--burn-subtitles']
        if self.api_key_var.get().strip():
            cmd += ['--api-key', self.api_key_var.get().strip()]
        if self.api_base_var.get().strip():
            cmd += ['--api-base', self.api_base_var.get().strip()]
        if self._effective_model().strip():
            cmd += ['--model', self._effective_model().strip()]
        self._run_command(cmd, self._after_export)

    def _after_export(self, code: int, text: str) -> None:
        self._set_busy(False)
        self.status_var.set('导出完成' if code == 0 else f'导出完成（部分失败）')
        self._parse_output_markers(text)
        self._set_stage('done' if code == 0 else 'error', '导出完成' if code == 0 else '导出结束，请查看日志中的失败项')
        if self.current_base_dir:
            clips_dir = self.current_base_dir / 'clips'
            self.output_path_var.set(str(clips_dir))
            self.set_output_display(self.output_path_var.get())
        if code == 0:
            messagebox.showinfo('完成', f'处理完成。\n\n输出目录：\n{self.output_path_var.get()}')
        else:
            self._show_error_popup(text, f'任务结束，请查看日志。\n\n输出目录：\n{self.output_path_var.get()}')

    def open_output_dir(self) -> None:
        path = self.output_path_var.get().strip()
        if not path:
            messagebox.showinfo('提示', '当前还没有可打开的输出目录。')
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showwarning('打开失败', str(exc))

    def clear_output_dir(self) -> None:
        self.output_path_var.set('')
        self.set_output_display('')


if __name__ == '__main__':
    App().mainloop()
