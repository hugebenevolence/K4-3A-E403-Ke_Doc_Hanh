// Vài mảnh giao diện dùng lại nhiều chỗ.
//
// Gom vào một file để nút ở thanh công cụ và nút ở khung hội thoại trông giống
// hệt nhau — rải class Tailwind ra từng chỗ thì mỗi nơi lệch một chút, và cái
// lệch đó là thứ làm giao diện trông nghiệp dư.

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { blurIn, EASE } from "./motion";

const BASE =
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap text-[13px] font-medium " +
  "rounded-lg border transition-colors select-none " +
  "disabled:pointer-events-none disabled:opacity-40";

const STYLES = {
  // Đen tuyền cho hành động chính: trong bảng đơn sắc, độ tương phản là thứ
  // duy nhất còn lại để nói "bấm cái này".
  primary: "bg-neutral-900 text-white border-neutral-900 hover:bg-neutral-700",
  normal: "bg-white text-neutral-800 border-neutral-200 hover:bg-neutral-50 hover:border-neutral-300",
  quiet: "bg-transparent text-neutral-500 border-transparent hover:text-neutral-900 hover:bg-neutral-100",
};

const SIZES = { sm: "h-7 px-2.5", md: "h-8 px-3", lg: "h-10 px-4 text-[14px]" };

export function Button({ variant = "normal", size = "md", pressed, className = "", ...props }) {
  const look = pressed ? STYLES.primary : STYLES[variant];
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={{ duration: 0.12 }}
      {...props}
      aria-pressed={pressed}
      className={`${BASE} ${SIZES[size]} ${look} ${className}`}
    />
  );
}

export function Eyebrow({ children, className = "" }) {
  return (
    <span className={`block text-[11px] font-medium tracking-wide text-neutral-400 ${className}`}>
      {children}
    </span>
  );
}

export function Badge({ children, tone = "neutral" }) {
  const look =
    tone === "strong"
      ? "bg-neutral-900 text-white"
      : "bg-neutral-100 text-neutral-600 ring-1 ring-inset ring-neutral-200";
  return (
    <span className={`inline-flex h-5 shrink-0 items-center whitespace-nowrap rounded-md px-1.5 text-[11px] font-medium ${look}`}>
      {children}
    </span>
  );
}

export function Kbd({ children }) {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-b-2 border-neutral-200 bg-white px-1 font-sans text-[11px] text-neutral-500">
      {children}
    </kbd>
  );
}

export function Separator({ vertical = true }) {
  return vertical ? (
    <span className="h-4 w-px shrink-0 bg-neutral-200" />
  ) : (
    <span className="h-px w-full bg-neutral-200" />
  );
}

/** Chấm trạng thái. Báo bằng CẢ chữ lẫn hình — HIG yêu cầu phản hồi không phụ
 *  thuộc riêng vào màu, để người mù màu và VoiceOver vẫn nhận được. */
export function LiveDot({ mode, label }) {
  const tone = mode === "idle" ? "bg-neutral-300" : "bg-neutral-900";
  return (
    <div className="flex items-center gap-2 text-[12px] text-neutral-500" aria-live="polite">
      <span className={`pulse size-1.5 shrink-0 rounded-full ${tone}`} data-mode={mode} />
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={label} {...blurIn} transition={{ duration: 0.25, ease: EASE }}>
          {label}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

/** Chữ hiện dần từng từ, mỗi từ nhoè rồi rõ.
 *
 *  Dùng cho lời agent: học viên đọc theo nhịp chữ xuất hiện thay vì bị ném một
 *  khối chữ vào mặt. Tổng thời gian có trần — câu dài mà chạy từng từ đủ nhịp
 *  thì học viên phải ngồi chờ chữ, đúng lúc họ đang muốn trả lời. */
export function WordsIn({ text, className = "" }) {
  const words = text.split(/(\s+)/);
  const step = Math.min(0.022, 0.9 / Math.max(words.length, 1));
  return (
    <span className={className}>
      {words.map((w, i) =>
        /^\s+$/.test(w) ? (
          w
        ) : (
          <motion.span
            key={i}
            className="inline-block whitespace-pre"
            initial={{ opacity: 0, filter: "blur(4px)" }}
            animate={{ opacity: 1, filter: "blur(0px)" }}
            transition={{ duration: 0.35, delay: i * step, ease: EASE }}
          >
            {w}
          </motion.span>
        ),
      )}
    </span>
  );
}

/** Luân phiên vài cụm từ tại cùng một chỗ, cụm cũ nhoè đi, cụm mới nhoè vào. */
export function RotatingWords({ words, interval = 2600, className = "" }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((n) => (n + 1) % words.length), interval);
    return () => clearInterval(id);
  }, [words.length, interval]);

  return (
    <span className={`relative inline-grid ${className}`}>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={words[i]}
          className="col-start-1 row-start-1 whitespace-nowrap"
          initial={{ opacity: 0, filter: "blur(10px)", y: 8 }}
          animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
          exit={{ opacity: 0, filter: "blur(10px)", y: -8 }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          {words[i]}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

const BARS = 14;

/** Vạch mức âm: bằng chứng tức thì rằng mic đang ăn.
 *
 *  Chữ từ STT về sau 1–2 giây, nên khoảng lặng đầu lượt là lúc học viên không
 *  biết máy có nghe không — và họ thường ngừng lại nói lại từ đầu. Vạch này
 *  nhúc nhích ngay từ âm đầu tiên. */
export function LevelMeter({ level }) {
  const middle = (BARS - 1) / 2;
  return (
    <span className="flex h-4 items-center gap-[3px]" aria-hidden="true">
      {Array.from({ length: BARS }, (_, i) => {
        // Sáng từ giữa ra hai bên, giữa cao hai đầu thấp: đọc ngay ra là một
        // làn sóng âm, kể cả lúc đứng yên.
        const distance = Math.abs(i - middle) / (middle + 1);
        const on = distance < level;
        const shape = 0.35 + 0.65 * Math.sin((Math.PI * (i + 0.5)) / BARS);
        return (
          <motion.span
            key={i}
            className={`w-[3px] rounded-full ${on ? "bg-neutral-900" : "bg-neutral-200"}`}
            animate={{ height: `${Math.max(3, (on ? 16 : 6) * shape)}px` }}
            transition={{ duration: 0.12 }}
          />
        );
      })}
    </span>
  );
}
