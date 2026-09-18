# Kịch bản video demo dự phòng (CP5) — khoảng 3 phút

Video này là **bản dự phòng** cho phần demo live ở slide 3: một case chuẩn + một
case chỗ khó (`brief/02-guide.md` §5.1). Mọi câu thoại dưới đây đã chạy thật với
bộ chấm thật và ra đúng kết quả ghi bên cạnh.

## Trước khi quay (5 phút)

- [ ] Mở link deploy bằng Chrome, **chỉ quay cửa sổ trình duyệt** — không quay
      màn hình có `.env` hay terminal.
- [ ] Cửa sổ khoảng 1440×900, zoom 100%. Tắt thông báo máy.
- [ ] Đăng nhập **member5** (mật khẩu hỏi Nhân — không ghi vào file này).
- [ ] Cho phép micro khi trình duyệt hỏi. Đeo tai nghe để mic không thu lại
      giọng học trò.
- [ ] Vào **Thư viện**, kiểm tra khung "Hành trình học của bạn" đang hiện:
      **3 Đã hiểu · 1 Cần sửa**, lời nhắc *"Có 1 trang bạn từng giảng sai"*.
      Không đúng như vậy → báo Nhân dựng lại dữ liệu (`scripts/seed_demo.py`).
- [ ] Mở sẵn file này ở máy khác hoặc in ra để đọc thoại.

Nói bằng giọng: **giữ phím Space** trong lúc nói, **thả ra** là gửi. Mic trục
trặc thì gõ đúng câu đó vào ô chữ rồi bấm **Gửi** — vẫn là luồng thật.

---

## Cảnh 0 — Mở đầu · Thư viện (0:00–0:20)

**Màn hình:** trang Thư viện.

**Thao tác:** rê chuột qua khung "Hành trình học của bạn", dừng ở lời nhắc
"Có 1 trang bạn từng giảng sai".

**Thuyết minh:**
> Đây là Giảng lại: học bằng cách giảng lại slide cho một học trò AI. Tài khoản
> này đã giảng trước vài trang để bản đồ có nội dung. Hệ thống nhớ trang nào tôi
> đã hiểu, và trang nào lần trước tôi giảng sai.

---

## Cảnh 1 — Case chuẩn · Day 1, slide 12 "Sinh văn bản" (0:20–1:10)

**Thao tác:**
1. Cột trái chọn bộ **Day 1 · AI & LLM Foundation** (bộ đầu tiên) → trong lưới
   slide bấm **Slide 12 · Sinh văn bản = đoán → nối vào câu → đoán tiếp**.
2. Trên slide, **kéo một khung** quanh phần nội dung chính (hoặc không chọn gì
   để giảng cả trang) → bấm **Bắt đầu giảng** (hoặc Enter).
3. Vùng vừa chọn **bị che lại**. Học trò đọc câu mở bài — để nó nói hết.
4. Giữ Space và nói:

> **"Model sinh văn bản bằng cách đoán một token tiếp theo dựa trên xác suất.
> Sau đó nó nối token vừa đoán vào ngữ cảnh rồi chạy lại từ đầu để đoán token kế
> tiếp. Vì vậy câu trả lời được tạo ra từng mảnh một chứ không phải nghĩ ra cả
> câu một lúc."**

**Kết quả mong đợi:** thẻ **"Học trò đã hiểu phần này"** · dàn ý bên trái,
slide 12 có **chấm đặc** (đã hiểu).

**Thuyết minh (lúc chờ chấm):**
> Slide bị che: tôi phải giảng bằng lời của mình, không đọc lại. Học trò chỉ biết
> đúng những gì tôi vừa nói.

*Nếu học trò hỏi thêm một câu thay vì đóng phiên, trả lời:*
> "Nó cứ lặp lại như vậy cho tới khi đủ câu, mỗi vòng chỉ thêm đúng một mẩu."

---

## Cảnh 2 — Chỗ khó · slide 13 "Token", đang **Cần sửa** (1:10–2:10)

**Thao tác:**
1. Dàn ý bên trái, bấm **13 · Token** (chấm **vòng rỗng** = cần sửa) →
   **Bắt đầu giảng**.
2. Giữ Space và nói **câu SAI** (hiểu lầm có thật trong chatlog):

