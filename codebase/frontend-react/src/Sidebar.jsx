// Thanh bên trái: bài đang học, tiến độ, và dàn ý slide.
//
// Mỗi dòng mang tiêu đề thật của trang chứ không chỉ số trang — học viên tìm
// lại chỗ mình nhớ theo nội dung, không theo số.

import { LayoutGroup, motion } from "motion/react";
import { Link } from "react-router";
import { EASE } from "./motion";

export default function Sidebar({ deck, outline, pages, page, teachingPages, taught, onPage }) {
  const rows = outline.length ? outline : Array.from({ length: pages }, (_, i) => ({ page: i + 1, title: "" }));
  const total = pages || rows.length;

  return (
    <aside className="flex min-h-0 flex-col border-r border-neutral-200 bg-neutral-50/70">
      <div className="flex h-12 shrink-0 items-center border-b border-neutral-200 px-4">
        <Link
          to="/library"
          className="-ml-1.5 rounded-md px-1.5 py-1 text-[13px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        >
          ← Thư viện
        </Link>
      </div>

      <div className="px-4 pt-4 pb-3">
        <p className="m-0 line-clamp-2 text-[14px] leading-snug font-semibold tracking-tight text-neutral-900">
          {deck.title}
        </p>
        <div className="mt-2.5 flex items-center gap-2.5">
          <span className="h-1 flex-1 overflow-hidden rounded-full bg-neutral-200">
            <motion.span
              className="block h-full rounded-full bg-neutral-900"
              initial={false}
              animate={{ width: `${(100 * taught.size) / Math.max(total, 1)}%` }}
              transition={{ duration: 0.6, ease: EASE }}
            />
          </span>
          <span className="text-[12px] tabular-nums text-neutral-500">
            {taught.size}/{total || "…"}
          </span>
        </div>
      </div>

      <LayoutGroup id="slides">
        <ol className="m-0 min-h-0 flex-1 list-none overflow-y-auto px-2 pb-3">
          {rows.map((row) => {
            const active = row.page === page;
            const teaching = teachingPages.has(row.page);
            const done = taught.has(row.page);
            return (
              <li key={row.page}>
                <button
                  onClick={() => onPage(row.page)}
                  aria-current={active ? "page" : undefined}
                  className={`relative flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] transition-colors ${
                    active ? "text-neutral-900" : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                  }`}
                >
                  {/* Nền của dòng đang xem trượt theo khi đổi trang — mắt theo
                      được mình vừa đi từ đâu tới đâu. */}
                  {active && (
                    <motion.span
                      layoutId="slide-active"
                      className="absolute inset-0 rounded-lg bg-white shadow-sm ring-1 ring-neutral-200"
                      transition={{ duration: 0.35, ease: EASE }}
                    />
                  )}
                  <span className="relative w-5 shrink-0 text-right text-[11px] tabular-nums text-neutral-400">
                    {row.page}
                  </span>
                  <span className="relative min-w-0 flex-1 truncate">{row.title || `Slide ${row.page}`}</span>
                  {/* Vòng rỗng: đang giảng. Chấm đặc: đã giảng được. */}
                  {teaching ? (
                    <span className="relative size-2 shrink-0 rounded-full ring-[1.5px] ring-neutral-900" title="Đang giảng" />
                  ) : (
                    done && <span className="relative size-2 shrink-0 rounded-full bg-neutral-900" title="Đã giảng" />
                  )}
                </button>
              </li>
            );
          })}
        </ol>
      </LayoutGroup>
    </aside>
  );
}
