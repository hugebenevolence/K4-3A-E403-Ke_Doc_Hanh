# Kịch bản quay video demo (khoảng 3 phút 30)

Video dự phòng cho phần demo ở slide 3, gồm một trường hợp chuẩn và một trường hợp
khó (`brief/02-guide.md` §5.1).

**Quy ước.** Mỗi bước gồm ba phần:

- **NÓI**: lời thuyết minh cho người xem, nói khi **không** giữ phím Space.
- **LÀM**: thao tác trên màn hình.
- **THẤY**: kết quả cần xuất hiện. Nếu không thấy, tra bảng sự cố ở cuối.

**Câu giảng cho học trò** (trong khung trích) là câu nói vào micro: giữ Space,
nói, rồi thả Space. Khi đang giữ Space, micro đang thu, vì vậy chỉ nói đúng câu đó.
Các câu này đã được kiểm với bộ chấm thật; hãy giữ nguyên từng chữ.

---

## Chuẩn bị

- Trình duyệt Chrome, cửa sổ khoảng 1440×900, thu phóng 100%, tắt thông báo. Chỉ
  quay cửa sổ trình duyệt.
- Đeo tai nghe để micro không thu lại giọng của học trò AI.
- Đăng nhập tài khoản **member5** (mật khẩu hỏi Nhân) và cho phép dùng micro.
- Mở tab **Bản đồ** một lần, bấm **Đã rõ** để tắt khung "Cách dùng bản đồ" (khung
  này chỉ hiện ở lần mở đầu), rồi quay lại.
- Mở trang **Thư viện**. Khung "Hành trình học của bạn" phải hiển thị
  **3 Đã hiểu · 1 Cần sửa**; nếu không, báo Nhân dựng lại dữ liệu.

---

## Bước 1. Giới thiệu hệ thống (0:00–0:35)

**LÀM:** giữ màn hình ở trang Thư viện.

**NÓI:**
> Trên VLearn, học viên khoá AI20k đã hơn 5.600 lần nhờ tutor giảng bài, nhưng
> tutor chỉ đặt câu hỏi ngược ở 0,2% số lượt. Ngay cả khi học viên tự trình bày cách
> hiểu, gần 87% trường hợp tutor vẫn giảng lại thay họ. Người học vì thế khó biết
> mình thực sự hiểu đến đâu.
>
> V_KDH đảo ngược vai trò này, dựa trên hiệu ứng học qua giảng dạy. Người học
> chọn một phần slide; phần đó được che đi, và họ trình bày lại bằng lời của mình
> cho một học trò AI. Học trò đối chiếu lời giảng với đúng nội dung slide, rồi đặt
> một câu hỏi vào chỗ còn thiếu, không bao giờ đưa ra đáp án.

---

## Bước 2. Hành trình học (0:35–0:50)

**LÀM:** rê chuột qua khung "Hành trình học của bạn", dừng ở dòng *"Có 1 trang bạn
từng giảng sai"*.

**NÓI:**
> Hệ thống lưu mức hiểu của từng trang theo tài khoản. Mức hiểu chỉ tăng khi người
> học giảng được, không tăng khi chỉ mở slide ra đọc. Tài khoản này đã giảng trước
> một số trang, trong đó có một trang từng giảng sai.

---

## Bước 3. Chọn phần cần giảng (0:50–1:05)

**LÀM:**
1. Ở cột trái, chọn bộ **Day 1 · AI & LLM Foundation**.
2. Chọn **Slide 12: Sinh văn bản = đoán → nối vào câu → đoán tiếp**.
3. Kéo một khung quanh phần nội dung chính của slide.
4. Bấm **Bắt đầu giảng**.

**THẤY:** vùng vừa chọn bị che; học trò đọc câu mở đầu.

**NÓI** (sau khi học trò nói xong):
> Phần vừa chọn đã được che. Từ đây, tôi phải trình bày bằng hiểu biết của mình,
> không thể đọc lại.

---

## Bước 4. Trường hợp chuẩn (1:05–1:35)

**LÀM:** giữ Space, nói câu dưới đây, rồi thả Space.

> **Giảng cho học trò:** "Model sinh văn bản bằng cách đoán một token tiếp theo dựa
> trên xác suất. Sau đó nó nối token vừa đoán vào ngữ cảnh rồi chạy lại từ đầu để
> đoán token kế tiếp. Vì vậy câu trả lời được tạo ra từng mảnh một chứ không phải
> nghĩ ra cả câu một lúc."

**THẤY:** thẻ **"Học trò đã hiểu phần này"**; ở dàn ý bên trái, slide 12 chuyển
sang chấm đặc.

**NÓI:**
> Lời giảng được đối chiếu với đúng slide này. Vì đã nêu đủ cơ chế, học trò xác nhận
> đã hiểu và trang được ghi nhận.

*Dự phòng — nếu học trò hỏi thêm, giữ Space và trả lời:*
> "Nó cứ lặp lại như vậy cho tới khi đủ câu, mỗi vòng chỉ thêm đúng một mẩu."

---

## Bước 5. Trường hợp khó: một hiểu lầm (1:35–2:05)

**LÀM:**
1. Ở dàn ý bên trái, chọn **13 · Token** (vòng rỗng, nghĩa là cần sửa).
2. Bấm **Bắt đầu giảng** và đợi học trò mở đầu xong.
3. Giữ Space, nói câu dưới đây, rồi thả Space.

> **Giảng cho học trò:** "Mỗi token là một từ, và tiếng Việt tốn ít token hơn tiếng
> Anh vì từ tiếng Việt ngắn."

**THẤY:** học trò không xác nhận và không sửa hộ; nó đặt một câu hỏi ngược, chẳng
hạn *"token thực tế là mảnh chữ hay ký tự như bạn nói, hay đúng là mỗi token một từ
vậy?"*

