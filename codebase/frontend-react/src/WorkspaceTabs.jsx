// Hai tab của không gian học: đang ở slide nào, và nó nằm đâu trên bản đồ.
//
// Học viên chuyển qua lại giữa giảng từng trang và nhìn toàn cảnh; không có
// tab thì bản đồ là một trang riêng, vào rồi không biết đường quay lại đúng
// slide vừa giảng. Tab Slide luôn nhớ trang cuối cùng, tab Bản đồ luôn biết
// mình vừa từ trang nào sang để đánh dấu "bạn đang ở đây".

import { LayoutGroup, motion } from "motion/react";
import { Link } from "react-router";
import { lastPage } from "./decks";
import { EASE } from "./motion";

export default function WorkspaceTabs({ active, deck, page, className = "" }) {
  const trang = page || (deck ? lastPage(deck) : null) || 1;
  const tabs = [
    {
      key: "slide",
      label: "Slide",
      to: deck ? `/learn/${encodeURIComponent(deck)}?page=${trang}` : "/library",
    },
    {
      key: "graph",
      label: "Bản đồ",
      to: deck ? `/graph?deck=${encodeURIComponent(deck)}&page=${trang}` : "/graph",
    },
  ];
  return (
    <LayoutGroup id="workspace-tabs">
      <nav
        aria-label="Chuyển giữa slide và bản đồ"
        className={`inline-flex items-center rounded-lg bg-neutral-100 p-0.5 ${className}`}
      >
        {tabs.map((t) => {
          const on = t.key === active;
          return (
            <Link
              key={t.key}
              to={t.to}
              aria-current={on ? "page" : undefined}
              className={`relative rounded-md px-3 py-1 text-[12.5px] font-medium whitespace-nowrap transition-colors ${
                on ? "text-neutral-900" : "text-neutral-500 hover:text-neutral-900"
              }`}
            >
              {on && (
                <motion.span
                  layoutId="workspace-tab"
                  className="absolute inset-0 rounded-md bg-white shadow-sm ring-1 ring-neutral-200"
                  transition={{ duration: 0.3, ease: EASE }}
                />
              )}
              <span className="relative">{t.label}</span>
            </Link>
          );
        })}
      </nav>
    </LayoutGroup>
  );
}
