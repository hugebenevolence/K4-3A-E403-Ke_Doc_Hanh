// Nhớ trang học viên mở gần nhất của mỗi bộ slide, để thư viện có nút "Học tiếp".
// Chỉ là tiện ích trên máy này: mất (trình duyệt ẩn danh, chặn lưu trữ) thì
// học viên chỉ phải tự chọn lại trang.

const key = (slug) => `giang-lai-last:${slug}`;

export function lastPage(slug) {
  try {
    return Number(localStorage.getItem(key(slug))) || null;
  } catch {
    return null;
  }
}

export function rememberPage(slug, page) {
  try {
    localStorage.setItem(key(slug), String(page));
  } catch {
    // Không lưu được thì chỉ mất nút "Học tiếp", không ảnh hưởng việc học.
  }
}