> **"Mỗi token là một từ, và tiếng Việt tốn ít token hơn tiếng Anh vì từ tiếng
> Việt ngắn."**

**Kết quả mong đợi:** học trò **không gật đầu, không sửa hộ** — nó hỏi ngược
đúng một câu, kiểu *"token thực tế là mảnh chữ hay ký tự như bạn nói, hay đúng là
mỗi token một từ vậy?"*

**Thuyết minh:**
> Tôi vừa nói sai. Học trò không bảo tôi sai, cũng không đưa đáp án — nó hỏi
> đúng vào chỗ tôi hổng, để tôi tự nhận ra.

3. Giữ Space và nói **câu tự sửa**:

> **"À mình nói sai. Model không đọc theo từng từ mà theo từng mẩu chữ nhỏ, một
> chữ dài hay có dấu có thể bị chặt ra thành ba bốn mẩu. Vì thế cùng một câu mà
> viết tiếng Việt có dấu thì ra nhiều mẩu hơn tiếng Anh, tức là tốn tiền hơn và
> dùng hết chỗ nhanh hơn."**

**Kết quả mong đợi:** **"Học trò đã hiểu phần này"** · dàn ý slide 13 đổi từ
vòng rỗng sang **chấm đặc**.

*Nếu còn bị hỏi thêm, nói:*
> "Ví dụ 'Xin chào' có thể thành ba bốn mẩu, còn 'Hello' chỉ một mẩu."

---

## Cảnh 3 — Bản đồ · nối hai buổi học (2:10–3:10)

**Thao tác:**
1. Bấm tab **Bản đồ** ở góc trên bên trái (cạnh tab Slide). Trang Token có dấu
   **"Bạn đang ở đây"**.
2. Bấm đỉnh **Context** (D1 · tr. 14) → khung phải hiện nguyên văn câu đã giảng
   → bấm **Nối với trang khác**.
3. Rê chuột sang **Hệ thống AI** (D2 · tr. 16) — có đường nét đứt đi theo — bấm.
4. Học trò hỏi: *"Bạn đã dạy mình «Context» và «Hệ thống AI» rồi. Hai trang đó
   liên quan gì với nhau vậy bạn?"* Giữ Space và nói:

> **"Ở Day 1, context là lượng chữ model nhìn được trong mỗi lần trả lời. Sang
> Day 2 thì context là một thành phần của hệ thống AI: mình đưa tài liệu nghiệp
> vụ vào context để model trả lời đúng với doanh nghiệp. Nhưng vì context có giới
> hạn và càng dài càng tốn tiền, nên không thể nhồi hết tài liệu mà phải chọn đúng
> phần liên quan."**

**Kết quả mong đợi:** **"Học trò đã thấy chỗ nối"** → bấm **Xong** → cạnh
**được vẽ dần ra** giữa Day 1 và Day 2, khung phải hiện đúng câu nối.

**Thuyết minh:**
> Mối nối này đi qua hai buổi học, và nó mang đúng câu tôi nói — hệ thống không
> tự nối hộ. Nối sai thì không có cạnh nào hiện ra.

---

## Cảnh 4 — Kết (3:10–3:25)

**Thao tác:** bấm **Thư viện** (góc trên phải).

**Kết quả mong đợi:** "Hành trình học" giờ là **5 Đã hiểu · 0 Cần sửa**.

**Thuyết minh:**
> Hai trang mới hiểu, một hiểu lầm đã sửa, một mối nối qua hai buổi — tất cả do
> chính tôi giảng ra.

---

## Khi có sự cố

| Sự cố | Làm gì |
|---|---|
| Mic không nhận hoặc nhận sai chữ | Gõ đúng câu thoại vào ô chữ → **Gửi** |
| Học trò hỏi thêm ngoài dự kiến | Dùng câu dự phòng ghi ở từng cảnh |
| Cảnh 3 bị chấm "chưa thấy chỗ nối" | **Thử nối lại**, nói: *"Vì context có hạn nên không nhồi hết tài liệu nghiệp vụ vào được, phải chọn đúng phần liên quan — đó là chỗ hai trang gặp nhau."* |
| Link không mở được | Báo Nhân — link Cloudflare tạm sẽ đổi khi dựng lại |
| Muốn quay lại từ đầu | Báo Nhân dựng lại dữ liệu member5 — tài khoản đã đổi sau lần quay trước |
