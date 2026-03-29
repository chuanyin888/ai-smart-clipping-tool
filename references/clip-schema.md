# Clip Schema

`selected_clips.json` should be an array of objects with this shape:

```json
[
  {
    "id": "clip-01",
    "start": "00:12:03,000",
    "end": "00:13:22,500",
    "start_seconds": 723.0,
    "end_seconds": 802.5,
    "duration_seconds": 79.5,
    "title": "一句能钩住人的工作标题",
    "summary": [
      "第一句说明这段在讲什么。",
      "第二句说明为什么值得切出来。"
    ],
    "reason": "为什么它适合做 shorts"
  }
]
```

Rules:

- `id` must be unique and stable.
- `summary` must contain exactly two sentences.
- Timestamps must describe a complete thought.
- Prefer `20` to `180` seconds per clip.
