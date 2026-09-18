# Kịch bản quay video demo — từng bước (khoảng 3 phút 30)

Video dự phòng cho phần demo live ở slide 3: một case chuẩn và một case chỗ khó
(`brief/02-guide.md` §5.1). Mọi câu giảng dưới đây đã chạy thật với bộ chấm thật
và ra đúng kết quả ghi ở dòng **THẤY**.

**Cách đọc kịch bản.** Mỗi bước có ba dòng:
- **NÓI** — lời thuyết minh cho người xem. Nói khi **KHÔNG** giữ phím Space.
- **LÀM** — thao tác trên màn hình.
- **THẤY** — kết quả phải hiện ra. Không thấy thì xem bảng sự cố ở cuối.

Câu **GIẢNG CHO HỌC TRÒ** (in đậm, trong khung trích) là câu nói vào mic: **giữ
Space → nói → thả Space**. Trong lúc giữ Space, mic đang thu, nên chỉ nói đúng câu
đó, không chen thuyết minh vào.

---

## Chuẩn bị (trước khi bấm quay)

- [ ] Chrome, cửa sổ khoảng 1440×900, zoom 100%. Tắt thông báo. **Chỉ quay cửa
      sổ trình duyệt.**
- [ ] Đeo tai nghe (để mic không thu lại giọng học trò AI).
- [ ] Mở link deploy, đăng nhập **member5** (mật khẩu hỏi Nhân — không ghi ở đây).
      Cho phép micro khi được hỏi.
- [ ] Đứng ở trang **Thư viện**. Khung "Hành trình học của bạn" phải hiện
      **3 Đã hiểu · 1 Cần sửa**. Không đúng → báo Nhân dựng lại dữ liệu.

---

## Bước 1 — Giới thiệu hệ thống (0:00–0:35)

**LÀM:** đứng yên ở trang Thư viện.

**NÓI:**
> Trong khoá AI20k, học viên hỏi tutor xin giảng hơn 5.600 lần. Nhưng khi học viên
> tự nói ra cách mình hiểu, tutor giảng lại cho họ gần 87% số lần, và chỉ hỏi ngược
> 0,2%. Học viên đọc xong không biết mình hiểu tới đâu.
>
> Giảng lại đảo vai: **bạn** là người giảng, AI là một học trò chưa biết gì. Bạn
> chọn một phần slide, phần đó bị che đi, và bạn giảng bằng lời của mình. Học trò
> chỉ hỏi đúng một câu vào chỗ bạn còn hổng — nó không bao giờ đưa đáp án. Mọi thứ
> được đối chiếu với đúng slide của khoá, không phải kiến thức chung của AI.

---

## Bước 2 — Hành trình học (0:35–0:50)

**LÀM:** rê chuột qua khung "Hành trình học của bạn", dừng ở dòng *"Có 1 trang bạn
từng giảng sai"*.

**NÓI:**
> Tài khoản này đã giảng trước vài trang. Hệ thống nhớ trang nào tôi đã hiểu, và
> trang nào lần trước tôi giảng sai — mức hiểu chỉ đi lên khi tôi giảng được, không
> phải khi tôi mở slide ra đọc.

---

## Bước 3 — Chọn slide để giảng (0:50–1:05)

**LÀM:**
1. Cột trái, bấm bộ **Day 1 · AI & LLM Foundation** (bộ đầu tiên).
2. Trong lưới slide, bấm **Slide 12 — Sinh văn bản = đoán → nối vào câu → đoán tiếp**.
3. Trên slide, **kéo một khung** quanh phần nội dung chính.
4. Bấm **Bắt đầu giảng**.

**THẤY:** vùng vừa chọn **bị che lại**; học trò đọc câu mở bài.

**NÓI** (sau khi học trò nói xong):
> Phần tôi chọn đã bị che. Giờ tôi phải giảng bằng lời mình, không đọc lại được.

---

## Bước 4 — Case chuẩn: giảng một trang (1:05–1:35)

**LÀM:** giữ **Space**, nói câu dưới, thả **Space**.

> **GIẢNG CHO HỌC TRÒ:** "Model sinh văn bản bằng cách đoán một token tiếp theo dựa
> trên xác suất. Sau đó nó nối token vừa đoán vào ngữ cảnh rồi chạy lại từ đầu để
> đoán token kế tiếp. Vì vậy câu trả lời được tạo ra từng mảnh một chứ không phải
> nghĩ ra cả câu một lúc."

**THẤY:** thẻ **"Học trò đã hiểu phần này"**; ở dàn ý bên trái, slide 12 có
**chấm đặc**.

**NÓI:**
> Học trò chấm lời tôi với đúng slide này. Tôi giảng đủ cơ chế nên nó hiểu, và
> slide 12 được đánh dấu đã hiểu.

*Nếu học trò hỏi thêm một câu thay vì đóng phiên — giữ Space, trả lời:*
> **"Nó cứ lặp lại như vậy cho tới khi đủ câu, mỗi vòng chỉ thêm đúng một mẩu."**

---

## Bước 5 — Case chỗ khó: nói sai (1:35–2:05)

**LÀM:**
1. Ở dàn ý bên trái, bấm **13 · Token** (chấm **vòng rỗng** = cần sửa).
2. Bấm **Bắt đầu giảng**, đợi học trò mở bài xong.
3. Giữ **Space**, nói câu **sai** dưới, thả **Space**.

