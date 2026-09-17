import "@fontsource-variable/inter";
import { MotionConfig } from "motion/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    {/* Ai bật "giảm chuyển động" trong hệ điều hành thì mọi animation của
        motion tự tắt — không phải nhớ kiểm ở từng component. */}
    <MotionConfig reducedMotion="user">
      <App />
    </MotionConfig>
  </StrictMode>,
);
