// Mức hiểu từng trang slide — một ngôn ngữ hình ảnh dùng chung cho thư viện,
// dàn ý và bản đồ, để người học đọc một lần là hiểu ở mọi nơi.
//
// Mức hiểu đến từ KẾT QUẢ CHẤM (backend domain/progress.py), không từ việc đã
// mở trang ra xem: "đã hiểu" trên màn hình đúng bằng đỉnh sáng trên bản đồ.

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { studentId } from "./useSession";

export const LEVELS = {
  moi: { label: "Chưa học", hint: "Chưa giảng trang này lần nào" },
  dang_hoc: { label: "Đang học", hint: "Đã thử giảng, học trò chưa hiểu hết" },
  can_sua: { label: "Cần sửa", hint: "Lần gần nhất bạn giảng sai chỗ này" },
  da_hieu: { label: "Đã hiểu", hint: "Học trò đã hiểu nhờ lời bạn" },
  vung: { label: "Vững", hint: "Giảng được ở ít nhất hai buổi khác nhau" },
};

/** Thứ tự đọc từ "cần làm ngay" tới "đã xong" — dùng cho chú thích và thống kê. */
export const LEVEL_ORDER = ["can_sua", "dang_hoc", "da_hieu", "vung"];

/** Chấm mức hiểu. Đơn sắc, không icon: độ đặc của chấm nói lên độ vững.
 *  Chưa học thì không vẽ gì — danh sách sạch, mắt chỉ dừng ở chỗ đã có gì đó. */
export function LevelDot({ level, size = 8, className = "" }) {
  if (!level || level === "moi") return null;
  const s = { width: size, height: size };
  const common = `relative inline-block shrink-0 rounded-full ${className}`;
  const title = LEVELS[level]?.label;
  if (level === "dang_hoc") return <span title={title} style={s} className={`${common} bg-neutral-300`} />;
  if (level === "can_sua")
    return <span title={title} style={s} className={`${common} bg-white ring-[1.5px] ring-neutral-900 ring-inset`} />;
  if (level === "vung")
    return (
      <span
        title={title}
        style={s}
        className={`${common} bg-neutral-900 outline-[1.5px] outline-offset-[1.5px] outline-neutral-900 outline`}
      />
    );
  return <span title={title} style={s} className={`${common} bg-neutral-900`} />;
}

/** Nhãn chữ kèm chấm — dùng khi có chỗ, để không ai phải nhớ quy ước chấm. */
export function LevelTag({ level, className = "" }) {
  if (!level || level === "moi") return null;
  const dam = level === "can_sua" || level === "da_hieu" || level === "vung";
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[12px] ${dam ? "font-medium text-neutral-900" : "text-neutral-500"} ${className}`}
    >
      <LevelDot level={level} />
      {LEVELS[level].label}
    </span>
  );
}

export function LevelLegend({ className = "" }) {
  return (
    <dl className={`m-0 flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-neutral-500 ${className}`}>
      {LEVEL_ORDER.map((k) => (
        <div key={k} className="flex items-center gap-1.5" title={LEVELS[k].hint}>
          <LevelDot level={k} />
          <dt className="m-0">{LEVELS[k].label}</dt>
        </div>
      ))}
    </dl>
  );
}

/** Thanh tiến độ chia theo mức: phần đậm là đã hiểu/vững, nhạt là đang học. */
export function ProgressBar({ levels, total, className = "" }) {
  const t = Math.max(total || 0, 1);
  const hieu = (levels?.da_hieu ?? 0) + (levels?.vung ?? 0);
  const phan = [
    ["vung", levels?.vung ?? 0, "bg-neutral-900"],
    ["da_hieu", levels?.da_hieu ?? 0, "bg-neutral-700"],
    ["can_sua", levels?.can_sua ?? 0, "bg-neutral-400"],
    ["dang_hoc", levels?.dang_hoc ?? 0, "bg-neutral-300"],
  ];
  return (
    <span className={`flex items-center gap-2.5 ${className}`}>
      <span
        className="flex h-1.5 flex-1 overflow-hidden rounded-full bg-neutral-200"
        role="img"
        aria-label={`${hieu} trên ${total} trang đã hiểu`}
      >
        {phan.map(([k, n, mau]) =>
          n > 0 ? (
            <span
              key={k}
              title={`${LEVELS[k].label}: ${n}`}
              className={`${mau} h-full transition-[width] duration-700`}
              style={{ width: `${(100 * n) / t}%` }}
            />
          ) : null,
        )}
      </span>
      <span className="shrink-0 text-[12px] tabular-nums text-neutral-500">
        {hieu}/{total || "…"}
      </span>
    </span>
  );
}

/** Tiến độ của học viên, tải từ server — đổi máy vẫn còn nguyên. */
export function useProgress() {
  const [data, setData] = useState(null);
  const reload = useCallback(() => {
    api(`/progress?student_id=${encodeURIComponent(studentId())}`)
      .then(setData)
      .catch(() => setData((d) => d ?? { summary: {}, decks: {}, recent: [] }));
  }, []);
  useEffect(() => {
    reload();
  }, [reload]);
  return [data, reload];
}

/** "3 phút trước", "hôm qua" — mốc thời gian đọc được bằng mắt. */
export function timeAgo(iso) {
  if (!iso) return "";
  const giay = (Date.now() - new Date(iso).getTime()) / 1000;
  if (giay < 60) return "vừa xong";
  if (giay < 3600) return `${Math.floor(giay / 60)} phút trước`;
  if (giay < 86400) return `${Math.floor(giay / 3600)} giờ trước`;
  if (giay < 172800) return "hôm qua";
  return `${Math.floor(giay / 86400)} ngày trước`;
}
