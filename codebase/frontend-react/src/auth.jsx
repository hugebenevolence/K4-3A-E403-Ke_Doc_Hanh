// Đăng nhập cho bản thử nghiệm nội bộ: tài khoản cố định do nhóm cấp.
//
// Server là nơi quyết định có cần đăng nhập hay không (biến MEMBERS). Chạy máy
// cá nhân không đặt MEMBERS thì /api/me trả lời luôn, và trang đăng nhập tự
// bỏ qua — không bắt người đang dev gõ mật khẩu.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router";
import { api, AUTH_EXPIRED, storeAuth } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // "checking" lúc đầu, rồi "in" | "out" | "offline".
  const [status, setStatus] = useState("checking");
  const [member, setMember] = useState(null);

  const check = useCallback(() => {
    api("/me")
      .then((me) => {
        setMember(me);
        setStatus("in");
      })
      .catch((err) => {
        if (err.status === 401) {
          storeAuth(null);
          setMember(null);
          setStatus("out");
        } else {
          setStatus("offline");
        }
      });
  }, []);

  useEffect(check, [check]);

  const retry = useCallback(() => {
    setStatus("checking");
    check();
  }, [check]);

  useEffect(() => {
    function expired() {
      storeAuth(null);
      setMember(null);
      setStatus("out");
    }
    addEventListener(AUTH_EXPIRED, expired);
    return () => removeEventListener(AUTH_EXPIRED, expired);
  }, []);

  const login = useCallback(async (username, password) => {
    const res = await api("/auth/login", { method: "POST", body: { username, password } });
    storeAuth(res.auth ? { token: res.token, name: res.name } : null);
    setMember({ name: res.name, auth: res.auth });
    setStatus("in");
  }, []);

  const logout = useCallback(() => {
    storeAuth(null);
    setMember(null);
    // Server không bật đăng nhập thì "đăng xuất" chẳng có nghĩa gì — hỏi lại
    // để trạng thái khớp với server thay vì kẹt ở "out".
    retry();
  }, [retry]);

  const value = useMemo(
    () => ({ status, member, login, logout, retry }),
    [status, member, login, logout, retry],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

/** Trang cần đăng nhập: chưa đăng nhập thì sang /login, xong quay lại đúng chỗ. */
export function RequireAuth({ children }) {
  const { status, retry } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return <p className="p-6 font-sans text-[13px] text-neutral-400">Đang tải…</p>;
  }
  if (status === "offline") {
    return (
      <div className="grid min-h-screen place-items-center bg-white px-4 font-sans">
        <div className="text-center">
          <p className="m-0 text-[15px] font-medium text-neutral-900">Không kết nối được máy chủ</p>
          <p className="m-0 mt-1 text-[13px] text-neutral-500">Kiểm tra backend đang chạy rồi thử lại.</p>
          <button
            onClick={retry}
            className="mt-4 h-9 rounded-lg bg-neutral-900 px-4 text-[13px] font-medium text-white hover:bg-neutral-700"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }
  if (status === "out") {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return children;
}
