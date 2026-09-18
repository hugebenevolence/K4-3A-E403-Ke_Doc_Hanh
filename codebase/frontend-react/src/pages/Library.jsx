// Thư viện: hành trình học, chọn bài, rồi chọn trang để vào giảng.
//
// Hai cột: bên trái là danh sách bộ slide gom theo ngày, bên phải là bộ đang
// chọn. Với 28 bộ slide, bố cục thẻ cũ bắt học viên cuộn qua 28 thẻ mới tới
// được lưới slide, và mỗi thẻ vẽ ảnh trang đầu — tức là tải về 28 file PDF, có
// file 25 MB, chỉ để hiện ảnh nhỏ. Danh sách gọn không tải PDF nào.
//
// Ảnh thu nhỏ chỉ còn ở lưới slide của bộ đang chọn: học viên tìm lại chỗ mình
// nhớ bằng mắt ("cái slide có sơ đồ vòng tròn") nhanh hơn bằng số trang.

import { AnimatePresence, motion, useInView } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { lastPage } from "../decks";
import { EASE } from "../motion";
import { deckDocument } from "../pdf";
import { LEVEL_ORDER, LEVELS, LevelDot, LevelLegend, LevelTag, ProgressBar, timeAgo, useProgress } from "../progress";
import { Brand, LinkButton } from "../site";

/** Bỏ dấu để gõ "chi so" vẫn tìm ra "chỉ số". */
function fold(text) {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase();
}

/** "Day 2 · Xác định bài toán" → nhóm "Day 2". Tiêu đề không có dấu · thì vào "Khác". */
function nhomCua(deck) {
  const [dau, sau] = deck.title.split(" · ");
  return sau ? dau : "Khác";
}

