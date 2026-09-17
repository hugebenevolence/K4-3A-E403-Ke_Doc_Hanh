import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5500,
    // Cùng đường dẫn /api như lúc deploy (backend phục vụ luôn giao diện), để
    // code gọi API không phải biết đang chạy dev hay chạy thật. 127.0.0.1 chứ
    // không phải localhost: Node phân giải localhost ra IPv6 (::1) trong khi
    // uvicorn chỉ nghe IPv4, và proxy báo 502.
    proxy: { "/api": { target: "http://127.0.0.1:8000", ws: true } },
  },
});
