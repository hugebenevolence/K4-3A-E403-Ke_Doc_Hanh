// Các trang: giới thiệu → đăng nhập → thư viện chọn slide → không gian học.

import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";
import { AuthProvider, RequireAuth } from "./auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";

// Thư viện và không gian học kéo theo PDF.js (hơn 1MB): tách ra tải sau, để
// trang giới thiệu mở ngay cả trên mạng chậm.
const Library = lazy(() => import("./pages/Library"));
const Learn = lazy(() => import("./pages/Learn"));
const Graph = lazy(() => import("./pages/Graph"));

export default function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<p className="p-6 font-sans text-[13px] text-neutral-400">Đang tải…</p>}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/library"
            element={
              <RequireAuth>
                <Library />
              </RequireAuth>
            }
          />
          <Route
            path="/graph"
            element={
              <RequireAuth>
                <Graph />
              </RequireAuth>
            }
          />
          <Route
            path="/learn/:slug"
            element={
              <RequireAuth>
                <Learn />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AuthProvider>
  );
}