export default function Library() {
  const { member, logout } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [decks, setDecks] = useState(null);
  const [outline, setOutline] = useState({});
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [progress] = useProgress();

  useEffect(() => {
    let cancelled = false;
    api("/decks")
      .then((list) => !cancelled && setDecks(list))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const active = decks?.find((d) => d.slug === params.get("deck")) ?? decks?.[0];

  // Dàn ý chỉ tải cho bộ đang chọn — 28 bộ mà tải hết một lúc là 28 lần đọc PDF.
  useEffect(() => {
    if (!active || outline[active.slug]) return;
    let cancelled = false;
    api(`/decks/${encodeURIComponent(active.slug)}/outline`)
      .then((rows) => !cancelled && setOutline((o) => ({ ...o, [active.slug]: rows })))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [active, outline]);

  const nhom = useMemo(() => {
    const m = new Map();
    for (const d of decks ?? []) m.set(nhomCua(d), [...(m.get(nhomCua(d)) ?? []), d]);
    return [...m.entries()];
  }, [decks]);

  const rows = useMemo(() => {
    const all = (active && outline[active.slug]) || [];
    const q = fold(query.trim());
    return q ? all.filter((row) => fold(`${row.page} ${row.title}`).includes(q)) : all;
  }, [active, outline, query]);

  const tieuDe = useMemo(() => new Map((decks ?? []).map((d) => [d.slug, d.title])), [decks]);
  const chon = (slug) => {
    setQuery("");
    setParams({ deck: slug }, { replace: true });
  };

  return (
    <div className="min-h-screen bg-white font-sans text-neutral-900 antialiased">
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
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

      <main className="mx-auto max-w-7xl px-4 pt-8 pb-24 sm:px-6">
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.03em] sm:text-[32px]">Thư viện</h1>
        {/* Không gian giảng bài là ba cột; trên điện thoại chỉ duyệt được. */}
        <p className="m-0 mt-1 text-[14px] text-neutral-500 lg:hidden">Nên dùng máy tính để giảng bài.</p>

        {progress && decks && <HanhTrinh progress={progress} tieuDe={tieuDe} />}

        {error && <p className="mt-10 text-[14px] text-neutral-500">{error}</p>}
        {decks && decks.length === 0 && (
          <p className="mt-10 text-[14px] text-neutral-500">Chưa có bài học nào trên máy chủ.</p>
        )}
        {!decks && !error && <SkeletonGrid />}

        {active && (
          <div className="mt-8 grid gap-8 lg:grid-cols-[300px_minmax(0,1fr)]">
            <nav aria-label="Các bộ slide" className="lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
              {nhom.map(([ten, ds]) => (
                <div key={ten} className="mb-4">
                  <p className="m-0 mb-1 px-2 text-[11px] font-medium tracking-wide text-neutral-400 uppercase">{ten}</p>
                  <ul className="m-0 list-none space-y-0.5 p-0">
                    {ds.map((d) => (
                      <li key={d.slug}>
                        <DeckRow
                          deck={d}
                          selected={d.slug === active.slug}
                          progress={progress?.decks?.[d.slug]}
                          onSelect={() => chon(d.slug)}
                        />
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>

            <section className="min-w-0">
              <DeckHeader deck={active} progress={progress?.decks?.[active.slug]} />
              <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center">
                <input
                  // type="text" chứ không "search": nút xoá mặc định của trình
                  // duyệt có màu xanh, lạc giữa giao diện đơn sắc.
                  type="text"
                  enterKeyHint="search"
                  aria-label="Tìm slide"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Tìm slide trong bộ này"
                  className="h-10 w-full rounded-lg border border-neutral-200 bg-white px-3.5 text-[14px] outline-none transition-shadow placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-4 focus:ring-neutral-900/5 sm:w-72"
                />
                <LevelLegend className="sm:ml-auto" />
              </div>
              <SlideGrid
                key={active.slug}
                deck={active}
                rows={rows}
                loading={!outline[active.slug]}
                query={query}
                levels={progress?.decks?.[active.slug]?.pages ?? {}}
              />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

/** Hành trình học: đã tới đâu, chỗ nào đang cần sửa, vừa học gì. */
function HanhTrinh({ progress, tieuDe }) {
  const tong = LEVEL_ORDER.reduce((n, k) => n + (progress.summary?.[k] ?? 0), 0);
  const canSua = Object.entries(progress.decks ?? {}).flatMap(([slug, d]) =>
    Object.entries(d.pages)
      .filter(([, v]) => v.level === "can_sua")
      .map(([page]) => ({ slug, page: Number(page) })),
  );

  if (!tong) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="mt-6 rounded-2xl border border-neutral-200 p-4"
      >
        <p className="m-0 text-[14px] font-medium">Hành trình học của bạn bắt đầu ở đây</p>
        <p className="m-0 mt-1 text-[13px] text-neutral-500">
          Chọn một bộ slide, giảng một trang cho học trò. Mỗi trang bạn giảng sẽ được ghi lại theo mức hiểu:
        </p>
        <LevelLegend className="mt-3" />
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="mt-6 grid gap-5 rounded-2xl border border-neutral-200 p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]"
    >
      <div>
        <p className="m-0 text-[14px] font-medium">Hành trình học của bạn</p>
        <dl className="m-0 mt-3 grid grid-cols-2 gap-2">
          {[...LEVEL_ORDER].reverse().map((k) => (
            <div key={k} className="rounded-xl bg-neutral-50 px-3 py-2" title={LEVELS[k].hint}>
              <dd className="m-0 text-[22px] font-semibold tracking-tight tabular-nums">
                {progress.summary?.[k] ?? 0}
              </dd>
              <dt className="m-0 flex items-center gap-1.5 text-[12px] text-neutral-500">
                <LevelDot level={k} />
                {LEVELS[k].label}
              </dt>
            </div>
          ))}
        </dl>
      </div>

      <div className="min-w-0">
        {canSua.length > 0 && (
          <div className="mb-3 rounded-xl border border-neutral-900 px-3 py-2.5">
            <p className="m-0 text-[13px] font-medium">
              Có {canSua.length} trang bạn từng giảng sai — giảng lại để sửa hiểu lầm
            </p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {canSua.slice(0, 4).map(({ slug, page }) => (
                <Link
                  key={`${slug}:${page}`}
                  to={`/learn/${encodeURIComponent(slug)}?page=${page}`}
                  className="rounded-md bg-neutral-100 px-2 py-1 text-[12px] text-neutral-800 transition-colors hover:bg-neutral-200"
                >
                  {tieuDe.get(slug)?.split(" · ")[0]} · tr. {page}
                </Link>
              ))}
            </div>
          </div>
        )}
        <p className="m-0 text-[12px] font-medium tracking-wide text-neutral-400 uppercase">Gần đây</p>
        <ul className="m-0 mt-1.5 list-none space-y-0.5 p-0">
          {progress.recent.slice(0, 5).map((r) => (
            <li key={`${r.deck}:${r.page}`}>
              <Link
                to={`/learn/${encodeURIComponent(r.deck)}?page=${r.page}`}
                className="group flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-neutral-50"
              >
                <span className="flex w-3 shrink-0 justify-center">
                  <LevelDot level={r.level} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium text-neutral-900">{r.title}</span>
                  <span className="block truncate text-[12px] text-neutral-500">
                    {tieuDe.get(r.deck)} · trang {r.page}
                  </span>
                </span>
                <span className="shrink-0 text-right text-[11px] text-neutral-400">
                  {LEVELS[r.level]?.label}
                  <span className="block">{timeAgo(r.at)}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}

function DeckRow({ deck, selected, progress, onSelect }) {
  const hieu = (progress?.levels?.da_hieu ?? 0) + (progress?.levels?.vung ?? 0);
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={`relative w-full rounded-xl px-2.5 py-2 text-left transition-colors ${
        selected ? "bg-neutral-900 text-white" : "hover:bg-neutral-100"
      }`}
    >
      <span className="block truncate text-[13px] font-medium">{deck.title.split(" · ").slice(1).join(" · ") || deck.title}</span>
      <span className={`mt-0.5 flex items-center gap-2 text-[11px] ${selected ? "text-white/60" : "text-neutral-500"}`}>
        <span className="min-w-0 flex-1 truncate">{deck.subtitle || `${deck.pages} trang`}</span>
        {progress && (
          <span className="shrink-0 tabular-nums">
            {hieu}/{progress.teachable}
          </span>
        )}
      </span>
    </button>
  );
}

function DeckHeader({ deck, progress }) {
  const resume = lastPage(deck.slug);
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={deck.slug}
        initial={{ opacity: 0, y: 6, filter: "blur(4px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        exit={{ opacity: 0, y: -4, filter: "blur(4px)" }}
        transition={{ duration: 0.3, ease: EASE }}
        className="flex flex-col gap-4 sm:flex-row sm:items-end"
      >
        <div className="min-w-0 flex-1">
          <p className="m-0 text-[12px] font-medium tracking-wide text-neutral-400 uppercase">{nhomCua(deck)}</p>
          <h2 className="m-0 mt-0.5 text-[22px] leading-tight font-semibold tracking-tight">
            {deck.title.split(" · ").slice(1).join(" · ") || deck.title}
          </h2>
          {deck.subtitle && <p className="m-0 mt-1 text-[13px] text-neutral-500">{deck.subtitle}</p>}
          <ProgressBar
            levels={progress?.levels}
            total={progress?.teachable ?? deck.pages}
            className="mt-3 max-w-md"
          />
        </div>
        <LinkButton to={`/learn/${encodeURIComponent(deck.slug)}?page=${resume || 1}`}>
          {resume ? `Học tiếp slide ${resume}` : "Bắt đầu từ slide 1"}
        </LinkButton>
      </motion.div>
    </AnimatePresence>
  );
}

function SlideGrid({ deck, rows, loading, query, levels }) {
  const resume = lastPage(deck.slug);

  if (loading) return <SkeletonGrid />;
  if (!rows.length) {
    return <p className="mt-12 text-center text-[14px] text-neutral-500">Không có slide nào khớp “{query}”.</p>;
  }
  return (
    <div className="mt-6 grid grid-cols-1 gap-x-5 gap-y-8 sm:grid-cols-2 xl:grid-cols-3">
      {rows.map((row, i) => {
        const level = levels[row.page]?.level;
        return (
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
                {level ? (
                  <LevelTag level={level} />
                ) : (
                  row.page === resume && <span className="text-neutral-500">Mở gần nhất</span>
                )}
              </p>
              <p className="m-0 mt-0.5 line-clamp-2 text-[14px] leading-snug font-medium text-neutral-900">
                {row.title || `Slide ${row.page}`}
              </p>
            </Link>
          </motion.div>
        );
      })}
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
