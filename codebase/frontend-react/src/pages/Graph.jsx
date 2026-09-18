// Bản đồ hiểu biết — một KHÔNG GIAN toàn màn hình, kiểu Obsidian.
//
// Hai luật, cùng một động từ — "giảng được" (spec §4c): đỉnh sáng là một TRANG
// slide học viên đã giảng được, mang nguyên văn những câu họ nói; cạnh là một
// mối nối họ đã giảng được. Không đỉnh, không cạnh nào do hệ thống suy ra.
//
// Bản đồ là CHỖ LÀM VIỆC, không chỉ để nhìn: đồ thị Obsidian bị chê "mở một lần
// rồi thôi" chính vì không làm được gì trên nó. Ở đây: kéo một trang sáng thả lên
// trang sáng khác là nối hai trang bằng lời; bấm một trang chưa học là đi giảng
// nó; tìm (phím /) là bay tới đúng trang.

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import GraphCanvas from "../GraphCanvas";
import LinkSession from "../LinkSession";
import { blurIn, EASE } from "../motion";
import { LEVELS, LevelDot, LevelLegend, useProgress } from "../progress";
import { Brand } from "../site";
import { Button, Kbd } from "../ui";
import { studentId } from "../useSession";
import WorkspaceTabs from "../WorkspaceTabs";

const TIPS_KEY = "giang-lai-graph-tips";

/** Một cặp chỉ có một cạnh, bất kể chiều — khớp với luật ở backend. */
function khoaCanh(l) {
  return [l.source, l.target].sort().join("|");
}

const isLit = (n) => n?.level === "da_hieu" || n?.level === "vung";

