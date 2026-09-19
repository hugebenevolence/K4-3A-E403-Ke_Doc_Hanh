# Codebase — Kẻ Độc Hành · Track D3

Prototype cho lát cắt: một học viên dạy lại một khái niệm bằng giọng nói cho AI đóng vai "học trò" · AI hỏi ngược đúng chỗ giải thích hổng/mơ hồ/sai (đối chiếu với nguồn) · chỉ "hiểu" và kết thúc phiên khi lời giải thích đủ đúng.

## Chạy

```bash
cd codebase/backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cp .env.example .env          # USE_MOCKS=true nên chạy được ngay, không cần key
.venv/Scripts/python -m pytest tests/ -q
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# frontend — React + Vite, cần serve chứ không mở file (getUserMedia đòi localhost)
cd codebase/frontend-react && npm install && npm run dev   # :5500, /api chuyển sang :8000
```

Các trang: `/` giới thiệu · `/login` · `/library` chọn bộ slide và trang · `/learn/:deck?page=N` không gian học.

## Deploy cho thành viên thử

Backend phục vụ luôn giao diện đã build (`frontend-react/dist`): một service, một
địa chỉ. Mic chỉ chạy trên HTTPS (hoặc localhost), nên link gửi cho thành viên
phải là HTTPS.

**Cách nhanh nhất — chạy trên máy mình, mở tunnel.** Slide của khoá ở nguyên
trên máy, không upload lên đâu; thành viên phải đăng nhập mới xem được.

```bash
cd codebase/frontend-react && npm install && npm run build

# thêm vào codebase/backend/.env
#   USE_MOCKS=false
#   SLIDES_DIR=D:/.../brief/data/vlearn-pack/slides
#   MEMBERS=an:matkhau-an,binh:matkhau-binh
#   AUTH_SECRET=...   (lệnh tạo có trong .env.example)

cd ../backend
env -u OPENAI_API_KEY .venv/Scripts/uvicorn app.main:app --port 8000   # bỏ key hệ thống, dùng key trong .env
cloudflared tunnel --url http://localhost:8000                          # terminal khác; in ra link https://…trycloudflare.com
```

Cần biết trước khi gửi link:

- Máy phải bật suốt lúc mọi người thử; tắt terminal là link chết, mở lại tunnel là ra link mới.
- Mỗi phiên tiêu credit thật (LLM + đọc thành tiếng). Không đặt `MEMBERS` thì ai có link cũng dùng được.
- Speechmatics giới hạn số phiên nhận dạng giọng nói **đồng thời** — nhiều người cùng nói một lúc sẽ gặp lỗi "Concurrent Quota Exceeded". Hẹn nhau thử lệch giờ, hoặc bật chế độ im lặng và gõ chữ.
- Tên hiển thị của từng bộ slide: `knowledge/decks.json` (gitignore), dạng `{"d1-slide-hackathon": {"title": "...", "subtitle": "..."}}`.

**Railway — chạy liên tục, không cần máy ai bật.** Railway build từ THƯ MỤC được
đẩy lên chứ không phải từ repo, nên slide và mô tả hình đi kèm gói mà không phải
commit chúng vào git. Máy không cần cài Docker: Railway tự build.

```bash
python codebase/scripts/dung_goi_deploy.py      # dựng deploy/ (~179 MB: code + knowledge + 28 bộ slide)
cd deploy
npx @railway/cli login
npx @railway/cli init
npx @railway/cli up
```

Gói CHỈ mang slide, không mang chatlog hay các pack khác trong `brief/data`, và
loại `.env` ra — khoá API đặt bằng biến môi trường trên Railway:

| Biến | Giá trị |
|---|---|
| `OPENAI_API_KEY`, `SPEECHMATICS_API_KEY` | khoá thật |
| `MEMBERS` | `an:matkhau-an,binh:matkhau-binh` |
| `AUTH_SECRET` | chuỗi ngẫu nhiên (lệnh tạo có trong `.env.example`) |
| `USE_MOCKS`, `SLIDES_DIR` | đã đặt sẵn trong image, không cần khai lại |

**Gắn volume vào `/app/codebase/backend/var`.** Tiến độ, bản đồ tri thức, hồ sơ
học viên và log phiên nằm ở đó; không gắn thì mỗi lần deploy lại là mọi người
mất sạch những gì đã giảng được.

Vẫn phải đăng nhập mới xem được slide, nên đặt `MEMBERS` trước khi gửi link.

**Docker — máy chủ của nhóm.** Image không chứa slide; mount lúc chạy, và đừng
push image kèm dữ liệu lên registry công khai.

```bash
docker build -t giang-lai codebase
docker run -p 8000:8000 --env-file codebase/backend/.env \
  -e SLIDES_DIR=/data/slides \
  -v "$PWD/brief/data/vlearn-pack/slides:/data/slides:ro" \
  -v "$PWD/knowledge:/app/knowledge:ro" \
  giang-lai
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

`USE_MOCKS=true` (mặc định) chạy được cả luồng mà không tốn credit — hữu ích
khi sửa giao diện hoặc chạy test. Đặt `false` rồi điền key thì dùng bản thật.

| Phần | Bản thật | Ghi chú |
|---|---|---|
| STT | Speechmatics realtime | WS, PCM16 16kHz, có partial nên chữ hiện lúc đang nói |
| TTS | OpenAI `gpt-4o-mini-tts` | FPT.AI bị loại: trả URL bất đồng bộ, chờ 5s–2 phút |
| LLM | OpenAI theo bảng tier trên | `service_tier=priority` cho nhanh |
| Nguồn | PDF slide, hoặc đoạn code | `adapters/knowledge/pdf.py` tách span kèm trang + bbox |

## Giao thức WebSocket `/api/ws/session`

Query: `deck` (mã bộ slide) · `spans` (mã các ô đã chọn, cách nhau dấu phẩy) ·
`token` khi server bật đăng nhập — trình duyệt không gắn được header vào
WebSocket. Token sai hoặc hết hạn: server gửi `{"type":"error"}` rồi đóng với mã `4401`.

Client → server: binary frame = audio chunk · `{"type":"explanation_done"}` = chốt lượt.

Server → client: `{"type":"state","state":...}` · `{"type":"transcript","role":...,"text":...,"filler":bool}` · binary frame = audio TTS · `{"type":"session_end","outcome":...,"source_span":...}`.

Client chỉ mở mic khi state cho phép **và** audio agent đã phát xong — thiếu vế
sau thì mic bắt lại chính giọng agent qua loa.
