// Vài mảnh giao diện dùng lại nhiều chỗ.
//
// Gom vào một file để nút ở thanh công cụ và nút ở khung dạy trông giống hệt
// nhau — rải class Tailwind ra từng chỗ thì mỗi nơi lệch một chút, và cái lệch
// đó là thứ làm giao diện trông nghiệp dư.

const BASE =
  "text-[13px] px-3 py-1.5 rounded-lg border transition-colors " +
  "disabled:cursor-default disabled:bg-neutral-100 disabled:text-neutral-400 " +
  "disabled:border-neutral-200";

const STYLES = {
  // Đen tuyền cho hành động chính: trong bảng đơn sắc, độ tương phản là thứ
  // duy nhất còn lại để nói "bấm cái này".
  primary:
    "bg-neutral-900 text-white border-transparent hover:bg-neutral-700 " +
    "active:bg-neutral-800",
  normal:
    "bg-white text-neutral-900 border-neutral-200 hover:bg-neutral-50 " +
    "active:bg-neutral-100",
  quiet:
    "bg-transparent text-neutral-500 border-transparent hover:text-neutral-900 " +
    "hover:bg-neutral-100",
};

export function Button({ variant = "normal", pressed, className = "", ...props }) {
  const look = pressed ? STYLES.primary : STYLES[variant];
  return (
    <button
      {...props}
      aria-pressed={pressed}
      className={`${BASE} ${look} ${className}`}
    />
  );
}

export function Eyebrow({ children }) {
  return (
    <span className="block text-[11px] uppercase tracking-[0.07em] text-neutral-400 font-semibold">
      {children}
    </span>
  );
}

export function Separator() {
  return <span className="w-px h-4 bg-neutral-200 shrink-0" />;
}

/** Chấm trạng thái. Báo bằng CẢ chữ lẫn hình — HIG yêu cầu phản hồi không phụ
 *  thuộc riêng vào màu, để người mù màu và VoiceOver vẫn nhận được. */
export function LiveDot({ mode, label }) {
  const tone = mode === "idle" ? "bg-neutral-300" : "bg-neutral-900";
  return (
    <div className="ml-auto flex items-center gap-2 text-[13px] text-neutral-600">
      <span className={`pulse size-2 rounded-full shrink-0 ${tone}`} data-mode={mode} />
      <span>{label}</span>
    </div>
  );
}

const BARS = 12;

/** Vạch mức âm: bằng chứng tức thì rằng mic đang ăn.
 *
 *  Chữ từ STT về sau 1–2 giây, nên khoảng lặng đầu lượt là lúc học viên không
 *  biết máy có nghe không — đo thật thì họ ngừng lại và nói lại từ đầu. Vạch
 *  này nhúc nhích ngay từ âm đầu tiên.
 *
 *  Vẽ bằng ô rời chứ không phải một thanh trượt mượt: mắt bắt chuyển động rời
 *  rạc tốt hơn nhiều, và ở bảng đơn sắc thì đây là cách duy nhất còn lại để
 *  diễn tả cường độ mà không dùng màu. */
export function LevelMeter({ level }) {
  const lit = Math.round(level * BARS);
  return (
    <span className="flex items-end gap-0.5" aria-hidden="true">
      {Array.from({ length: BARS }, (_, i) => (
        <span
          key={i}
          className={`w-0.5 rounded-full transition-colors ${
            i < lit ? "bg-neutral-900" : "bg-neutral-200"
          }`}
          // Cao dần sang phải: hình dáng nói lên "to dần" ngay cả khi đứng yên.
          style={{ height: `${6 + i}px` }}
        />
      ))}
    </span>
  );
}