**NÓI:**
> Đây là một hiểu lầm có thật, trích từ chatlog của khoá. Học trò không xác nhận ý
> sai và cũng không sửa hộ; nó đặt đúng một câu hỏi vào chỗ sai để người học tự nhận
> ra.

---

## Bước 6. Tự điều chỉnh (2:05–2:35)

**LÀM:** giữ Space, nói câu dưới đây, rồi thả Space.

> **Giảng cho học trò:** "À mình nói sai. Model không đọc theo từng từ mà theo từng
> mẩu chữ nhỏ, một chữ dài hay có dấu có thể bị chặt ra thành ba bốn mẩu. Vì thế cùng
> một câu mà viết tiếng Việt có dấu thì ra nhiều mẩu hơn tiếng Anh, tức là tốn tiền
> hơn và dùng hết chỗ nhanh hơn."

**THẤY:** thẻ **"Học trò đã hiểu phần này"**; slide 13 chuyển từ vòng rỗng sang
chấm đặc.

**NÓI:**
> Sau khi người học tự điều chỉnh, trang từng bị ghi là cần sửa chuyển sang đã hiểu.

*Dự phòng — nếu học trò hỏi thêm, giữ Space và trả lời:*
> "Ví dụ 'Xin chào' có thể thành ba bốn mẩu, còn 'Hello' chỉ một mẩu."

---

## Bước 7. Bản đồ hiểu biết (2:35–2:50)

**LÀM:** bấm tab **Bản đồ** ở góc trên bên trái.

**THẤY:** bản đồ toàn màn hình, Day 1 bên trái, Day 2 bên phải; các trang đã hiểu
là chấm đen; trang Token có nhãn đen **"Bạn đang ở đây"**.

**NÓI:**
> Bản đồ hiểu biết tập hợp các trang đã giảng được qua mọi buổi học, xếp theo từng
> buổi. Mỗi điểm lưu nguyên văn lời người học, không phải lời AI diễn đạt lại.

**LÀM:** bấm vào đỉnh **Context** (D1 · tr. 14); khung bên phải hiển thị câu đã giảng.
Bấm **Đóng** trên khung đó.

---

## Bước 8. Nối hai buổi học (2:50–3:20)

**LÀM:**
1. Kéo đỉnh **Context** (D1 · tr. 14), thả lên đỉnh **Hệ thống AI** (D2 · tr. 16).
   Khi thả trúng, vòng nét đứt quanh Hệ thống AI đậm lên.
2. Trên thanh đen phía trên, bấm **Giảng mối nối**.

**THẤY:** học trò hỏi một câu dựng từ chính lời bạn đã giảng ở hai trang — câu chữ
mỗi lần một khác, đại ý như *"Bạn nói Context là lượng chữ model thấy trong một lần,
còn trang Hệ thống AI gọi Context là tri thức riêng của doanh nghiệp — hai Context đó
khác nhau ở chỗ nào vậy bạn?"*

**LÀM:** giữ Space, nói câu dưới đây, rồi thả Space.

> **Giảng cho học trò:** "Ở Day 1, context là lượng chữ model nhìn được trong mỗi
> lần trả lời. Sang Day 2 thì context là một thành phần của hệ thống AI: mình đưa tài
> liệu nghiệp vụ vào context để model trả lời đúng với doanh nghiệp. Nhưng vì context
> có giới hạn và càng dài càng tốn tiền, nên không thể nhồi hết tài liệu mà phải chọn
> đúng phần liên quan."

**THẤY:** thông báo **"Học trò đã thấy chỗ nối"**. Bấm **Xong**; một đường nối được
vẽ giữa trang Day 1 và trang Day 2, khung bên phải hiển thị đúng câu vừa nói.

**NÓI:**
> Hai trang thuộc hai buổi học khác nhau vừa được nối lại bằng chính lời giải thích
> của người học. Hệ thống không tự suy ra liên kết; một liên kết sai sẽ không được
> ghi nhận.

---

## Bước 9. Kết (3:20–3:35)

**LÀM:** bấm **Thư viện** ở góc trên bên phải.

**THẤY:** khung "Hành trình học" hiển thị **5 Đã hiểu · 0 Cần sửa**.

**NÓI:**
> Chỉ trong vài phút, hai trang mới được hiểu, một hiểu lầm được sửa và một liên kết
> giữa hai buổi học được thiết lập. Tất cả đều do người học tự trình bày; AI chỉ đặt
> câu hỏi.

---

## Xử lý sự cố

| Tình huống | Cách xử lý |
|---|---|
| Micro không nhận hoặc nhận sai | Gõ đúng câu giảng vào ô nhập phía dưới rồi bấm **Gửi**; luồng xử lý vẫn là thật |
| Học trò hỏi thêm ngoài dự kiến | Dùng câu dự phòng ghi ở bước tương ứng |
| Bước 8 kéo thả không trúng | Bấm đỉnh **Context** → **Nối với trang khác** → bấm đỉnh **Hệ thống AI** |
| Bước 8 bị chấm "chưa thấy chỗ nối" | Bấm **Thử nối lại** và giảng: *"Vì context có hạn nên không nhồi hết tài liệu nghiệp vụ vào được, phải chọn đúng phần liên quan — đó là chỗ hai trang gặp nhau."* |
| Muốn bỏ qua lời học trò đang đọc | Bấm **Bỏ qua** hoặc nhấn Space |
| Không mở được đường dẫn | Báo Nhân; đường dẫn tạm của Cloudflare sẽ thay đổi khi dựng lại |
| Cần quay lại từ đầu | Báo Nhân dựng lại dữ liệu member5, vì mỗi lần quay đều làm thay đổi dữ liệu |
