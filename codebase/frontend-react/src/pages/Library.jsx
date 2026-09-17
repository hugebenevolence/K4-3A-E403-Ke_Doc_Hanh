// Thư viện: chọn bài, rồi chọn trang để vào giảng.
//
// Thẻ mang ảnh thu nhỏ của chính trang slide và tiêu đề thật của nó — học viên
// tìm lại chỗ mình nhớ bằng mắt ("cái slide có sơ đồ vòng tròn") nhanh hơn
// bằng số trang. Trang nào đã giảng được thì đánh dấu, để biết còn lại bao nhiêu.

import { motion, useInView } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { lastPage, taughtPages } from "../decks";
import { EASE } from "../motion";
import { deckDocument } from "../pdf";
import { Brand, LinkButton } from "../site";

/** Bỏ dấu để gõ "chi so" vẫn tìm ra "chỉ số". */
function fold(text) {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase();
}

export default function Library() {
  const { member, logout } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [decks, setDecks] = useState(null);
  const [outlines, setOutlines] = useState({});
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    api("/decks")
      .then(async (list) => {
        if (cancelled) return;
        setDecks(list);
        const rows = await Promise.all(list.map((d) => api(`/decks/${encodeURIComponent(d.slug)}/outline`)));
        if (!cancelled) setOutlines(Object.fromEntries(list.map((d, i) => [d.slug, rows[i]])));
      })
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const active = decks?.find((d) => d.slug === params.get("deck")) ?? decks?.[0];
  const rows = useMemo(() => {
    const all = (active && outlines[active.slug]) || [];
    const q = fold(query.trim());
    return q ? all.filter((row) => fold(`${row.page} ${row.title}`).includes(q)) : all;
  }, [active, outlines, query]);

  return (
    <div className="min-h-screen bg-white font-sans text-neutral-900 antialiased">
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <Brand />
          <div className="ml-auto flex items-center gap-1">
            <LinkButton to="/graph" variant="quiet">
              Bản đồ
            </LinkButton>
            {member?.name && (
              <span className="mr-1 flex items-center gap-2 text-[13px] text-neutral-600">
                <span className="grid size-7 place-items-center rounded-full bg-neutral-100 text-[12px] font-semibold uppercase text-neutral-700">
                  {member.name.slice(0, 1)}
                </span>
                <span className="hidden sm:inline">{member.name}</span>
              </span>
            )}
            {member?.auth && (
              <button
                onClick={() => {
                  logout();
                  navigate("/");
                }}
                className="h-8 rounded-lg px-2.5 text-[13px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
              >
                Đăng xuất
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pt-10 pb-24 sm:px-6 sm:pt-12">
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.03em] sm:text-[32px]">Thư viện</h1>
        {/* Không gian giảng bài là ba cột; trên điện thoại chỉ duyệt được. */}
        <p className="m-0 mt-1 text-[14px] text-neutral-500 lg:hidden">Nên dùng máy tính để giảng bài.</p>

        {error && <p className="mt-10 text-[14px] text-neutral-500">{error}</p>}
        {decks && decks.length === 0 && (
          <p className="mt-10 text-[14px] text-neutral-500">Chưa có bài học nào trên máy chủ.</p>
        )}
        {!decks && !error && <SkeletonGrid />}

        {active && (
          <>
            <div className="mt-8 grid gap-3 md:grid-cols-2">
              {decks.map((deck, i) => (
                <DeckCard
                  key={deck.slug}
                  deck={deck}
                  index={i}
                  selected={deck.slug === active.slug}
                  onSelect={() => {
                    setQuery("");
                    setParams({ deck: deck.slug }, { replace: true });
                  }}
                />
              ))}
            </div>

            <div className="mt-10 flex flex-col-reverse gap-3 sm:flex-row sm:items-center">
              <input
                // type="text" chứ không "search": nút xoá mặc định của trình
                // duyệt có màu xanh, lạc giữa giao diện đơn sắc.
                type="text"
                enterKeyHint="search"
                aria-label="Tìm slide"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Tìm slide"
                className="h-10 w-full rounded-lg border border-neutral-200 bg-white px-3.5 text-[14px] outline-none transition-shadow placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-4 focus:ring-neutral-900/5 sm:w-72"
              />
              <ResumeButton deck={active} />
            </div>

            <SlideGrid key={active.slug} deck={active} rows={rows} loading={!outlines[active.slug]} query={query} />
          </>
        )}
      </main>
    </div>
  );
}

function DeckCard({ deck, index, selected, onSelect }) {
  const taught = taughtPages(deck.slug).size;
  return (
    <motion.button
      initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.5, delay: index * 0.06, ease: EASE }}
      onClick={onSelect}
      aria-pressed={selected}
      className={`flex items-center gap-4 rounded-2xl border bg-white p-3 text-left transition-colors ${
        selected ? "border-neutral-900 ring-1 ring-neutral-900" : "border-neutral-200 hover:border-neutral-400"
      }`}
    >
      <span className="relative aspect-video w-28 shrink-0 overflow-hidden rounded-lg bg-neutral-100 ring-1 ring-neutral-200 sm:w-36">
        <Thumb slug={deck.slug} page={1} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-semibold tracking-tight">{deck.title}</span>
        {deck.subtitle && (
          <span className="mt-0.5 line-clamp-2 block text-[13px] leading-snug text-neutral-500">{deck.subtitle}</span>
        )}
        <span className="mt-2.5 flex items-center gap-2.5">
          <span className="h-1 flex-1 overflow-hidden rounded-full bg-neutral-200">
            <motion.span
              className="block h-full rounded-full bg-neutral-900"
              initial={{ width: 0 }}
              animate={{ width: `${(100 * taught) / Math.max(deck.pages, 1)}%` }}
              transition={{ duration: 0.8, delay: 0.2 + index * 0.06, ease: EASE }}
            />
          </span>
          <span className="text-[12px] tabular-nums text-neutral-500">
            {taught}/{deck.pages}
          </span>
        </span>
      </span>
    </motion.button>
  );
}

