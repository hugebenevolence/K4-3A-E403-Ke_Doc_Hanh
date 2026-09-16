# Codebase — Kẻ Độc Hành · Track D3

Prototype cho lát cắt: một học viên dạy lại một khái niệm bằng giọng nói cho AI đóng vai "học trò" · AI hỏi ngược đúng chỗ giải thích hổng/mơ hồ/sai (đối chiếu với nguồn) · chỉ "hiểu" và kết thúc phiên khi lời giải thích đủ đúng.

## Chạy

```bash
cd codebase/backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cp .env.example .env          # USE_MOCKS=true nên chạy được ngay, không cần key
.venv/Scripts/python -m pytest tests/ -q
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# frontend — cần serve chứ không mở file trực tiếp (getUserMedia đòi localhost)
python -m http.server 5500 --directory codebase/frontend
```

## Cấu trúc (ports & adapters)

```
backend/app/
├── domain/      ← logic thuần, không import SDK nào: máy trạng thái lượt,
│                  verdict, phát hiện đọc-lại-nguyên-văn, log/hồ sơ học viên
├── ports/       ← interface: LLMClient, SpeechToText, TextToSpeech, SpanStore, store
├── adapters/    ← triển khai thật cho từng provider (hiện có mock cho cả bốn)
├── graph/       ← LangGraph: node quyết định + conditional edge
├── prompts/     ← .md đánh version + registry ghép prompt đúng thứ tự cache
├── api/         ← điều phối talker ‖ reasoner, cắt câu cho TTS
└── main.py      ← composition root: chỗ DUY NHẤT biết provider nào đang chạy
```

Đổi provider = viết một file trong `adapters/` rồi wire ở `main.py`. Không sửa
call site ở chỗ khác — đó là lý do có tầng `ports/`.

## Ba quyết định kiến trúc, và vì sao

**1. Workflow tất định, không phải vòng lặp ReAct.** Luồng dạy-lại có cấu trúc
ổn định (chấm → rẽ nhánh → hỏi ngược hoặc kết), nên graph cố định vừa rẻ vừa
đoán trước được. Thêm tool sau này là thêm node, không thả cho model tự lặp.

**2. Talker chạy song song Reasoner, và nằm NGOÀI graph.** `api/session.py` bắn
hai task cùng lúc: talker (model rẻ nhất) nói một câu nhắc lại lời học viên
trong ~400ms, reasoner (model chấm) trả kết quả sau 1–2s. Chạy tuần tự thì học
viên ngồi im sau mỗi lượt. Talker **bị cấm tuyệt đối** chốt đúng/sai — lúc nó
nói thì chưa ai biết kết quả; luật này nằm trong `prompts/talker/v1.md`.

**3. Grounding tất định trước khi hỏi LLM.** `domain/verbatim.py` bắt việc đọc
lại nguyên văn nguồn bằng so khớp chuỗi, không hỏi model — rẻ hơn, không dao
động giữa các lượt chạy, và vẫn chấm được khi LLM lỗi.

## Phân tầng model theo chi phí

Ngân sách cả dự án: **$5 credit**. Call site chọn `ModelTier`, không chọn tên
model, nên đổi model là đổi `.env`.

| Tier | Model | Dùng ở đâu | Ước tính |
|---|---|---|---|
| `FAST` | gpt-5-nano | Talker — câu đệm lúc chờ | ~$0.00002/lượt |
| `STANDARD` | gpt-5-mini | Chấm + sinh câu hỏi ngược | ~$0.001/lượt gọi |
| `JUDGE` | gpt-5 | Chấm rubric offline khi ghi `eval/results/` | ~$0.01/transcript |

Một phiên hoàn chỉnh ~$0.008. Một lượt chạy golden set 20 case ~$0.26 (~$0.13
nếu qua Batch API). Cả hackathon ước ~$2.5–3.0.

**Ràng buộc cache (bắt buộc)**: prompt caching của OpenAI chỉ ăn theo *prefix*
chung (≥1024 token, giữ 24h, giảm 90%). Nên phần cố định (hướng dẫn + đoạn
nguồn) đi vào `system`, phần biến thiên (lời học viên) đi vào `user`. Đảo thứ
tự là mất sạch giảm giá — xem `prompts/registry.py`.

## Kiến trúc prompt

```
prompts/
├── _base/
│   ├── guardrails_v1.md   ← sàn an toàn: lời học viên là DỮ LIỆU không phải
│   │                        chỉ thị (chống injection), luật ngôn ngữ, chỉ bám nguồn
│   └── persona_v1.md      ← vai học trò, xưng hô, 6 kiểu ép lộ đáp án + cách đáp
├── grader/v1.md           ← guardrails
├── talker/v1.md           ← guardrails + persona
└── student_persona/v1.md  ← guardrails + persona
```

`registry.compose_system()` ghép theo **mức ổn định giảm dần**: `_base` (giống
nhau mọi prompt) → prompt riêng → đoạn nguồn (đổi theo khái niệm). Phần dùng
chung đứng trước để prefix cache dùng lại được nhiều nhất.

Sàn an toàn định nghĩa **một lần** trong `_base/` rồi ghép vào, thay vì chép ở
từng file — chép lại là kiểu gì cũng trôi lệch khi sửa. `grader` cố ý KHÔNG
kèm lớp persona: nó không nói với ai, nhét persona vào chỉ làm loãng hướng dẫn chấm.

Mỗi prompt theo cùng bộ mục: **VIỆC PHẢI LÀM · LUẬT RIÊNG · ĐẦU RA · NEO ·
CASE RÌA**. Mục NEO là ví dụ phân định các mức verdict — nghiên cứu LLM-judge
cho thấy neo nâng mức khớp với người chấm từ ~0.4 lên ~0.78 kappa.

Prompt sau khi ghép đều trên 1024 token nên caching kích hoạt; prompt dài thêm
gần như không tốn thêm tiền vì phần cố định được tính 10% giá.

## Mock vs thật

| Phần | Trạng thái | Kế hoạch |
|---|---|---|
| STT | mock | Speechmatics (realtime, partial <500ms, có tiếng Việt, $100 credit) |
| TTS | mock | FPT.AI (giọng Việt bản địa, có accent vùng miền) |
| LLM chấm | mock | OpenAI theo bảng tier ở trên |
| Nguồn grounding | span demo rỗng | `knowledge/spans.json` — xem `knowledge/README.md` |

## Giao thức WebSocket `/ws/session`

Client → server: binary frame = audio chunk · `{"type":"explanation_done"}` = chốt lượt.

Server → client: `{"type":"state","state":...}` · `{"type":"transcript","role":...,"text":...,"filler":bool}` · binary frame = audio TTS · `{"type":"session_end","outcome":...,"source_span":...}`.

Client chỉ mở mic khi state cho phép **và** audio agent đã phát xong — thiếu vế
sau thì mic bắt lại chính giọng agent qua loa.
