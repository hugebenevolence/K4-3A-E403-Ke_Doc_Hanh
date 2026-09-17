// Mọi lời gọi tới backend đi qua đây, để token gắn vào đúng một chỗ.
//
// Đường dẫn tương đối "/api": deploy thì backend phục vụ luôn giao diện nên
// cùng một địa chỉ; chạy dev thì Vite chuyển tiếp /api sang cổng 8000. Không
// ghép cứng "http://host:8000" nữa — qua tunnel HTTPS thì địa chỉ đó không tồn
// tại, và trình duyệt chặn gọi http từ một trang https.

const KEY = "giang-lai-auth";

/** Phát ra khi server báo token hết hạn — AuthProvider nghe để đưa về đăng nhập. */
export const AUTH_EXPIRED = "giang-lai:auth-expired";

export function storedAuth() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null;
  } catch {
    return null;
  }
}

export function storeAuth(auth) {
  try {
    if (auth) localStorage.setItem(KEY, JSON.stringify(auth));
    else localStorage.removeItem(KEY);
  } catch {
    // Trình duyệt chặn lưu trữ: vẫn học được, chỉ phải đăng nhập lại khi tải lại trang.
  }
}

export function authHeaders() {
  const token = storedAuth()?.token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function api(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: { ...authHeaders(), ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Không kết nối được máy chủ");
  }
  if (res.status === 401 && path !== "/auth/login") dispatchEvent(new Event(AUTH_EXPIRED));
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail, () => "");
    throw new ApiError(res.status, typeof detail === "string" && detail ? detail : `Lỗi ${res.status}`);
  }
  return res.json();
}

/** Địa chỉ WebSocket cùng máy chủ. Trình duyệt không gắn được header vào
 *  WebSocket, nên token đi qua query. */
export function socketUrl(path, params) {
  const query = new URLSearchParams(params);
  const token = storedAuth()?.token;
  if (token) query.set("token", token);
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}/api${path}?${query}`;
}

export function deckPdf(slug) {
  return { url: `/api/decks/${encodeURIComponent(slug)}/pdf`, httpHeaders: authHeaders() };
}