export default function GraphPage() {
  const { member, logout } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const hereDeck = params.get("deck") || "";
  const herePage = Number(params.get("page")) || 0;
  const here = hereDeck && herePage ? `${hereDeck}:${herePage}` : null;

  const [data, setData] = useState(null);
  const [decks, setDecks] = useState([]);
  const [error, setError] = useState("");
  const [progress, reloadProgress] = useProgress();
  const [chon, setChon] = useState(null); // { kind: "node" | "edge", id }
  const [noiTu, setNoiTu] = useState(null); // nối bằng nút: đỉnh gốc
  const [xacNhan, setXacNhan] = useState(null); // nối bằng kéo thả: chờ xác nhận
  const [phien, setPhien] = useState(null); // { a, b } — phiên nối đang mở
  const [canhMoi, setCanhMoi] = useState(null);
  const [query, setQuery] = useState("");
  const [hienMoi, setHienMoi] = useState(true);
  const [tips, setTips] = useState(() => {
    try {
      return localStorage.getItem(TIPS_KEY) !== "1";
    } catch {
      return true;
    }
  });
  const canvas = useRef(null);
  const timKiem = useRef(null);
  const daCo = useRef(null);

  // Tải lại sau mỗi phiên nối, và nhớ những cạnh đã có để biết cạnh nào VỪA
  // sinh ra — cạnh đó được vẽ dần ra thay vì hiện bụp một cái.
  const tai = useCallback(async () => {
    try {
      // Gửi kèm mã học viên của trình duyệt này: khi server KHÔNG bật đăng
      // nhập, phiên giảng ghi đồ thị dưới mã đó, còn API mặc định lại đọc "demo".
      const d = await api(
        `/graph?student_id=${encodeURIComponent(studentId())}&deck=${encodeURIComponent(hereDeck)}`,
      );
      const moi = daCo.current && d.links.map(khoaCanh).find((k) => !daCo.current.has(k));
      daCo.current = new Set(d.links.map(khoaCanh));
      if (moi) setCanhMoi(moi);
      setData(d);
    } catch (e) {
      setError(e.message || "Không tải được bản đồ");
    }
  }, [hereDeck]);

  useEffect(() => {
    tai();
    api("/decks")
      .then(setDecks)
      .catch(() => {});
  }, [tai]);

  const tieuDe = useMemo(() => new Map(decks.map((d) => [d.slug, d.title])), [decks]);
  const deckLabel = useCallback(
    (slug, ngan) => {
      const t = tieuDe.get(slug) || slug;
      return ngan ? t.split(" · ")[0] : t;
    },
    [tieuDe],
  );

  // Đỉnh: trang đã sáng (từ đồ thị) + mọi trang còn giảng được của các bộ đang
  // học (từ vành tối), tô theo mức hiểu (từ tiến độ) — cùng ngôn ngữ chấm với
  // thư viện, nên trang "cần sửa" cũng hiện trên bản đồ.
  const { nodes, links } = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const levelOf = (deck, page) => progress?.decks?.[deck]?.pages?.[page]?.level;
    const sang = data.claims.map((c) => ({
      id: c.concept,
      deck: c.deck,
      page: c.page,
      label: c.label,
      title: c.title,
      said: c.said,
      sentences: c.sentences,
      times_taught: c.times_taught,
      level: levelOf(c.deck, c.page) === "vung" || c.times_taught >= 2 ? "vung" : "da_hieu",
    }));
    const toi = data.dim
      .map((d) => ({
        id: d.concept,
        deck: d.deck,
        page: d.page,
        label: d.label,
        title: d.title,
        level: levelOf(d.deck, d.page) || "moi",
      }))
      .filter((n) => hienMoi || n.level !== "moi" || n.id === here);
    return { nodes: [...sang, ...toi], links: data.links };
  }, [data, progress, hienMoi, here]);

  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const soSang = nodes.filter(isLit).length;
  const soCanSua = nodes.filter((n) => n.level === "can_sua").length;
  const nodeChon = chon?.kind === "node" ? byId.get(chon.id) : null;
  const canhChon = chon?.kind === "edge" ? links.find((l) => khoaCanh(l) === chon.id) : null;

  // Mở từ trang học: bay tới "bạn đang ở đây" sau khi bản đồ đã vừa màn hình.
  const daToi = useRef(false);
  useEffect(() => {
    if (daToi.current || !here || !byId.has(here)) return;
    daToi.current = true;
    const id = setTimeout(() => canvas.current?.focus(here), 700);
    return () => clearTimeout(id);
  }, [here, byId]);

  const bamDinh = (id) => {
    const n = byId.get(id);
    if (!n) return;
    if (noiTu) {
      if (id === noiTu) return setNoiTu(null);
      if (!isLit(n)) return;
      setPhien({ a: byId.get(noiTu), b: n });
      setNoiTu(null);
      setChon(null);
      return;
    }
    setChon((c) => (c?.kind === "node" && c.id === id ? null : { kind: "node", id }));
  };

  const dongPhien = () => {
    const { a, b } = phien;
    const k = [a.id, b.id].sort().join("|");
    setPhien(null);
    reloadProgress();
    if (daCo.current?.has(k)) setChon({ kind: "edge", id: k });
  };

  const tatTips = () => {
    setTips(false);
    try {
      localStorage.setItem(TIPS_KEY, "1");
    } catch {
      // Không lưu được thì lần sau hiện lại — không sao.
    }
  };

  const ketQuaTim = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? nodes.filter((n) => `${n.label} ${n.title}`.toLowerCase().includes(q)).slice(0, 6) : [];
  }, [nodes, query]);

  const toiTrang = (id) => {
    setQuery("");
    setChon({ kind: "node", id });
    // Đợi khung chi tiết mở ra đã, để trang được đưa vào giữa phần CÒN nhìn thấy.
    setTimeout(() => canvas.current?.focus(id), 30);
    timKiem.current?.blur();
  };

  // Việc nên làm tiếp: sửa trang giảng sai trước, rồi nối những trang còn lẻ.
  // Chỉ GỢI Ý chỗ để giảng — không gợi ý hai trang "liên quan", vì như thế là
  // hệ thống tự suy ra mối nối (spec §4c).
  const viecTiep = useMemo(() => {
    const coCanh = new Set(links.flatMap((l) => [l.source, l.target]));
    const sua = nodes
      .filter((n) => n.level === "can_sua")
      .map((n) => ({
        key: n.id,
        level: n.level,
        title: n.label || n.title,
        hint: "Giảng sai lần trước — giảng lại",
        lam: () => toiTrang(n.id),
      }));
    const le =
      soSang >= 2
        ? nodes
            .filter((n) => isLit(n) && !coCanh.has(n.id))
            .map((n) => ({
              key: n.id,
              level: n.level,
              title: n.label || n.title,
              hint: "Chưa nối với trang nào — nối thử",
              lam: () => {
                setChon(null);
                setNoiTu(n.id);
                canvas.current?.fit();
              },
            }))
        : [];
    return [...sua, ...le].slice(0, 3);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, links, soSang]);

  // Phím tắt: / tìm · Esc thoát · F vừa màn hình · + − phóng.
  useEffect(() => {
    function onKey(e) {
      const typing = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName);
      if (e.key === "Escape") {
        if (typing) return timKiem.current?.blur();
        if (phien) return; // phiên nối có nút Đóng riêng — không để lỡ tay mất câu đang nói
        if (xacNhan) return setXacNhan(null);
        if (noiTu) return setNoiTu(null);
        return setChon(null);
      }
      if (typing || e.ctrlKey || e.metaKey || e.altKey || phien) return;
      if (e.key === "/") {
        e.preventDefault();
        timKiem.current?.focus();
      } else if (e.key === "f" || e.key === "F") canvas.current?.fit();
      else if (e.key === "+" || e.key === "=") canvas.current?.zoomBy(1.3);
      else if (e.key === "-") canvas.current?.zoomBy(1 / 1.3);
    }
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [phien, xacNhan, noiTu]);

  const drawer = phien ? "phien" : nodeChon ? "dinh" : canhChon ? "canh" : null;

  return (
    <div className="flex h-screen flex-col bg-white font-sans text-neutral-900 antialiased">
      <header className="z-30 flex h-12 shrink-0 items-center gap-3 border-b border-neutral-200 bg-white px-4 whitespace-nowrap max-sm:gap-2 max-sm:px-3">
        <Brand />
        <WorkspaceTabs active="graph" deck={hereDeck || undefined} page={herePage || undefined} className="ml-1" />
        <span className="ml-1 hidden text-[13px] text-neutral-400 md:inline">Bản đồ hiểu biết</span>
        <div className="ml-auto flex items-center gap-3 max-sm:gap-1">
          <span className="hidden text-[12px] tabular-nums text-neutral-500 sm:inline">
            {soSang} trang đã hiểu · {links.length} mối nối
            {soCanSua > 0 && ` · ${soCanSua} cần sửa`}
          </span>
          <Link
            to="/library"
            className="h-8 rounded-lg px-2.5 text-[13px] leading-8 text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          >
            Thư viện
          </Link>
          {member?.auth && (
            <button
              onClick={() => {
                logout();
                navigate("/");
              }}
              className="h-8 rounded-lg px-2.5 max-sm:hidden text-[13px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            >
              Đăng xuất
            </button>
          )}
        </div>
      </header>

      <main className="relative min-h-0 flex-1 overflow-hidden bg-neutral-50/50">
        {error && <p className="p-6 text-[13px] text-neutral-700">{error}</p>}
        {!data && !error && <p className="p-6 text-[13px] text-neutral-400">Đang dựng bản đồ…</p>}

        {data && (
          <GraphCanvas
            ref={canvas}
            nodes={nodes}
            links={links}
            deckLabel={deckLabel}
            here={here}
            selectedId={nodeChon?.id}
            selectedEdge={chon?.kind === "edge" ? chon.id : null}
            connectFrom={noiTu}
            linking={phien ? [phien.a.id, phien.b.id] : null}
            query={query}
            newEdge={canhMoi}
            onSelectNode={bamDinh}
            onSelectEdge={(k) => !noiTu && setChon({ kind: "edge", id: k })}
            onBackground={() => (noiTu ? setNoiTu(null) : setChon(null))}
            onDropConnect={(a, b) => setXacNhan({ a: byId.get(a), b: byId.get(b) })}
            rightInset={drawer ? 412 : 0}
          />
        )}

        {/* Góc trên trái: tìm trang, bộ lọc. */}
        {data && (
          <div className="absolute top-4 left-4 z-20 w-72 max-w-[calc(100%-2rem)]">
            <div className="relative">
              <input
                ref={timKiem}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && ketQuaTim[0] && toiTrang(ketQuaTim[0].id)}
                placeholder="Tìm một trang"
                aria-label="Tìm một trang trên bản đồ"
                className="h-10 w-full rounded-xl border border-neutral-200 bg-white/95 pr-10 pl-3.5 text-[14px] shadow-sm backdrop-blur outline-none transition-shadow placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-4 focus:ring-neutral-900/5"
              />
              <span className="absolute top-1/2 right-2.5 -translate-y-1/2">
                <Kbd>/</Kbd>
              </span>
            </div>
            <AnimatePresence>
              {ketQuaTim.length > 0 && (
                <motion.ul
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.15 }}
                  className="m-0 mt-1.5 list-none overflow-hidden rounded-xl border border-neutral-200 bg-white p-1 shadow-lg"
                >
                  {ketQuaTim.map((n) => (
                    <li key={n.id}>
                      <button
                        onClick={() => toiTrang(n.id)}
                        className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left transition-colors hover:bg-neutral-100"
                      >
                        <span className="flex w-3 shrink-0 justify-center">
                          <LevelDot level={n.level} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-medium">{n.title}</span>
                          <span className="block truncate text-[11px] text-neutral-500">
                            {deckLabel(n.deck)} · trang {n.page}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </motion.ul>
              )}
            </AnimatePresence>
            <label className="mt-2 inline-flex cursor-pointer items-center gap-2 rounded-lg bg-white/90 px-2.5 py-1.5 text-[12px] text-neutral-600 shadow-sm ring-1 ring-neutral-200 backdrop-blur">
              <input
                type="checkbox"
                checked={hienMoi}
                onChange={(e) => {
                  setHienMoi(e.target.checked);
                  // Bỏ/hiện trang mờ làm cả bản đồ dồn lại — đợi nó lắng rồi mới vừa màn hình.
                  setTimeout(() => canvas.current?.fit(), 600);
                }}
                className="accent-neutral-900"
              />
              Hiện cả trang chưa học
            </label>
          </div>
        )}

        {/* Giữa trên: đang nối bằng nút / xác nhận nối bằng kéo thả. */}
        <AnimatePresence>
          {(noiTu || xacNhan) && (
            <motion.div
              key={noiTu ? "noi" : "xac-nhan"}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2, ease: EASE }}
              className="absolute top-4 left-1/2 z-30 flex w-max max-w-[min(560px,calc(100%-2rem))] -translate-x-1/2 items-center gap-3 rounded-xl bg-neutral-900 px-4 py-2.5 text-white shadow-lg"
              role="status"
            >
              {noiTu ? (
                <>
                  <p className="m-0 min-w-0 flex-1 text-[13px]">
                    Chọn một trang đã sáng để nối với <strong>«{byId.get(noiTu)?.label}»</strong>
                  </p>
                  <Kbd tone="dark">Esc</Kbd>
                  <button
                    onClick={() => setNoiTu(null)}
                    className="h-7 rounded-md px-2 text-[12px] text-white/80 hover:bg-white/10 hover:text-white"
                  >
                    Huỷ
                  </button>
                </>
              ) : (
                <>
                  <p className="m-0 min-w-0 flex-1 text-[13px]">
                    Nối <strong>«{xacNhan.a?.label}»</strong> với <strong>«{xacNhan.b?.label}»</strong>? Bạn sẽ giảng
                    cho học trò vì sao hai trang liên quan.
                  </p>
                  <button
                    onClick={() => {
                      setPhien(xacNhan);
                      setXacNhan(null);
                      setChon(null);
                    }}
                    className="h-8 shrink-0 rounded-lg bg-white px-3 text-[13px] font-medium text-neutral-900 hover:bg-neutral-100"
                  >
                    Giảng mối nối
                  </button>
                  <button
                    onClick={() => setXacNhan(null)}
                    className="h-8 shrink-0 rounded-md px-2 text-[12px] text-white/80 hover:bg-white/10 hover:text-white"
                  >
                    Huỷ
                  </button>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Trống: chưa trang nào sáng. */}
        {data && soSang === 0 && !phien && (
          <motion.div
            {...blurIn}
            className="absolute top-1/2 left-1/2 z-20 w-[min(420px,calc(100%-2rem))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-neutral-200 bg-white/95 p-5 text-center shadow-lg backdrop-blur"
          >
            <p className="m-0 text-[15px] font-medium">Bản đồ còn tối</p>
            <p className="m-0 mt-1 text-[13px] leading-relaxed text-neutral-500">
              Học trò chỉ biết đúng những gì bạn đã giảng cho nó. Giảng được một trang slide là đỉnh đầu tiên sáng lên.
            </p>
            <Link to="/library" className="mt-3 inline-block">
              <Button variant="primary" size="sm">
                Chọn bài để giảng
              </Button>
            </Link>
          </motion.div>
        )}

        {/* Góc trên phải: việc nên làm tiếp, suy từ chính bản đồ. */}
        <AnimatePresence>
          {data && !drawer && !noiTu && viecTiep.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12 }}
              transition={{ duration: 0.25, ease: EASE }}
              className="absolute top-4 right-4 z-20 w-64 rounded-xl bg-white/95 p-1.5 shadow-sm ring-1 ring-neutral-200 backdrop-blur max-md:hidden"
            >
              <p className="m-0 px-2 pt-1 pb-1.5 text-[11px] tracking-wide text-neutral-400 uppercase">Việc nên làm tiếp</p>
              <ul className="m-0 list-none p-0">
                {viecTiep.map((v) => (
                  <li key={v.key}>
                    <button
                      onClick={v.lam}
                      className="flex w-full items-start gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-neutral-100"
                    >
                      <span className="mt-1.5 flex w-3 shrink-0 justify-center">
                        <LevelDot level={v.level} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13px] font-medium">{v.title}</span>
                        <span className="block text-[12px] text-neutral-500">{v.hint}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Góc dưới trái: chú thích. */}
        {data && (
          <div className="absolute bottom-4 left-4 z-20 max-w-[calc(100%-2rem)] rounded-xl bg-white/90 px-3 py-2.5 shadow-sm ring-1 ring-neutral-200 backdrop-blur max-sm:hidden">
            <LevelLegend />
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-neutral-500">
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full border border-dashed border-neutral-400" /> Chưa học
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-px w-3 bg-neutral-500" /> mối nối bạn đã giảng
              </span>
            </div>
          </div>
        )}

        {/* Góc dưới phải: điều khiển khung nhìn. */}
        {data && (
          <div
            className={`absolute bottom-4 z-20 flex flex-col gap-1 rounded-xl bg-white/90 p-1 shadow-sm ring-1 ring-neutral-200 backdrop-blur transition-[right] duration-300 ${
              drawer ? "right-4 lg:right-103" : "right-4"
            }`}
          >
            {[
              ["+", "Phóng to (+)", () => canvas.current?.zoomBy(1.3)],
              ["−", "Thu nhỏ (−)", () => canvas.current?.zoomBy(1 / 1.3)],
              ["⤢", "Vừa màn hình (F)", () => canvas.current?.fit()],
            ].map(([k, label, fn]) => (
              <button
                key={label}
                onClick={fn}
                title={label}
                aria-label={label}
                className="grid size-8 place-items-center rounded-lg text-[15px] text-neutral-700 transition-colors hover:bg-neutral-100"
              >
                {k}
              </button>
            ))}
            {here && byId.has(here) && (
              <button
                onClick={() => canvas.current?.focus(here)}
                title="Tới trang đang học"
                className="rounded-lg px-1.5 py-1 text-[11px] font-medium text-neutral-700 transition-colors hover:bg-neutral-100"
              >
                Tới chỗ tôi
              </button>
            )}
          </div>
        )}

        {/* Gợi ý lần đầu. */}
        <AnimatePresence>
          {data && tips && soSang > 0 && !drawer && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="absolute bottom-4 left-1/2 z-20 w-[min(560px,calc(100%-2rem))] -translate-x-1/2 rounded-2xl border border-neutral-200 bg-white/95 p-4 shadow-lg backdrop-blur max-lg:bottom-28"
            >
              <p className="m-0 text-[13px] font-medium">Cách dùng bản đồ</p>
              <ul className="m-0 mt-1.5 grid list-none gap-1 p-0 text-[12.5px] text-neutral-600 sm:grid-cols-2">
                <li>Kéo nền để di chuyển, cuộn chuột để phóng to</li>
                <li>Kéo một trang để sắp xếp lại</li>
                <li>
                  <strong className="font-medium text-neutral-900">Thả một trang sáng lên trang sáng khác</strong> để nối
                  hai trang
                </li>
                <li>
                  Bấm trang mờ để đi giảng nó · <Kbd>/</Kbd> để tìm
                </li>
              </ul>
              <Button size="sm" className="mt-3" onClick={tatTips}>
                Đã rõ
              </Button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Khung chi tiết trượt vào từ bên phải. */}
        <AnimatePresence>
          {drawer && (
            <motion.aside
              key="drawer"
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="absolute top-4 right-4 bottom-4 z-30 flex w-[min(380px,calc(100%-2rem))] flex-col"
            >
              {drawer === "phien" ? (
                <LinkSession
                  key={`${phien.a.id}|${phien.b.id}`}
                  a={phien.a}
                  b={phien.b}
                  deckTag={(slug) => deckLabel(slug, true)}
                  onEnded={(outcome) => outcome === "TAUGHT" && tai()}
                  onClose={dongPhien}
                />
              ) : drawer === "dinh" ? (
                <ChiTietDinh
                  key={nodeChon.id}
                  node={nodeChon}
                  links={links}
                  byId={byId}
                  deckLabel={deckLabel}
                  coTheNoi={soSang >= 2}
                  onNoi={() => {
                    setNoiTu(nodeChon.id);
                    setChon(null);
                  }}
                  onChonCanh={(k) => setChon({ kind: "edge", id: k })}
                  onClose={() => setChon(null)}
                />
              ) : (
                <ChiTietCanh
                  key={chon.id}
                  link={canhChon}
                  byId={byId}
                  deckLabel={deckLabel}
                  onChonDinh={(id) => {
                    setChon({ kind: "node", id });
                    canvas.current?.focus(id);
                  }}
                  onNoiLai={() => setPhien({ a: byId.get(canhChon.source), b: byId.get(canhChon.target) })}
                  onClose={() => setChon(null)}
                />
              )}
            </motion.aside>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

function KhungNoi({ children, onClose, eyebrow }) {
  return (
    <div className="flex max-h-full flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-xl">
      <div className="flex items-center gap-2 border-b border-neutral-100 px-4 py-2.5">
        <p className="m-0 min-w-0 flex-1 truncate text-[11px] tracking-wide text-neutral-400 uppercase">{eyebrow}</p>
        <button
          onClick={onClose}
          aria-label="Đóng"
          className="-mr-1 h-7 rounded-md px-2 text-[12px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        >
          Đóng
        </button>
      </div>
      <div className="min-h-0 overflow-y-auto p-4">{children}</div>
    </div>
  );
}

function ChiTietDinh({ node, links, byId, deckLabel, coTheNoi, onNoi, onChonCanh, onClose }) {
  const sang = isLit(node);
  const noi = links.filter((l) => l.source === node.id || l.target === node.id);
  const moSlide = `/learn/${encodeURIComponent(node.deck)}?page=${node.page}`;

  return (
    <KhungNoi onClose={onClose} eyebrow={`${deckLabel(node.deck)} · trang ${node.page}`}>
      <p className="m-0 flex flex-wrap items-center gap-1.5 text-[12px] text-neutral-500">
        <LevelDot level={node.level} />
        <span className="font-medium text-neutral-800">{LEVELS[node.level]?.label}</span>
        <span className="text-neutral-300">·</span>
        {LEVELS[node.level]?.hint}
      </p>
      <h2 className="m-0 mt-1.5 text-[16px] leading-snug font-semibold tracking-tight">{node.title}</h2>

      {sang ? (
        <>
          <p className="m-0 mt-3 text-[11px] text-neutral-400">Nguyên văn lời bạn</p>
          <ul className="m-0 mt-1 list-none space-y-2 p-0">
            {(node.sentences?.length ? node.sentences : [node.said]).map((cau) => (
              <li key={cau} className="border-l-2 border-neutral-200 pl-3 text-[14px] leading-relaxed text-neutral-800">
                {cau}
              </li>
            ))}
          </ul>
          <p className="m-0 mt-3 text-[12px] text-neutral-500">Giảng được ở {node.times_taught} buổi</p>
        </>
      ) : (
        <p className="m-0 mt-2 text-[13px] leading-relaxed text-neutral-500">
          {node.level === "can_sua"
            ? "Lần gần nhất bạn giảng trang này có chỗ sai. Giảng lại để sửa hiểu lầm — học trò sẽ hỏi đúng vào chỗ đó."
            : "Học trò chưa biết gì về trang này. Mở ra, chọn phần muốn giảng, rồi giảng không nhìn."}
        </p>
      )}

      {noi.length > 0 && (
        <>
          <p className="m-0 mt-4 text-[11px] text-neutral-400">Đã nối với</p>
          <ul className="m-0 mt-1 list-none space-y-1 p-0">
            {noi.map((l) => {
              const kia = byId.get(l.source === node.id ? l.target : l.source);
              return (
                <li key={khoaCanh(l)}>
                  <button
                    onClick={() => onChonCanh(khoaCanh(l))}
                    className="w-full rounded-lg px-2 py-1.5 text-left text-[13px] text-neutral-700 transition-colors hover:bg-neutral-100"
                  >
                    <span className="font-medium">{kia?.label}</span>
                    <span className="block truncate text-[12px] text-neutral-500">“{l.evidence}”</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {sang && (
          <Button variant="primary" size="sm" disabled={!coTheNoi} onClick={onNoi}>
            Nối với trang khác
          </Button>
        )}
        <Link to={moSlide}>
          <Button size="sm" variant={sang ? "normal" : "primary"}>
            {sang ? `Mở slide ${node.page}` : node.level === "can_sua" ? "Giảng lại trang này" : "Giảng trang này"}
          </Button>
        </Link>
      </div>
      {sang && (
        <p className="m-0 mt-2 text-[12px] text-neutral-400">
          {coTheNoi
            ? "Mẹo: kéo trang này thả lên một trang sáng khác cũng nối được."
            : "Giảng được thêm một trang nữa là nối được."}
        </p>
      )}
    </KhungNoi>
  );
}

function ChiTietCanh({ link, byId, deckLabel, onChonDinh, onNoiLai, onClose }) {
  const a = byId.get(link.source);
  const b = byId.get(link.target);
  return (
    <KhungNoi onClose={onClose} eyebrow="Mối nối bạn đã giảng">
      <div className="flex flex-wrap items-center gap-1.5">
        {[a, b].map((n, i) => (
          <span key={n?.id ?? i} className="contents">
            {i === 1 && <span className="text-neutral-400">—</span>}
            <button
              onClick={() => onChonDinh(n.id)}
              className="rounded-lg bg-neutral-100 px-2 py-1 text-[13px] font-medium text-neutral-900 transition-colors hover:bg-neutral-200"
            >
              {n?.label}{" "}
              <span className="font-normal text-neutral-500">
                {deckLabel(n?.deck, true)} · {n?.page}
              </span>
            </button>
          </span>
        ))}
      </div>
      <p className="m-0 mt-3 text-[11px] text-neutral-400">Nguyên văn lời bạn</p>
      <blockquote className="m-0 mt-1 border-l-2 border-neutral-200 pl-3 text-[14px] leading-relaxed text-neutral-800">
        {link.evidence}
      </blockquote>
      <div className="mt-4">
        <Button size="sm" onClick={onNoiLai}>
          Giảng lại mối nối này
        </Button>
      </div>
    </KhungNoi>
  );
}