function ResumeButton({ deck }) {
  const resume = lastPage(deck.slug);
  return (
    <LinkButton to={`/learn/${encodeURIComponent(deck.slug)}?page=${resume || 1}`} className="sm:ml-auto">
      {resume ? `Học tiếp slide ${resume}` : "Bắt đầu từ slide 1"}
    </LinkButton>
  );
}

function SlideGrid({ deck, rows, loading, query }) {
  const resume = lastPage(deck.slug);
  const taught = useMemo(() => taughtPages(deck.slug), [deck.slug]);

  if (loading) return <SkeletonGrid />;
  if (!rows.length) {
    return <p className="mt-12 text-center text-[14px] text-neutral-500">Không có slide nào khớp “{query}”.</p>;
  }
  return (
    <div className="mt-6 grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {rows.map((row, i) => (
        <motion.div
          key={row.page}
          initial={{ opacity: 0, y: 10, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.5, delay: Math.min(i, 12) * 0.03, ease: EASE }}
        >
          <Link to={`/learn/${encodeURIComponent(deck.slug)}?page=${row.page}`} className="group block">
            <div className="relative aspect-video overflow-hidden rounded-xl bg-neutral-100 ring-1 ring-neutral-200 transition duration-300 group-hover:-translate-y-0.5 group-hover:shadow-[0_16px_40px_-20px_rgb(0_0_0/0.3)] group-hover:ring-neutral-900">
              <Thumb slug={deck.slug} page={row.page} />
            </div>
            <p className="m-0 mt-3 flex items-center justify-between text-[12px] tabular-nums text-neutral-400">
              Slide {row.page}
              {taught.has(row.page) ? (
                <span className="flex items-center gap-1.5 font-medium text-neutral-900">
                  <span className="size-1.5 rounded-full bg-neutral-900" />
                  Đã giảng
                </span>
              ) : (
                row.page === resume && <span className="text-neutral-500">Mở gần nhất</span>
              )}
            </p>
            <p className="m-0 mt-0.5 line-clamp-2 text-[14px] leading-snug font-medium text-neutral-900">
              {row.title || `Slide ${row.page}`}
            </p>
          </Link>
        </motion.div>
      ))}
    </div>
  );
}

/** Ảnh thu nhỏ của một trang slide, chỉ vẽ khi sắp cuộn tới. */
function Thumb({ slug, page }) {
  const canvas = useRef(null);
  const inView = useInView(canvas, { once: true, margin: "300px 0px" });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!inView) return;
    let cancelled = false;
    let task = null;
    deckDocument(slug)
      .then((doc) => doc.getPage(page))
      .then((pdfPage) => {
        const el = canvas.current;
        if (cancelled || !el) return;
        const base = pdfPage.getViewport({ scale: 1 });
        const width = el.clientWidth || 320;
        const viewport = pdfPage.getViewport({ scale: (width * Math.min(devicePixelRatio, 2)) / base.width });
        el.width = viewport.width;
        el.height = viewport.height;
        task = pdfPage.render({ canvasContext: el.getContext("2d"), viewport });
        return task.promise.then(() => !cancelled && setReady(true));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [inView, slug, page]);

  return (
    <>
      {!ready && <span className="absolute inset-0 animate-pulse bg-neutral-100" />}
      <canvas
        ref={canvas}
        className={`block h-full w-full object-contain transition-opacity duration-500 ${ready ? "opacity-100" : "opacity-0"}`}
      />
    </>
  );
}

function SkeletonGrid() {
  return (
    <div className="mt-8 grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }, (_, i) => (
        <div key={i}>
          <div className="aspect-video animate-pulse rounded-xl bg-neutral-100" />
          <div className="mt-3 h-2.5 w-12 animate-pulse rounded-full bg-neutral-100" />
          <div className="mt-2 h-3 w-3/4 animate-pulse rounded-full bg-neutral-100" />
        </div>
      ))}
    </div>
  );
}