> **GIẢNG CHO HỌC TRÒ:** "Mỗi token là một từ, và tiếng Việt tốn ít token hơn tiếng
> Anh vì từ tiếng Việt ngắn."

**THẤY:** học trò **không gật đầu, không sửa hộ** — nó hỏi ngược đúng một câu,
kiểu *"token thực tế là mảnh chữ hay ký tự như bạn nói, hay đúng là mỗi token một
từ vậy?"*

**NÓI:**
> Tôi vừa nói sai — đây là một hiểu lầm có thật trong chatlog của khoá. Học trò
> không bảo tôi sai, cũng không đưa đáp án. Nó hỏi đúng vào chỗ tôi hổng, để tôi tự
> nhận ra.

---

## Bước 6 — Tự sửa (2:05–2:35)

**LÀM:** giữ **Space**, nói câu dưới, thả **Space**.

> **GIẢNG CHO HỌC TRÒ:** "À mình nói sai. Model không đọc theo từng từ mà theo từng
> mẩu chữ nhỏ, một chữ dài hay có dấu có thể bị chặt ra thành ba bốn mẩu. Vì thế cùng
> một câu mà viết tiếng Việt có dấu thì ra nhiều mẩu hơn tiếng Anh, tức là tốn tiền
> hơn và dùng hết chỗ nhanh hơn."

**THẤY:** **"Học trò đã hiểu phần này"**; slide 13 ở dàn ý đổi từ vòng rỗng sang
**chấm đặc**.

**NÓI:**
> Tôi tự sửa được, và trang từng giảng sai giờ thành đã hiểu.

*Nếu còn bị hỏi thêm — giữ Space, trả lời:*
> **"Ví dụ 'Xin chào' có thể thành ba bốn mẩu, còn 'Hello' chỉ một mẩu."**

---

## Bước 7 — Bản đồ hiểu biết (2:35–2:50)

**LÀM:** bấm tab **Bản đồ** ở góc trên bên trái (cạnh tab Slide).

**THẤY:** các trang đã hiểu là chấm đen; trang Token có dấu **"Bạn đang ở đây"**.

**NÓI:**
> Mỗi chấm đen là một trang tôi đã giảng được. Bấm vào là thấy nguyên văn câu tôi
> đã nói — không phải câu AI viết lại.

**LÀM:** bấm đỉnh **Context** (D1 · tr. 14) — khung phải hiện câu đã giảng.

---

## Bước 8 — Nối hai buổi học (2:50–3:20)

**LÀM:**
1. Ở khung phải, bấm **Nối với trang khác**.
2. Rê chuột sang **Hệ thống AI** (D2 · tr. 16) — có đường nét đứt đi theo — bấm.

**THẤY:** học trò hỏi *"Bạn đã dạy mình «Context» và «Hệ thống AI» rồi. Hai trang
đó liên quan gì với nhau vậy bạn?"*

**LÀM:** giữ **Space**, nói câu dưới, thả **Space**.

> **GIẢNG CHO HỌC TRÒ:** "Ở Day 1, context là lượng chữ model nhìn được trong mỗi
> lần trả lời. Sang Day 2 thì context là một thành phần của hệ thống AI: mình đưa tài
> liệu nghiệp vụ vào context để model trả lời đúng với doanh nghiệp. Nhưng vì context
> có giới hạn và càng dài càng tốn tiền, nên không thể nhồi hết tài liệu mà phải chọn
> đúng phần liên quan."

**THẤY:** **"Học trò đã thấy chỗ nối"** → bấm **Xong** → một đường nối được **vẽ
dần ra** giữa trang Day 1 và trang Day 2, khung phải hiện đúng câu vừa nói.

**NÓI:**
> Hai buổi học khác nhau vừa được nối lại — bằng chính lời tôi giảng. Hệ thống không
> tự nối hộ, và nối sai thì không có đường nào hiện ra.

---

## Bước 9 — Kết (3:20–3:35)

**LÀM:** bấm **Thư viện** ở góc trên bên phải.

**THẤY:** "Hành trình học" giờ là **5 Đã hiểu · 0 Cần sửa**.

**NÓI:**
> Hai trang mới hiểu, một hiểu lầm đã sửa, một mối nối qua hai buổi học. Tất cả do
> chính tôi giảng ra — AI chỉ hỏi, không làm hộ.

---

## Khi có sự cố

| Sự cố | Làm gì |
|---|---|
| Mic không nhận, hoặc nhận sai chữ | Gõ đúng câu giảng vào ô chữ phía dưới → bấm **Gửi** (vẫn là luồng thật) |
| Học trò hỏi thêm ngoài dự kiến | Dùng câu dự phòng ghi ở từng bước |
| Bước 8 bị chấm "chưa thấy chỗ nối" | Bấm **Thử nối lại**, giảng: *"Vì context có hạn nên không nhồi hết tài liệu nghiệp vụ vào được, phải chọn đúng phần liên quan — đó là chỗ hai trang gặp nhau."* |
| Học trò đang nói mà muốn đi tiếp | Bấm **Bỏ qua** hoặc nhấn Space để cắt |
| Link không mở được | Báo Nhân — link Cloudflare tạm sẽ đổi khi dựng lại |
| Muốn quay lại từ đầu | Báo Nhân dựng lại dữ liệu member5 (mỗi lần quay đã làm đổi dữ liệu) |
