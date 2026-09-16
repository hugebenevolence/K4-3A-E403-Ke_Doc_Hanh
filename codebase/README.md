# Codebase — Kẻ Độc Hành · Track D1

Prototype cho lát cắt: một học viên ôn khái niệm bằng giọng nói · AI đóng vai bạn học nêu một cách hiểu sai · học viên ngắt lời để sửa · AI đối chiếu với nguồn transcript và xác nhận trước khi kết thúc phiên.

## Cấu trúc

```
codebase/
├── backend/        ← FastAPI, orchestrate STT → LLM → TTS + turn-arbitration
│   └── app/
│       ├── main.py         # entrypoint + WebSocket /ws/session
│       ├── voice/          # STT/TTS adapter — đổi provider ở đây
│       ├── agents/         # persona "bạn học", prompt + logic chọn misconception
│       └── prompts/        # prompt templates, tách khỏi code
└── frontend/       ← thuần HTML/CSS/JS, không cần build step
    ├── index.html
    ├── css/style.css
    └── js/app.js   # mic capture + WebSocket client
```

## Mock vs thật (cập nhật liên tục — bắt buộc theo rubric R5)

| Phần | Trạng thái | Ghi chú |
|---|---|---|
| STT | _(điền: mock / thật, provider nào)_ | |
| TTS | _(điền)_ | |
| LLM quyết định trung tâm | _(điền)_ | ≥1 lời gọi AI thật là bắt buộc |
| Đối chiếu nguồn transcript | _(điền)_ | |

## Vì sao chọn stack này

- **Backend Python**: hầu hết SDK STT/TTS (PhoWhisper, ElevenLabs, Deepgram, FPT.AI) đều có binding Python tốt nhất; FastAPI + WebSocket hợp để stream audio hai chiều với latency thấp.
- **Frontend không build step**: mở `index.html` chạy ngay, không tốn thời gian hackathon setup Node/Vite. Đổi sang framework khác nếu nhóm quen hơn — không bắt buộc giữ nguyên.

Đây là điểm khởi đầu, không phải quyết định cuối — đổi nếu cả nhóm thấy hợp hơn.
