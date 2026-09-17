// Tiến độ học trên máy này: trang mở gần nhất, và những trang đã giảng được.
// Chỉ là tiện ích hiển thị: mất (trình duyệt ẩn danh, chặn lưu trữ) thì học
// viên chỉ mất nút "Học tiếp" và dấu đã giảng, không mất gì của phiên học.

const lastKey = (slug) => `giang-lai-last:${slug}`;
const taughtKey = (slug) => `giang-lai-taught:${slug}`;

export function lastPage(slug) {
  try {
    return Number(localStorage.getItem(lastKey(slug))) || null;
  } catch {
    return null;
  }
}

export function rememberPage(slug, page) {
  try {
    localStorage.setItem(lastKey(slug), String(page));
  } catch {
    // Không lưu được thì thôi.
  }
}

export function taughtPages(slug) {
  try {
    return new Set(JSON.parse(localStorage.getItem(taughtKey(slug))) || []);
  } catch {
    return new Set();
  }
}

export function markTaught(slug, page) {
  const pages = taughtPages(slug);
  pages.add(page);
  try {
    localStorage.setItem(taughtKey(slug), JSON.stringify([...pages].sort((a, b) => a - b)));
  } catch {
    // Không lưu được thì thôi.
  }
}
