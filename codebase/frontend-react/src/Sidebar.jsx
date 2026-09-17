// Thanh bên trái: bài đang học và dàn ý slide.
//
// Mỗi dòng mang tiêu đề thật của trang ("Giới hạn bẩm sinh…") chứ không chỉ
// số trang — học viên tìm lại chỗ mình nhớ theo nội dung, không theo số.

import { LayoutGroup, motion } from "motion/react";
import { useState } from "react";
import { Link } from "react-router";
import { EASE } from "./motion";
import { Eyebrow, Kbd } from "./ui";

const FILTERS = [
  { id: "all", label: "Tất cả" },
  { id: "teaching", label: "Đang dạy" },
];

export default function Sidebar({ deck, outline, pages, page, teachingPages, onPage }) {
  const [filter, setFilter] = useState("all");

  const rows = (outline.length ? outline : Array.from({ length: pages }, (_, i) => ({ page: i + 1, title: "" })))
    .filter((row) => filter === "all" || teachingPages.has(row.page));

  return (
    <aside className="flex min-h-0 flex-col border-r border-neutral-200 bg-neutral-50/70">
      <div className="flex items-center gap-2.5 px-4 pt-4 pb-3">
        {/* Chữ lồng thay cho logo: đơn sắc, không phải một icon trang trí. */}
        <Link to="/" className="flex min-w-0 flex-1 items-center gap-2.5">
          <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-neutral-900 text-[13px] font-semibold text-white">
            G
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block text-[13px] font-semibold text-neutral-900">Giảng lại</span>
            <span className="block truncate text-[11px] text-neutral-500">cho học trò AI</span>
          </span>
        </Link>
      </div>

      <Link
        to="/library"
        className="group mx-3 block rounded-xl border border-neutral-200 bg-white px-3 py-2.5 transition-colors hover:border-neutral-300"
      >
        <span className="flex items-center justify-between">
          <Eyebrow>Bài đang học</Eyebrow>
          <span className="text-[11px] text-neutral-400 transition-colors group-hover:text-neutral-900">
            Đổi bài
          </span>
        </span>
        <span className="mt-0.5 block truncate text-[13px] font-medium text-neutral-900">{deck.title}</span>
        <span className="block text-[11px] text-neutral-500">{pages || "…"} slide</span>
      </Link>

      <LayoutGroup id="filter">
        <div className="mx-3 mt-3 grid grid-cols-2 rounded-lg bg-neutral-200/60 p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className="relative h-7 rounded-md text-[12px] font-medium text-neutral-600 aria-pressed:text-neutral-900"
              aria-pressed={filter === f.id}
            >
              {filter === f.id && (
                <motion.span
                  layoutId="filter-pill"
                  className="absolute inset-0 rounded-md bg-white shadow-sm ring-1 ring-neutral-200"
                  transition={{ duration: 0.3, ease: EASE }}
                />
              )}
              <span className="relative">{f.label}</span>
            </button>
          ))}
        </div>
      </LayoutGroup>

      <Eyebrow className="px-4 pt-4 pb-1.5">Slide</Eyebrow>
      <LayoutGroup id="slides">
        <ol className="m-0 min-h-0 flex-1 list-none overflow-y-auto px-2 pb-3">
          {rows.map((row) => {
            const active = row.page === page;
            return (
              <li key={row.page}>
                <button
                  onClick={() => onPage(row.page)}
                  className={`relative flex w-full items-start gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] transition-colors ${
                    active ? "text-neutral-900" : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                  }`}
                >
                  {/* Nền của dòng đang chọn trượt theo khi đổi trang, thay vì
                      nháy tắt chỗ cũ bật chỗ mới — mắt theo được mình vừa đi
                      từ đâu tới đâu. */}
                  {active && (
                    <motion.span
                      layoutId="slide-active"
                      className="absolute inset-0 rounded-lg bg-white shadow-sm ring-1 ring-neutral-200"
                      transition={{ duration: 0.35, ease: EASE }}
                    />
                  )}
                  <span className="relative w-5 shrink-0 pt-px text-right text-[11px] tabular-nums text-neutral-400">
                    {row.page}
                  </span>
                  <span className="relative min-w-0 flex-1 truncate">
                    {row.title || `Slide ${row.page}`}
                  </span>
                  {teachingPages.has(row.page) && (
                    <span
                      className="relative mt-1.5 size-1.5 shrink-0 rounded-full bg-neutral-900"
                      aria-label="đang dạy"
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ol>
      </LayoutGroup>

      <div className="space-y-1.5 border-t border-neutral-200 px-4 py-3 text-[11px] text-neutral-500">
        <p className="m-0 flex items-center justify-between">
          Giữ để nói <Kbd>Space</Kbd>
        </p>
        <p className="m-0 flex items-center justify-between">
          Lật slide
          <span className="flex gap-1">
            <Kbd>←</Kbd>
            <Kbd>→</Kbd>
          </span>
        </p>
        <p className="m-0 flex items-center justify-between">
          Vùng đang dạy <Kbd>F</Kbd>
        </p>
      </div>
    </aside>
  );
}
