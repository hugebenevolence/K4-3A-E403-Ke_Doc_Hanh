// Bản đồ hiểu biết: thứ học viên đã DẠY ĐƯỢC, qua mọi buổi và mọi bộ slide.
//
// Hai luật, cùng một động từ — "giảng được": đỉnh sáng là một TRANG slide họ
// đã giảng được (bộ chấm xác nhận đủ), mang nguyên văn những câu họ nói; cạnh
// là một mối nối họ đã giảng được. Đỉnh tối là trang còn giảng được mà họ chưa
// giảng. Không đỉnh, không cạnh nào do hệ thống suy ra.
//
// Bản đồ là CHỖ LÀM VIỆC, không chỉ để nhìn (spec §4c): bấm một đỉnh tối là đi
// giảng trang đó; chọn hai đỉnh sáng là giảng mối nối giữa chúng ngay tại đây.
// Đồ thị kiểu Obsidian bị chê "mở một lần rồi thôi" chính vì không làm được gì
// trên nó — lý do để mở lại bản đồ này là để nối thêm.

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { layout, ringLayout } from "../graph-layout";
import LinkSession from "../LinkSession";
import { blurIn, EASE } from "../motion";
import { Brand, LinkButton } from "../site";
import { Button, Kbd } from "../ui";
import { studentId } from "../useSession";

const W = 900;
const H = 620;

/** Số trang còn tối hiện trên vành ngoài.
 *
 *  Đo trên bản dựng thật: 33 đỉnh mờ biến vành ngoài thành một dải chữ chen
 *  nhau, và phần sáng — thứ học viên thật sự muốn nhìn — chìm nghỉm giữa đám
 *  đó. Mười sáu thì vành vẫn thưa và vẫn đủ nói "còn nhiều chỗ chưa dạy". */
const MAX_TOI = 16;

/** Đỉnh trượt tới chỗ mới thay vì nhảy: thêm một cạnh làm lò xo kéo lại cả cụm,
 *  và nhảy tức thì thì người học mất dấu đỉnh mình vừa nối. */
const TRUOT = { duration: 0.7, ease: EASE };

/** "d1-slide-hackathon" → "D1": đủ để thấy một cạnh nối hai bộ slide khác nhau. */
function deckTag(slug) {
  return (slug || "").split("-")[0].toUpperCase();
}

/** Bán kính theo số buổi đã giảng lại được — "độ đậm" của spec §4c. */
function banKinh(lan) {
  return 9 + Math.min(lan, 5) * 2.6;
}

/** Một cặp chỉ có một cạnh, bất kể chiều — khớp với luật ở backend. */
function khoaCanh(l) {
  return [l.source, l.target].sort().join("|");
}

