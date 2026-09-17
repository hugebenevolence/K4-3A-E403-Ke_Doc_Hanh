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

| Tệp | Việc |
| --- | --- |
| `src/useSession.js` | WebSocket, mic, hàng đợi phát tiếng — toàn bộ trạng thái phiên |
| `src/App.jsx` | Khung màn hình, phím tắt, chọn chế độ slide hay code |
| `src/TeachPanel.jsx` | Lời thoại hai bên và các nút điều khiển |
| `src/SlideView.jsx` | Vẽ PDF bằng PDF.js, khoanh vùng theo bbox |
| `src/CodeView.jsx` | Monaco, tô sáng khoảng dòng agent đang bàn |
| `src/ui.jsx` | Nút, nhãn, chỉ báo trạng thái dùng chung |
| `public/pcm-worklet.js` | Lấy PCM16 thô cho STT (MediaRecorder cho ra webm/opus, STT không nhận) |

## Quy ước giao diện

Đơn sắc trắng–đen–xám, không icon, không màu thương hiệu. Chỗ duy nhất được
phép nổi bật là vùng nội dung agent đang hỏi tới — mọi mảng màu khác đều tranh
sự chú ý với chính việc học viên đang làm.

Style viết bằng Tailwind. `src/styles.css` chỉ giữ những gì Tailwind không với
tới: decoration do Monaco tự chèn vào DOM, overlay trên canvas PDF cần toạ độ
tính bằng JS, và keyframe của chỉ báo trạng thái.

## Phím tắt

| Phím | Việc |
| --- | --- |
| `Space` | Xong lượt nói, hoặc bỏ qua khi agent đang nói |
| `←` `→` | Lật slide |
| `G` | Về trang đang dạy |
| `F` | Bật/tắt chế độ vùng đang dạy |
