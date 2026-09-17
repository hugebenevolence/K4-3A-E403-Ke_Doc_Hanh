// Thư viện: chọn bộ slide, rồi chọn trang để vào giảng.
//
// Thẻ mang ảnh thu nhỏ của chính trang slide và tiêu đề thật của nó — học viên
// tìm lại chỗ mình nhớ bằng mắt ("cái slide có sơ đồ vòng tròn") nhanh hơn
// bằng số trang.

import { AnimatePresence, LayoutGroup, motion, useInView } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { lastPage } from "../decks";
import { blurIn, EASE } from "../motion";
import { deckDocument } from "../pdf";
import { Brand, LinkButton } from "../site";

/** Bỏ dấu để tìm "attention" hay "chu y" đều ra "Chú ý". */
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
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <Brand />
          <span className="text-neutral-300">/</span>
          <span className="text-[13px] font-medium text-neutral-600">Thư viện</span>
          <div className="ml-auto flex items-center gap-2">
            {member?.name && (
              <span className="flex items-center gap-2 text-[13px] text-neutral-600">
                <span className="grid size-6 place-items-center rounded-full bg-neutral-100 text-[11px] font-semibold uppercase text-neutral-700 ring-1 ring-neutral-200">
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
                className="h-8 rounded-full px-3 text-[13px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
              >
                Đăng xuất
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pt-10 pb-24 sm:px-6 sm:pt-14">
        <motion.div {...blurIn} transition={{ duration: 0.6, ease: EASE }}>
          <p className="m-0 text-[13px] font-medium text-neutral-400">Thư viện</p>
          <h1 className="m-0 mt-1 text-[32px] leading-tight font-semibold tracking-[-0.03em] sm:text-[40px]">
            Chọn slide để học
          </h1>
          <p className="m-0 mt-2 max-w-xl text-[15px] leading-relaxed text-neutral-500">
            Mở một trang, kéo khung quanh phần muốn giảng, rồi giảng lại cho học trò AI.
          </p>
          {/* Không gian học là ba cột: slide, hội thoại, dàn ý. Trên điện thoại
              vẫn xem được thư viện, nhưng nói trước để khỏi bất ngờ. */}
          <p className="m-0 mt-4 inline-block rounded-lg bg-neutral-100 px-3 py-2 text-[13px] text-neutral-600 lg:hidden">
            Phần giảng bài cần màn hình rộng — mở trên laptop để học thoải mái nhất.
          </p>
        </motion.div>

        {error && <p className="mt-10 text-[14px] text-neutral-500">{error}</p>}
        {decks && decks.length === 0 && (
          <p className="mt-10 text-[14px] text-neutral-500">
            Chưa có bộ slide nào. Đặt SLIDES_DIR trên server trỏ tới thư mục chứa file PDF.
          </p>
        )}

        {decks?.length > 0 && active && (
          <>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
              {decks.length > 1 && (
                <LayoutGroup id="decks">
                  <div className="flex gap-1 overflow-x-auto rounded-full bg-neutral-100 p-1">
                    {decks.map((deck) => {
                      const on = deck.slug === active.slug;
                      return (
                        <button
                          key={deck.slug}
                          onClick={() => setParams({ deck: deck.slug }, { replace: true })}
                          className={`relative h-8 shrink-0 rounded-full px-3.5 text-[13px] font-medium transition-colors ${on ? "text-neutral-900" : "text-neutral-500 hover:text-neutral-900"}`}
                        >
                          {on && (
                            <motion.span
                              layoutId="deck-pill"
                              className="absolute inset-0 rounded-full bg-white shadow-sm ring-1 ring-neutral-200"
                              transition={{ duration: 0.35, ease: EASE }}
                            />
                          )}
                          <span className="relative">{deck.title}</span>
                        </button>
                      );
                    })}
                  </div>
                </LayoutGroup>
              )}
              <input
                // type="text" chứ không "search": nút xoá mặc định của trình
                // duyệt có màu xanh, lạc giữa giao diện đơn sắc.
                type="text"
                enterKeyHint="search"
                aria-label="Tìm slide"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Tìm theo tiêu đề slide"
                className="h-10 w-full rounded-full border border-neutral-200 bg-white px-4 text-[14px] outline-none transition-shadow placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-4 focus:ring-neutral-900/5 sm:ml-auto sm:w-72"
              />
            </div>

            <AnimatePresence mode="wait">
              <motion.section key={active.slug} {...blurIn} className="mt-6">
                <DeckHeader deck={active} />
                <SlideGrid deck={active} rows={rows} loading={!outlines[active.slug]} query={query} />
              </motion.section>
            </AnimatePresence>
          </>
        )}

        {!decks && !error && <SkeletonGrid />}
      </main>
    </div>
  );
}

function DeckHeader({ deck }) {
  const resume = lastPage(deck.slug);
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-neutral-200 p-5 sm:flex-row sm:items-center sm:p-6">
      <div className="min-w-0 flex-1">
        <h2 className="m-0 text-[20px] font-semibold tracking-tight">{deck.title}</h2>
        {deck.subtitle && <p className="m-0 mt-1 text-[14px] text-neutral-500">{deck.subtitle}</p>}
        <p className="m-0 mt-2 text-[12px] text-neutral-400">
          {deck.pages} slide{deck.figures ? ` · ${deck.figures} hình và sơ đồ` : ""}
        </p>
      </div>
      <LinkButton to={`/learn/${encodeURIComponent(deck.slug)}?page=${resume || 1}`} size="lg">
        {resume ? `Học tiếp slide ${resume}` : "Bắt đầu từ slide 1"}
      </LinkButton>
    </div>
  );
}

function SlideGrid({ deck, rows, loading, query }) {
  if (loading) return <SkeletonGrid />;
  if (!rows.length) {
    return <p className="mt-10 text-center text-[14px] text-neutral-500">Không có slide nào khớp “{query}”.</p>;
  }
  const resume = lastPage(deck.slug);
  return (
    <div className="mt-6 grid grid-cols-1 gap-x-5 gap-y-7 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {rows.map((row, i) => (
        <motion.div
          key={row.page}
          initial={{ opacity: 0, y: 10, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.5, delay: Math.min(i, 12) * 0.035, ease: EASE }}
        >
          <Link to={`/learn/${encodeURIComponent(deck.slug)}?page=${row.page}`} className="group block">
            <div className="relative aspect-video overflow-hidden rounded-xl bg-neutral-100 ring-1 ring-neutral-200 transition-all duration-300 group-hover:-translate-y-0.5 group-hover:shadow-[0_16px_40px_-16px_rgb(0_0_0/0.25)] group-hover:ring-neutral-900">
              <Thumb slug={deck.slug} page={row.page} />
              {row.page === resume && (
                <span className="absolute top-2 left-2 rounded-md bg-neutral-900 px-1.5 py-0.5 text-[11px] font-medium text-white">
                  Mở gần nhất
                </span>
              )}
              <span className="absolute right-2 bottom-2 translate-y-1 rounded-full bg-neutral-900 px-2.5 py-1 text-[12px] font-medium text-white opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
                Giảng slide này
              </span>
            </div>
            <p className="m-0 mt-3 text-[12px] tabular-nums text-neutral-400">Slide {row.page}</p>
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
        className={`h-full w-full object-contain transition-opacity duration-500 ${ready ? "opacity-100" : "opacity-0"}`}
      />
    </>
  );
}

function SkeletonGrid() {
  return (
    <div className="mt-6 grid grid-cols-1 gap-x-5 gap-y-7 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
