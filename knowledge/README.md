# knowledge/ — nguồn grounding (KHÔNG commit nội dung)

Thư mục này đã nằm trong `.gitignore`. Data pack của BTC thuộc quy định bảo mật:
không chia sẻ ra ngoài khoá, **không commit vào repo nộp bài**. Repo chỉ chứa
loader (`app/adapters/knowledge/local.py`) và file README này.

## Nạp về máy

Tạo `knowledge/spans.json` từ `brief/data/vlearn-pack/`, dạng:

```json
[
  { "span_id": "[T06-138]", "text": "<nội dung đoạn>" },
  { "span_id": "[T06-139]", "text": "<nội dung đoạn>" }
]
```

Case đang dùng cho lát cắt: **"vì sao LLM bịa"** — đoạn `[T06-138]`–`[T06-139]`
trong `transcript-06-clean.md` (mục "Vì sao có hallucination — bias dữ liệu và
quá trình huấn luyện").

Giai đoạn PDF sẽ thêm `page` và `bbox` vào mỗi span để highlight lại đúng vùng
trên slide.

## Nhắc

Khi viết `eval/` hay `spec.md`, chỉ trích **mã đoạn** (`[Txx-NNN]`), không dán
nguyên văn dài — xem `brief/README-goc-btc.md` mục "Bảo mật dữ liệu".
