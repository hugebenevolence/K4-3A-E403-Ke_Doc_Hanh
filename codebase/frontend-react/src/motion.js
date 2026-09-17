// Nhịp chuyển động dùng chung, để mọi thứ trên màn hình chuyển động cùng một
// kiểu. Tách khỏi ui.jsx vì file chỉ chứa component thì hot-reload mới chạy.

/** Đường cong "ra nhanh, dừng êm" — dùng chung để mọi chuyển động cùng một nhịp. */
export const EASE = [0.22, 1, 0.36, 1];

/** Hiện ra từ trạng thái nhoè — chuyển động đặc trưng của ảnh tham chiếu. Nhoè
 *  rồi rõ đọc như "thứ này vừa được nghĩ ra", còn trượt vào thì chỉ đọc như
 *  "thứ này vừa được thêm vào danh sách". */
export const blurIn = {
  initial: { opacity: 0, y: 6, filter: "blur(6px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -4, filter: "blur(6px)" },
  transition: { duration: 0.45, ease: EASE },
};
