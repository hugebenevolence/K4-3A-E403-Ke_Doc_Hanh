# Kịch bản một phiên thử (10 phút / người)

Theo `02-guide.md` §4.2. Mỗi phiên cần **hai người của nhóm**: một người **dẫn**
(đọc đúng các câu in nghiêng, ngoài ra im lặng) và một người **ghi** (ghi hành động
và chép nguyên văn lời người thử). Người thử tự cầm chuột, tự đeo tai nghe.

---

## Trước khi mời người thử

- [ ] Chrome, cửa sổ lớn, đã mở link deploy (hỏi Nhân link mới nhất).
- [ ] Tai nghe có micro. Không có tai nghe thì micro thu lại giọng học trò AI.
- [ ] Một **tài khoản riêng, chưa ai dùng** cho người này (hỏi Nhân tài khoản và
  mật khẩu; `member5` dành cho video demo, không dùng). Tài khoản phải **trống**:
  thư viện không có trang nào "đã hiểu". Không trống thì báo Nhân.
- [ ] Ghi **giờ bắt đầu** (vd `2026-09-19T09:40`) — dùng để lọc số liệu sau phiên.
- [ ] Mở sẵn một dòng mới trong [nhat-ky.md](nhat-ky.md).

Không đăng nhập hộ, không mở sẵn slide, không chọn sẵn vùng: thấy người thử tự
tìm đường là một nửa giá trị của phiên.

---

## 1. Làm quen (~1')

*"Tụi mình đang đánh giá sản phẩm, không đánh giá bạn. Không có câu trả lời đúng
hay sai. Trong lúc dùng, bạn cứ nói to điều mình đang nghĩ nhé."*

## 2. Bối cảnh (~1') — hỏi TRƯỚC khi mở sản phẩm

*"Kể lần gần nhất bạn ôn lại một slide của khoá sau buổi học. Bạn đã làm gì? Làm
sao bạn biết là mình đã hiểu?"*

Người ghi chép nguyên văn. Câu trả lời này là mốc so sánh: họ đang tự kiểm bằng
cách nào (đọc lại, hỏi tutor, làm bài tập, không kiểm).

## 3. Giao việc (~1') — giao KẾT QUẢ, không chỉ nút

**Việc chính:**
*"Hãy dùng cái này để tự kiểm xem bạn hiểu slide Token — Day 1, trang 13 — tới
đâu. Xong khi nào bạn thấy đủ."*

**Việc khó hơn** (còn giờ, hoặc nếu người thử chỉ toàn khen):
*"Theo bạn, Context ở Day 1 liên quan gì tới hệ thống AI ở Day 2? Hãy dùng sản
phẩm để chứng minh điều đó với học trò."*
Việc này buộc họ giảng được hai trang rồi tự tìm ra cách nối trên bản đồ.

Sau câu giao việc: **không nói thêm gì nữa**.

## 4. Quan sát (~5') — im lặng

Người ghi đánh dấu giờ (phút:giây) cạnh từng điểm dưới đây khi nó xảy ra:

| Khoảnh khắc | Ghi gì |
|---|---|
| Hành động đầu tiên | Bấm vào đâu trước. Tìm ra slide Token bằng cách nào |
| Chọn vùng trên slide | Có hiểu phải kéo khung không, hay bấm "Bắt đầu" ngay |
| Nói vào micro | Có hiểu giữ Space để nói không, hay gõ chữ, hay chờ |
| Sau câu hỏi ngược đầu tiên | Trả lời tiếp · hỏi xin đáp án · muốn xem lại slide đang bị che · bỏ ngang |
| Khi bị chấm chưa đủ / sai | Phản ứng bằng lời (chép nguyên văn), có giảng lại không |
| Khi học trò nói "đã hiểu" | Có tin không, có nhìn vào căn cứ chấm không |
| Bản đồ | Có tự mở tab Bản đồ không; bấm hay kéo thứ gì trên đó |
| Do dự | Mọi chỗ ngồi im quá 5 giây: đang nhìn vào đâu |

**Chỉ được dùng 3 câu cứu hộ trung tính** khi người thử kẹt:

- *"Cứ nói to suy nghĩ nhé."*
- *"Bạn sẽ làm gì tiếp?"*
- *"Bạn nghĩ nó nên hoạt động thế nào?"*

Mỗi lần dùng câu cứu hộ, ghi lại **ở bước nào** — đó là chỗ sản phẩm chưa tự nói
được. **Cấm:** giải thích màn hình, chỉ nút, nhắc phím Space, hỏi "bạn có thích không?".

## 5. Hỏi sau khi dùng (~2') — chép nguyên văn

1. *"Điều gì khó hiểu hoặc khó chịu nhất?"*
2. *"Kết quả học trò chấm bạn, bạn có tin không? Vì sao?"*
3. *"Bạn có dùng thật không, trước một buổi kiểm tra chẳng hạn? Vì sao, hoặc vì sao chưa?"*
4. *"Nếu từ mai không được dùng cái này nữa, bạn thấy: rất tiếc, hơi tiếc, hay không sao?"*

Chép nguyên văn, kể cả nói lấp lửng hay sai chính tả. Không tóm tắt hộ.

---

## Sau phiên (người ghi, ~5')

1. Lấy số liệu hành vi của phiên từ server (Nhân chạy trên máy deploy):

   ```bash
   cd codebase/backend
   .venv/Scripts/python scripts/validation_report.py member1 --since 2026-09-19T09:40
   ```

   Ra một bảng: mỗi phiên giảng trang nào, bao nhiêu lượt, nhãn chấm qua từng lượt
   (vd `incorrect → incomplete → sufficient`), có dạy được không, và học trò chờ bao
   lâu mới lên tiếng. Dán vào mục "Số liệu hành vi" của [nhat-ky.md](nhat-ky.md).
   Thêm `--texts` để xem lại người thử đã giảng câu gì ở từng lượt.

2. Điền một dòng vào bảng nhật ký: quan sát, quote, mức nghiêm trọng.

## Đọc một hành động theo hai nghĩa (PAIR 5.1)

Ghi **cả hành động lẫn ngữ cảnh**. Cùng một hành động có thể mang hai nghĩa ngược nhau:

| Hành động | Có thể là | Hoặc là | Phân biệt bằng |
|---|---|---|---|
| Hỏi xin đáp án | Đang thử xem học trò có lộ đáp án không | Kẹt thật, câu hỏi ngược không giúp được | Lời nói ngay trước đó |
| Giảng lại nhiều lượt | Đang đào sâu, muốn được "đã hiểu" | Bực vì câu hỏi ngược lặp hoặc mơ hồ | Giọng, câu cảm thán, lượt sau dài hơn hay ngắn đi |
| Bấm "Bỏ qua" lời học trò | Đã quen, muốn nhanh | Học trò nói dài, nói chậm | Bỏ qua từ lượt đầu hay chỉ lượt sau |
| Không mở bản đồ | Không cần tới | Không thấy có tab | Câu hỏi 1 sau phiên |
| Bỏ ngang giữa phiên | — | Gần như luôn tiêu cực | Bước nào, sau câu gì của học trò |

Thang bằng chứng, mạnh xuống yếu: **hành vi quan sát được** → lời nói trong lúc
dùng → giải thích khi được hỏi → dự đoán "mình sẽ dùng". Một hành động thật nặng
hơn mười câu "chắc mình sẽ dùng".