export default function GraphPage() {
  const { member, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [chon, setChon] = useState(null); // { kind: "node" | "edge", id }
  const [ro, setRo] = useState(null); // đỉnh đang được rê chuột hoặc focus
  const [noiTu, setNoiTu] = useState(null); // chế độ nối: đỉnh gốc
  const [phien, setPhien] = useState(null); // { a, b } — phiên nối đang mở
  const [canhMoi, setCanhMoi] = useState(null);
  const daCo = useRef(null);

  // Tải lại sau mỗi phiên nối, và nhớ những cạnh đã có để biết cạnh nào VỪA
  // sinh ra — cạnh đó được vẽ dần ra thay vì hiện bụp một cái.
  const tai = useCallback(async () => {
    try {
      // Gửi kèm mã học viên của trình duyệt này: khi server KHÔNG bật đăng
      // nhập, phiên giảng ghi đồ thị dưới mã đó, còn API mặc định lại đọc
      // "demo" — lệch khoá là bản đồ hiện rỗng dù vừa dạy xong.
      const d = await api(`/graph?student_id=${encodeURIComponent(studentId())}`);
      const moi = daCo.current && d.links.map(khoaCanh).find((k) => !daCo.current.has(k));
      daCo.current = new Set(d.links.map(khoaCanh));
      if (moi) setCanhMoi(moi);
      setData(d);
    } catch (e) {
      setError(e.message || "Không tải được bản đồ");
    }
  }, []);

  useEffect(() => {
    tai();
  }, [tai]);

  const { nodes, byId, pos, links } = useMemo(() => {
    if (!data) return { nodes: [], byId: new Map(), pos: new Map(), links: [] };
    const sang = data.claims.map((c) => ({ ...c, id: c.concept, sang: true, weight: c.times_taught }));
    // Vành tối ưu tiên trang của những bộ slide học viên ĐANG học: người mới
    // giảng vài trang Day 1 cần thấy phần còn lại của Day 1, chưa cần Day 2.
    const dangHoc = new Set(sang.map((n) => n.deck));
    const toi = [...data.dim]
      .sort((a, b) => Number(dangHoc.has(b.deck)) - Number(dangHoc.has(a.deck)))
      .map((d) => ({ ...d, id: d.concept, sang: false, weight: 0 }))
      .slice(0, MAX_TOI);

    // Hai phép xếp khác nhau cho hai loại đỉnh, cố ý: cụm sáng thả lò xo để
    // những trang bạn đã nối nằm cạnh nhau, còn vùng tối xếp thành vành ngoài
    // đều đặn. Thả chung thì nhãn vùng tối đè lên nhau thành đám chữ không đọc
    // được, và chen vào giữa làm loãng phần đáng nhìn nhất.
    const trong = layout(sang, data.links, { width: W * 0.62, height: H * 0.62 });
    const pos = new Map();
    const lech = { x: (W - W * 0.62) / 2, y: (H - H * 0.62) / 2 };
    for (const [id, p] of trong) pos.set(id, { x: p.x + lech.x, y: p.y + lech.y });
    for (const [id, p] of ringLayout(toi.map((n) => n.id), { width: W, height: H })) pos.set(id, p);

    const all = [...sang, ...toi];
    return { nodes: all, byId: new Map(all.map((n) => [n.id, n])), pos, links: data.links };
  }, [data]);

  const soSang = nodes.filter((n) => n.sang).length;
  const nodeChon = chon?.kind === "node" ? byId.get(chon.id) : null;
  const canhChon = chon?.kind === "edge" ? links.find((l) => khoaCanh(l) === chon.id) : null;

  // Những đỉnh đang "được nhìn": đỉnh chọn/rê và hàng xóm trực tiếp của nó.
  // Chỉ làm mờ phần còn lại khi tâm là một trang SÁNG CÓ CẠNH: rê qua một trang
  // tối (không hàng xóm nào) mà cả cụm sáng mờ đi thì người học tưởng mình vừa
  // làm mất bản đồ — đo được khi đi Tab qua vành tối.
  const tam = phien ? null : (noiTu ?? ro ?? nodeChon?.id ?? null);
  const hangXom = useMemo(() => {
    if (!tam || !byId.get(tam)?.sang || !links.some((l) => l.source === tam || l.target === tam)) return null;
    const s = new Set([tam]);
    for (const l of links) {
      if (l.source === tam) s.add(l.target);
      if (l.target === tam) s.add(l.source);
    }
    return s;
  }, [links, tam, byId]);

  const batDauNoi = (id) => {
    setNoiTu(id);
    setChon(null);
  };
  const huyNoi = () => setNoiTu(null);

  const bamDinh = (n) => {
    if (noiTu) {
      if (n.id === noiTu) return huyNoi();
      if (!n.sang) return; // đích không hợp lệ: đã mờ đi, bấm vào không làm gì
      setPhien({ a: byId.get(noiTu), b: n });
      setNoiTu(null);
      setChon(null);
      return;
    }
    setChon((c) => (c?.kind === "node" && c.id === n.id ? null : { kind: "node", id: n.id }));
  };

  // Esc: thoát chế độ nối trước, rồi mới bỏ chọn. Phiên nối có nút Đóng riêng —
  // không để một phím lỡ tay xoá mất câu trả lời đang nói dở.
  useEffect(() => {
    function onKey(e) {
      if (e.key !== "Escape" || phien) return;
      if (noiTu) setNoiTu(null);
      else setChon(null);
    }
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [noiTu, phien]);

  const dongPhien = (noiDuoc) => {
    const { a, b } = phien;
    setPhien(null);
    if (noiDuoc) setChon({ kind: "edge", id: [a.id, b.id].sort().join("|") });
  };

  const dichHopLe = noiTu && ro && ro !== noiTu && byId.get(ro)?.sang;

  return (
    <div className="min-h-screen bg-white font-sans text-neutral-900 antialiased">
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <Brand />
          <span className="ml-1 hidden text-[13px] text-neutral-400 sm:inline">Bản đồ hiểu biết</span>
          <div className="ml-auto flex items-center gap-1">
            <LinkButton to="/library" variant="quiet">
              Thư viện
            </LinkButton>
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

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <h1 className="m-0 text-[22px] font-semibold tracking-tight">Bạn đã dạy học trò những gì</h1>
        <p className="m-0 mt-1 max-w-2xl text-[13px] leading-relaxed text-neutral-500">
          Mỗi đỉnh sáng là một trang slide <strong className="font-medium text-neutral-700">bạn đã giảng được</strong>{" "}
          — học trò hiểu nó nhờ chính lời bạn. Mỗi đường nối là một mối liên hệ bạn đã giảng được giữa hai trang.
        </p>

        {error && <p className="mt-4 text-[13px] text-neutral-700">{error}</p>}
        {!data && !error && <p className="mt-4 text-[13px] text-neutral-400">Đang dựng bản đồ…</p>}

        {data && soSang === 0 && (
          <motion.div {...blurIn} className="mt-5 rounded-2xl border border-neutral-200 p-5">
            <p className="m-0 text-[15px] font-medium">Bản đồ còn trống</p>
            <p className="m-0 mt-1 text-[13px] leading-relaxed text-neutral-500">
              Học trò chưa biết gì cả — nó chỉ biết đúng những điều bạn đã giảng cho nó. Giảng được một trang slide
              là đỉnh đầu tiên sáng lên ở đây.
            </p>
            <LinkButton to="/library" className="mt-4">
              Chọn bài để giảng
            </LinkButton>
          </motion.div>
        )}

        {data && soSang > 0 && (
          <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
            <motion.div
              {...blurIn}
              className="relative overflow-hidden rounded-2xl border border-neutral-200 bg-white"
            >
              <AnimatePresence>
                {noiTu && (
                  <motion.div
                    key="noi"
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.2, ease: EASE }}
                    className="absolute inset-x-3 top-3 z-10 flex items-center gap-3 rounded-xl bg-neutral-900 px-3.5 py-2.5 text-white"
                    role="status"
                  >
                    <p className="m-0 min-w-0 flex-1 text-[13px]">
                      Chọn một trang đã sáng để nối với{" "}
                      <strong className="font-semibold">«{byId.get(noiTu)?.label}»</strong>
                    </p>
                    <Kbd tone="dark">Esc</Kbd>
                    <button
                      onClick={huyNoi}
                      className="h-7 rounded-md px-2 text-[12px] text-white/80 transition-colors hover:bg-white/10 hover:text-white"
                    >
                      Huỷ
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>

              <svg
                viewBox={`0 0 ${W} ${H}`}
                className="block h-[min(70vh,620px)] w-full"
                // Bấm ra chỗ trống: thoát chế độ nối, hoặc bỏ chọn — như bấm Esc.
                onClick={() => (noiTu ? huyNoi() : setChon(null))}
                role="group"
                aria-label="Bản đồ các trang bạn đã giảng"
              >
                {/* Cạnh. Một đường trong suốt dày hơn nằm dưới để bấm trúng dễ —
                    đường 1px thì chuột phải căn chính xác từng điểm ảnh. */}
                {links.map((l) => {
                  const a = pos.get(l.source);
                  const b = pos.get(l.target);
                  if (!a || !b) return null;
                  const k = khoaCanh(l);
                  const noiBat =
                    chon?.kind === "edge" ? chon.id === k : !!hangXom && (l.source === tam || l.target === tam);
                  const mo = phien ? true : !noiBat && (hangXom || chon?.kind === "edge");
                  return (
                    <g key={k}>
                      <motion.line
                        initial={k === canhMoi ? { pathLength: 0 } : false}
                        animate={{ x1: a.x, y1: a.y, x2: b.x, y2: b.y, pathLength: 1 }}
                        transition={k === canhMoi ? { ...TRUOT, pathLength: { duration: 0.9, ease: EASE } } : TRUOT}
                        stroke={noiBat ? "#171717" : "#a3a3a3"}
                        strokeWidth={noiBat ? 2 : 1.3}
                        opacity={mo ? 0.25 : 1}
                      />
                      <line
                        x1={a.x}
                        y1={a.y}
                        x2={b.x}
                        y2={b.y}
                        stroke="transparent"
                        strokeWidth="14"
                        className={noiTu ? "" : "cursor-pointer"}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!noiTu) setChon({ kind: "edge", id: k });
                        }}
                      >
                        <title>{`${byId.get(l.source)?.label} — ${byId.get(l.target)?.label}: “${l.evidence}”`}</title>
                      </line>
                    </g>
                  );
                })}

                {/* Hai trang đang được nối: đường nét đứt, thành nét liền khi nối được. */}
                {phien && pos.get(phien.a.id) && pos.get(phien.b.id) && (
                  <motion.line
                    x1={pos.get(phien.a.id).x}
                    y1={pos.get(phien.a.id).y}
                    x2={pos.get(phien.b.id).x}
                    y2={pos.get(phien.b.id).y}
                    stroke="#171717"
                    strokeWidth="1.6"
                    strokeDasharray="5 5"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0.35, 1, 0.35] }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                    pointerEvents="none"
                  />
                )}

                {/* Đường nối thử trong chế độ nối: đi theo con trỏ tới đích. */}
                {dichHopLe && (
                  <line
                    x1={pos.get(noiTu).x}
                    y1={pos.get(noiTu).y}
                    x2={pos.get(ro).x}
                    y2={pos.get(ro).y}
                    stroke="#171717"
                    strokeWidth="1.5"
                    strokeDasharray="5 5"
                    pointerEvents="none"
                  />
                )}

                {nodes.map((n) => {
                  const p = pos.get(n.id);
                  if (!p) return null;
                  const r = n.sang ? banKinh(n.times_taught) : 5;
                  const laGoc = noiTu === n.id;
                  const dichDuoc = noiTu && n.sang && !laGoc;
                  const mo = phien
                    ? n.id !== phien.a.id && n.id !== phien.b.id
                    : noiTu
                      ? !laGoc && !dichDuoc
                      : (hangXom && !hangXom.has(n.id)) ||
                        (canhChon && n.id !== canhChon.source && n.id !== canhChon.target);
                  const dangRo = ro === n.id;
                  const dangChon = nodeChon?.id === n.id;
                  const ten = n.label || n.title;
                  return (
                    <motion.g
                      key={n.id}
                      initial={false}
                      animate={{ x: p.x, y: p.y, opacity: mo ? 0.22 : 1 }}
                      transition={TRUOT}
                      className={noiTu && !dichDuoc && !laGoc ? "cursor-not-allowed" : "cursor-pointer"}
                      tabIndex={0}
                      role="button"
                      aria-label={`${n.sang ? "Đã giảng" : "Chưa giảng"}: ${n.title}`}
                      aria-pressed={dangChon}
                      style={{ outline: "none" }}
                      onMouseEnter={() => setRo(n.id)}
                      onMouseLeave={() => setRo((x) => (x === n.id ? null : x))}
                      onFocus={() => setRo(n.id)}
                      onBlur={() => setRo((x) => (x === n.id ? null : x))}
                      onClick={(e) => {
                        e.stopPropagation();
                        bamDinh(n);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          bamDinh(n);
                        }
                      }}
                    >
                      <title>{n.title}</title>
                      {/* Vòng hít thở ở đỉnh gốc trong lúc chọn đích để nối. */}
                      {laGoc && (
                        <motion.circle
                          r={r + 9}
                          fill="none"
                          stroke="#171717"
                          strokeWidth="1.4"
                          initial={{ opacity: 0.6, scale: 0.9 }}
                          animate={{ opacity: [0.6, 0.15, 0.6], scale: [0.9, 1.15, 0.9] }}
                          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                        />
                      )}
                      {(dangChon || dangRo) && !laGoc && (
                        <circle
                          r={r + 7}
                          fill="none"
                          stroke={dangChon ? "#171717" : "#a3a3a3"}
                          strokeWidth="1.3"
                          strokeDasharray={dichDuoc ? "4 3" : undefined}
                        />
                      )}
                      <circle
                        r={r}
                        fill={n.sang ? "#171717" : "#fff"}
                        stroke={n.sang ? "#171717" : "#a3a3a3"}
                        strokeWidth={n.sang ? 0 : 1.4}
                        strokeDasharray={n.sang ? undefined : "3 3"}
                      />
                      <text
                        y={r + 15}
                        textAnchor="middle"
                        stroke="#fff"
                        strokeWidth="4"
                        strokeLinejoin="round"
                        paintOrder="stroke"
                        className={`text-[12px] ${n.sang ? "fill-neutral-900 font-medium" : "fill-neutral-400"}`}
                      >
                        {ten}
                      </text>
                      {n.sang && (
                        <text
                          y={r + 28}
                          textAnchor="middle"
                          stroke="#fff"
                          strokeWidth="4"
                          strokeLinejoin="round"
                          paintOrder="stroke"
                          className="fill-neutral-400 text-[10px]"
                        >
                          {deckTag(n.deck)} · tr. {n.page}
                        </text>
                      )}
                    </motion.g>
                  );
                })}
              </svg>
            </motion.div>

            <aside className="lg:sticky lg:top-20 lg:self-start">
              <AnimatePresence mode="wait">
                {phien ? (
                  <LinkSession
                    key={`${phien.a.id}|${phien.b.id}`}
                    a={phien.a}
                    b={phien.b}
                    deckTag={deckTag}
                    onEnded={(outcome) => outcome === "TAUGHT" && tai()}
                    onClose={() => dongPhien(daCo.current?.has([phien.a.id, phien.b.id].sort().join("|")))}
                  />
                ) : nodeChon ? (
                  <ChiTietDinh
                    key={nodeChon.id}
                    node={nodeChon}
                    links={links}
                    byId={byId}
                    coTheNoi={soSang >= 2}
                    onNoi={() => batDauNoi(nodeChon.id)}
                    onChonCanh={(k) => setChon({ kind: "edge", id: k })}
                  />
                ) : canhChon ? (
                  <ChiTietCanh
                    key={chon.id}
                    link={canhChon}
                    byId={byId}
                    onChonDinh={(id) => setChon({ kind: "node", id })}
                    onNoiLai={() => setPhien({ a: byId.get(canhChon.source), b: byId.get(canhChon.target) })}
                  />
                ) : (
                  <HuongDan key="huong-dan" soSang={soSang} soCanh={links.length} />
                )}
              </AnimatePresence>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}

