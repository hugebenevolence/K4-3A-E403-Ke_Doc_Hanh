// Đăng nhập bằng tài khoản nhóm cấp — bản thử nghiệm nội bộ, không đăng ký.

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth";
import { blurIn, EASE } from "../motion";
import { Brand } from "../site";

function Field({ label, ...props }) {
  return (
    <label className="block">
      <span className="text-[13px] font-medium text-neutral-700">{label}</span>
      <input
        {...props}
        className="mt-1.5 block h-10 w-full rounded-lg border border-neutral-200 bg-white px-3 text-[14px] text-neutral-900 transition-shadow outline-none placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-4 focus:ring-neutral-900/5"
      />
    </label>
  );
}

export default function Login() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const from = useLocation().state?.from || "/library";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // Đổi key mỗi lần sai để khung lắc lại, kể cả khi sai y như lần trước.
  const [attempt, setAttempt] = useState(0);

  // Đã đăng nhập, hoặc server không bật đăng nhập: không có gì để làm ở đây.
  if (status === "in" && !busy) return <Navigate to={from} replace />;

  async function submit(e) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Nhập tên đăng nhập và mật khẩu");
      setAttempt((n) => n + 1);
      return;
    }
    setBusy(true);
    setError("");
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.status === 401 ? "Sai tên đăng nhập hoặc mật khẩu" : err.message);
      setAttempt((n) => n + 1);
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-neutral-50 font-sans text-neutral-900 antialiased">
      <div className="mx-auto flex h-14 max-w-6xl items-center px-4 sm:px-6">
        <Brand />
      </div>

      <div className="grid min-h-[calc(100vh-56px)] place-items-center px-4 pb-16">
        <motion.div
          key={attempt}
          initial={attempt ? { x: 0 } : { opacity: 0, y: 16, filter: "blur(10px)" }}
          animate={attempt ? { x: [0, -8, 7, -5, 3, 0] } : { opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={attempt ? { duration: 0.4 } : { duration: 0.7, ease: EASE }}
          className="w-full max-w-95"
        >
          <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-[0_1px_2px_rgb(0_0_0/0.04),0_24px_60px_-30px_rgb(0_0_0/0.2)] sm:p-8">
            <h1 className="m-0 text-[24px] font-semibold tracking-[-0.02em]">Đăng nhập</h1>
            <p className="m-0 mt-1 text-[14px] text-neutral-500">Dùng tài khoản nhóm đã cấp cho bạn.</p>

            <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
              <Field
                label="Tên đăng nhập"
                name="username"
                autoComplete="username"
                autoCapitalize="none"
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              <Field
                label="Mật khẩu"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <AnimatePresence mode="wait">
                {error && (
                  <motion.p
                    key={error}
                    {...blurIn}
                    role="alert"
                    className="m-0 rounded-lg bg-neutral-100 px-3 py-2 text-[13px] font-medium text-neutral-900"
                  >
                    {error}
                  </motion.p>
                )}
              </AnimatePresence>

              <motion.button
                whileTap={{ scale: 0.98 }}
                type="submit"
                disabled={busy}
                className="h-10 w-full rounded-lg bg-neutral-900 text-[14px] font-medium text-white transition-colors hover:bg-neutral-700 disabled:opacity-60"
              >
                {busy ? "Đang kiểm tra…" : "Đăng nhập"}
              </motion.button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
