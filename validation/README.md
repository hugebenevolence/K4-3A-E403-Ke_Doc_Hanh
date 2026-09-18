# Validation — người ngoài dùng thử (R6, bonus +8đ)

Theo `02-guide.md` §4.2. Không bắt buộc, nhưng thiếu mục này thì trần điểm là 92.

| File | Dùng để |
|---|---|
| [kich-ban-phien-thu.md](kich-ban-phien-thu.md) | Kịch bản một phiên 10 phút: câu dẫn nguyên văn, việc giao, những gì cần quan sát, câu hỏi sau phiên |
| [nhat-ky.md](nhat-ky.md) | Bảng nhật ký (mỗi người thử một dòng), 4 dòng tổng hợp, số liệu hành vi |
| `codebase/backend/scripts/validation_report.py` | Lấy hành vi của từng người thử từ log server: phiên, lượt, nhãn chấm, thời gian chờ |

## Cần đủ 4 thứ

- [ ] **≥5 người ngoài nhóm** dùng thử, trong đó **≥2 người đã khai willing user từ CP1**
  (`spec.md` §8). Nhân và Bình là thành viên nhóm, không tính.
- [ ] **Quote nguyên văn**: chép đúng lời, kể cả sai chính tả.
- [ ] **Bảng nhật ký**: `người thử (tên/vai) | task giao | quan sát | quote | mức nghiêm trọng | quyết định`.
- [ ] **≥1 thay đổi** ghi vào `spec.md` §9 Changelog, hoặc giữ nguyên kèm lý do.

Cuối bảng: chủ đề lặp nhiều nhất · sẽ sửa gì trước demo · giữ nguyên gì và vì sao · để dành sau.

Giao task theo **outcome** ("hãy dùng cái này để tự kiểm xem bạn hiểu slide Token
tới đâu"), không chỉ nút bấm. Quan sát im lặng; đừng hỏi "sản phẩm này hay không".
Nếu mọi phản hồi đều là lời khen, phiên chưa đạt: giao việc khó hơn hoặc đổi người thử.
