# Giao diện dạy lại

React + Vite + Tailwind. Học viên giải thích bài cho một "học trò AI"; giao diện
lo phần nghe, phần hiển thị nguồn (slide PDF hoặc code), và phần chỉ đúng chỗ
agent đang thắc mắc.

```bash
npm install
npm run dev        # http://localhost:5500
```

Cần backend chạy sẵn ở `:8000` (xem `../backend/README.md`). Mic chỉ hoạt động
trên localhost hoặc HTTPS.

## Bố cục

Ba cột theo khuôn của Profound (thanh bên · hội thoại · tài liệu), nền trắng:

| Tệp | Việc |
| --- | --- |
| `src/App.jsx` | Khung ba cột, phím tắt (giữ Space để nói) |
| `src/Sidebar.jsx` | Bài đang học, dàn ý slide có tiêu đề thật, lọc "đang dạy" |
| `src/Conversation.jsx` | Hội thoại: dòng "Đã nghĩ trong Xs · vai nào làm", thẻ trỏ nguồn, ô nhập nói/gõ |
| `src/SourcePanel.jsx` | Khung slide: tab, thanh công cụ, chuyển trang có hiệu ứng |
| `src/SlideView.jsx` | Vẽ PDF bằng PDF.js, khoanh vùng theo bbox, vẽ lại khi khung co giãn |
| `src/useSession.js` | WebSocket, mic, hàng đợi phát tiếng — toàn bộ trạng thái phiên |
| `src/vad.js` | Nhận ra lúc học viên nói xong (có test: `npm test`) |
| `src/ui.jsx`, `src/motion.js` | Thành phần dùng chung và nhịp chuyển động chung |
| `public/pcm-worklet.js` | Lấy PCM16 thô cho STT (MediaRecorder cho ra webm/opus, STT không nhận) |

## Quy ước giao diện

Nền trắng, đơn sắc trắng–đen–xám, không icon. Chỗ duy nhất được phép nổi bật là
vùng slide agent đang hỏi tới.

Chuyển động dùng thư viện `motion`, cùng một nhịp (`src/motion.js`): nội dung
mới hiện ra từ trạng thái nhoè, lời agent hiện dần từng từ, nền của mục đang
chọn trượt theo. Ai bật "giảm chuyển động" trong hệ điều hành thì tất cả tự tắt.

Thẻ trỏ nguồn trong hội thoại **cố ý không trích nguyên văn** đoạn slide: đo
trên LLM thật thì trích dẫn nằm ngay dưới câu hỏi ngược chính là đáp án.

Style viết bằng Tailwind. `src/styles.css` chỉ giữ overlay vẽ bằng toạ độ JS
trên canvas PDF và các keyframe.

## Phím tắt

| Phím | Việc |
| --- | --- |
| Giữ `Space` | Nói; thả ra là gửi. Khi agent đang nói thì bấm để bỏ qua |
| `←` `→` | Lật slide |
| `G` | Về trang đang dạy |
| `F` | Bật/tắt chế độ vùng đang dạy |
