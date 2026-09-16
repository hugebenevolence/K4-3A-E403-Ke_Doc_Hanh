# Eval — golden set & kết quả chạy

Theo `02-guide.md` §2.6 và §4.1 của đề bài, rubric R4 (15đ).

## `golden-set/`

≥20 case tự xây: ≥2 case/lớp trong 4 lớp chỗ khó (①nguồn sự thật ②mơ hồ ③ngoài phạm vi ④đặc thù domain) + 8-10 case thường + 2-4 case hiếm. ≥10 case lấy/phát triển từ transcript thật — dẫn mã đoạn `[Txx-NNN]`, **không dán nguyên văn dài** (luật bảo mật data pack).

Định dạng gợi ý mỗi case: `case_id | input (mô tả tình huống + mã đoạn nguồn) | lớp chỗ khó | kỳ vọng (đạt khi nào)`.

## `results/`

Một file/lượt chạy: `case | output thực tế | đạt theo định nghĩa chiều nào | ghi chú`. Chạy **trọn bộ** mỗi lượt, kể cả case fail — không lọc bớt.

Quality bar (chốt tại hạn chốt spec, xem `spec.md` §7) áp dụng từ lượt đó trở đi, không đổi ngược.
