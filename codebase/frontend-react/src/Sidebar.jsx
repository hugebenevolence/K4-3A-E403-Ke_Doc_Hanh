// Thanh bên trái: tab Slide | Bản đồ, bài đang học, tiến độ, và dàn ý slide.
//
// Mỗi dòng mang tiêu đề thật của trang chứ không chỉ số trang — học viên tìm
// lại chỗ mình nhớ theo nội dung, không theo số. Chấm cuối dòng là MỨC HIỂU của
// trang đó (spec §4c tự khai "chưa có lớp phủ trạng thái trên dàn ý" — đây là
// lớp phủ đó), cùng ngôn ngữ chấm với thư viện và bản đồ.

import { LayoutGroup, motion } from "motion/react";
import { Link } from "react-router";
import { EASE } from "./motion";
import { LEVELS, LevelDot, ProgressBar } from "./progress";
import WorkspaceTabs from "./WorkspaceTabs";

export default function Sidebar({ deck, outline, pages, page, teachingPages, progress, onPage }) {
  const rows = outline.length ? outline : Array.from({ length: pages }, (_, i) => ({ page: i + 1, title: "" }));
  const levelOf = (p) => progress?.pages?.[p]?.level;

  return (
    <aside className="flex min-h-0 flex-col border-r border-neutral-200 bg-neutral-50/70">
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-neutral-200 px-3">
        <Link
          to="/library"
          title="Về thư viện"
          className="rounded-md px-1.5 py-1 text-[13px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        >
          ← Thư viện
        </Link>
        <WorkspaceTabs active="slide" deck={deck.slug} page={page} className="ml-auto" />
      </div>

      <div className="px-4 pt-4 pb-3">
        <p className="m-0 line-clamp-2 text-[14px] leading-snug font-semibold tracking-tight text-neutral-900">
          {deck.title}
        </p>
        <ProgressBar levels={progress?.levels} total={progress?.teachable} className="mt-2.5" />
        <p className="m-0 mt-1 text-[11px] text-neutral-400">trang đã hiểu / trang giảng được</p>
      </div>

      <LayoutGroup id="slides">
        <ol className="m-0 min-h-0 flex-1 list-none overflow-y-auto px-2 pb-3">
          {rows.map((row) => {
            const active = row.page === page;
            const teaching = teachingPages.has(row.page);
            const level = levelOf(row.page);
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
                  {/* Đang giảng: vòng nhấp nháy. Còn lại: chấm mức hiểu. */}
                  {teaching ? (
                    <motion.span
                      className="relative size-2 shrink-0 rounded-full ring-[1.5px] ring-neutral-900"
                      title="Đang giảng"
                      animate={{ opacity: [1, 0.35, 1] }}
                      transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                    />
                  ) : (
                    <span className="relative flex w-3 shrink-0 justify-center" title={LEVELS[level]?.label}>
                      <LevelDot level={level} />
                    </span>
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