function HuongDan({ soSang, soCanh }) {
  return (
    <motion.div {...blurIn} className="rounded-2xl border border-neutral-200 p-4">
      <p className="m-0 text-[13px] font-medium">Bấm vào một trang</p>
      <p className="m-0 mt-1 text-[13px] leading-relaxed text-neutral-500">
        Trang sáng: đọc lại đúng những câu bạn đã giảng, rồi nối nó với một trang khác. Trang mờ: đi giảng trang đó.
      </p>
      <dl className="m-0 mt-4 space-y-2 text-[13px]">
        <div className="flex items-center gap-2.5">
          <span className="size-3 shrink-0 rounded-full bg-neutral-900" />
          <span className="text-neutral-600">đã giảng được — càng to càng nhiều buổi</span>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="size-3 shrink-0 rounded-full border border-dashed border-neutral-400" />
          <span className="text-neutral-600">học trò còn tối trang này</span>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="h-px w-3 shrink-0 bg-neutral-500" />
          <span className="text-neutral-600">mối nối bạn đã giảng được</span>
        </div>
      </dl>
      <p className="m-0 mt-4 text-[12px] text-neutral-400">
        {soSang} trang đã giảng · {soCanh} mối nối
      </p>
    </motion.div>
  );
}

function ChiTietDinh({ node, links, byId, coTheNoi, onNoi, onChonCanh }) {
  const noi = links.filter((l) => l.source === node.id || l.target === node.id);
  const moSlide = `/learn/${encodeURIComponent(node.deck)}?page=${node.page}`;

  return (
    <motion.div {...blurIn} className="rounded-2xl border border-neutral-200 p-4">
      <p className="m-0 text-[11px] tracking-wide text-neutral-400 uppercase">
        {node.sang ? "Bạn đã dạy học trò" : "Học trò còn tối trang này"} · {deckTag(node.deck)} · trang {node.page}
      </p>
      <h2 className="m-0 mt-1 text-[16px] leading-snug font-semibold tracking-tight">{node.title}</h2>

      {node.sang ? (
        <>
          <p className="m-0 mt-3 text-[11px] text-neutral-400">Nguyên văn lời bạn</p>
          <ul className="m-0 mt-1 list-none space-y-2 p-0">
            {(node.sentences?.length ? node.sentences : [node.said]).map((cau) => (
              <li
                key={cau}
                className="border-l-2 border-neutral-200 pl-3 text-[14px] leading-relaxed text-neutral-800"
              >
                {cau}
              </li>
            ))}
          </ul>
          <p className="m-0 mt-3 text-[12px] text-neutral-500">Giảng được ở {node.times_taught} buổi</p>
        </>
      ) : (
        <p className="m-0 mt-2 text-[13px] leading-relaxed text-neutral-500">
          Bạn chưa giảng trang này cho học trò. Mở ra, chọn phần muốn giảng, rồi giảng không nhìn.
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
        {node.sang && (
          <Button
            variant="primary"
            size="sm"
            disabled={!coTheNoi}
            onClick={onNoi}
            title={coTheNoi ? "Chọn một trang khác để giảng mối nối" : undefined}
          >
            Nối với trang khác
          </Button>
        )}
        <Link to={moSlide}>
          <Button size="sm" variant={node.sang ? "normal" : "primary"}>
            {node.sang ? `Mở slide ${node.page}` : "Giảng trang này"}
          </Button>
        </Link>
      </div>
      {node.sang && !coTheNoi && (
        <p className="m-0 mt-2 text-[12px] text-neutral-400">Giảng được thêm một trang nữa là nối được.</p>
      )}
    </motion.div>
  );
}

function ChiTietCanh({ link, byId, onChonDinh, onNoiLai }) {
  const a = byId.get(link.source);
  const b = byId.get(link.target);
  return (
    <motion.div {...blurIn} className="rounded-2xl border border-neutral-200 p-4">
      <p className="m-0 text-[11px] tracking-wide text-neutral-400 uppercase">Mối nối bạn đã giảng</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {[a, b].map((n, i) => (
          <span key={n?.id ?? i} className="contents">
            {i === 1 && <span className="text-neutral-400">—</span>}
            <button
              onClick={() => onChonDinh(n.id)}
              className="rounded-lg bg-neutral-100 px-2 py-1 text-[13px] font-medium text-neutral-900 transition-colors hover:bg-neutral-200"
            >
              {n?.label}{" "}
              <span className="font-normal text-neutral-500">
                {deckTag(n?.deck)} · {n?.page}
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
    </motion.div>
  );
}
