# knowledge/ — nguồn grounding (KHÔNG commit nội dung)

Thư mục này đã nằm trong `.gitignore`. Data pack của BTC thuộc quy định bảo mật:
không chia sẻ ra ngoài khoá, **không commit vào repo nộp bài**. Repo chỉ chứa
loader (`app/adapters/knowledge/local.py`) và file README này.

## Nạp bài thật

Tạo `knowledge/lesson.json` từ `brief/data/vlearn-pack/`:

```json
{
  "concept": "vì sao LLM hay bịa (hallucination)",
  "spans": [
    { "span_id": "[T06-138]", "text": "<nội dung đoạn>" },
    { "span_id": "[T06-139]", "text": "<nội dung đoạn>" }
  ]
}
```

Rồi đặt `USE_MOCKS=false` trong `.env`.

Case cho lát cắt: **"vì sao LLM bịa"** — đoạn `[T06-138]`–`[T06-139]` trong
`transcript-06-clean.md`, mục "Vì sao có hallucination — bias dữ liệu và quá
trình huấn luyện".

Giai đoạn PDF sẽ thêm `page` và `bbox` vào mỗi span để highlight lại đúng vùng
trên slide — loader đã đọc sẵn hai trường đó.

## Bài demo

Khi `USE_MOCKS=true` (mặc định), app nạp `codebase/backend/fixtures/demo_lesson.json`
— một bài **tự bịa** về nước sôi/áp suất, commit được vì không dính data pack.
Cùng định dạng với bài thật, nên đường chạy demo và đường chạy thật là một.

## Nhắc

Khi viết `eval/` hay `spec.md`, chỉ trích **mã đoạn** (`[Txx-NNN]`), không dán
nguyên văn dài — xem `brief/README-goc-btc.md` mục "Bảo mật dữ liệu".
