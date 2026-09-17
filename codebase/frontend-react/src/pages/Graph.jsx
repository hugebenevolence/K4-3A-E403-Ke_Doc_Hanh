// Bản đồ hiểu biết: thứ học viên đã DẠY ĐƯỢC, qua mọi buổi và mọi bộ slide.
//
// Đỉnh sáng là một mệnh đề chính họ nói ra và bộ chấm xác nhận có căn cứ; đỉnh
// tối là khái niệm của bài họ chưa giảng nổi. Cạnh chỉ có khi chính họ nối hai
// ý bằng lời — không cạnh nào do hệ thống suy ra.
//
// Vì sao trang này tồn tại (spec §4c): học trò vốn quên sạch sau mỗi phiên, nên
// học viên không thật sự *dạy* nó, chỉ bị nó kiểm tra. Bản đồ là chỗ công sức
// dạy của họ đọng lại và nhìn thấy được.

import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api } from "../api";
import { useAuth } from "../auth";
import { layout, ringLayout } from "../graph-layout";
import { blurIn } from "../motion";
import { studentId } from "../useSession";
import { Brand, LinkButton } from "../site";
import { Button } from "../ui";

const W = 900;
const H = 620;

/** Số khái niệm còn tối hiện trên vành ngoài.
 *
 *  Đo trên bản dựng thật: 33 đỉnh mờ biến vành ngoài thành một dải chữ chen
 *  nhau, và phần sáng — thứ học viên thật sự muốn nhìn — chìm nghỉm giữa đám
 *  đó. Mười sáu thì vành vẫn thưa và vẫn đủ nói "còn nhiều chỗ chưa dạy". */
const MAX_TOI = 16;

/** Bán kính theo số buổi đã giảng lại được — "độ đậm" của spec §4c. */
function banKinh(lan) {
  return 9 + Math.min(lan, 5) * 2.6;
}

export default function GraphPage() {
  const { member, logout } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [chon, setChon] = useState(null);

  useEffect(() => {
    let huy = false;
    // Gửi kèm mã học viên của trình duyệt này: khi server KHÔNG bật đăng nhập,
    // phiên giảng ghi đồ thị dưới mã đó, còn API mặc định lại đọc "demo" —
    // lệch khoá là bản đồ hiện rỗng dù vừa dạy xong.
    api(`/graph?student_id=${encodeURIComponent(studentId())}`)
      .then((d) => !huy && setData(d))
      .catch((e) => !huy && setError(e.message || "Không tải được bản đồ"));
    return () => {
      huy = true;
    };
  }, []);

  const { nodes, pos, links } = useMemo(() => {
    if (!data) return { nodes: [], pos: new Map(), links: [] };
    const sang = data.claims.map((c) => ({ ...c, id: c.concept, sang: true, weight: c.times_taught }));
    // Vùng tối chỉ lấy những khái niệm chưa có đỉnh sáng, và bỏ trùng giữa hai
    // bộ slide — cùng một chữ "token" ở d1 và d2 là MỘT khái niệm, đúng tinh
    // thần xuyên tài liệu của đồ thị.
    const daSang = new Set(sang.map((n) => n.id));
    const toi = [];
    for (const d of data.dim) {
      if (daSang.has(d.concept) || toi.some((t) => t.id === d.concept)) continue;
      toi.push({ ...d, id: d.concept, sang: false, weight: 0 });
    }
    const vanh = toi.slice(0, MAX_TOI);

    // Hai phép xếp khác nhau cho hai loại đỉnh, cố ý: cụm sáng thả lò xo để
    // những ý bạn tự nối nằm cạnh nhau, còn vùng tối xếp thành vành ngoài đều
    // đặn. Thả chung một chỗ thì nhãn của vùng tối đè lên nhau thành đám chữ
    // không đọc được, và chúng chen vào giữa làm loãng phần đáng nhìn nhất.
    const trong = layout(sang, data.links, { width: W * 0.62, height: H * 0.62 });
    const pos = new Map();
    const lech = { x: (W - W * 0.62) / 2, y: (H - H * 0.62) / 2 };
    for (const [id, p] of trong) pos.set(id, { x: p.x + lech.x, y: p.y + lech.y });
    for (const [id, p] of ringLayout(vanh.map((n) => n.id), { width: W, height: H })) pos.set(id, p);

    return { nodes: [...sang, ...vanh], pos, links: data.links };
  }, [data]);

  const dangChon = chon ? nodes.find((n) => n.id === chon) : null;
  const noiVoiChon = useMemo(
    () => new Set(links.filter((l) => l.source === chon || l.target === chon).flatMap((l) => [l.source, l.target])),
    [links, chon],
  );

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
          Mỗi đỉnh sáng là một ý <strong className="font-medium text-neutral-700">chính bạn nói ra</strong> và học
          trò đã hiểu. Đỉnh càng to là bạn giảng lại được càng nhiều buổi. Đỉnh mờ là phần bài học trò vẫn còn tối —
          nó chỉ sáng lên khi bạn giảng.
        </p>

        {error && <p className="mt-4 text-[13px] text-neutral-700">{error}</p>}
        {!data && !error && <p className="mt-4 text-[13px] text-neutral-400">Đang dựng bản đồ…</p>}

        {data && data.claims.length === 0 && (
          <motion.div {...blurIn} className="mt-5 rounded-2xl border border-neutral-200 p-5">
            <p className="m-0 text-[15px] font-medium">Bản đồ còn trống</p>
            <p className="m-0 mt-1 text-[13px] leading-relaxed text-neutral-500">
              Học trò chưa biết gì cả — nó chỉ biết đúng những điều bạn đã giảng cho nó. Giảng xong một phần slide
              là đỉnh đầu tiên hiện ra ở đây.
            </p>
            <LinkButton to="/library" className="mt-4">
              Chọn bài để giảng
            </LinkButton>
          </motion.div>
        )}

        {data && data.claims.length > 0 && (
          <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
            <motion.div {...blurIn} className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
              <svg
                viewBox={`0 0 ${W} ${H}`}
                className="block h-[min(70vh,620px)] w-full"
                onClick={() => setChon(null)}
                role="img"
                aria-label="Bản đồ khái niệm bạn đã giảng"
              >
                {links.map((l) => {
                  const a = pos.get(l.source);
                  const b = pos.get(l.target);
                  if (!a || !b) return null;
                  const noiBat = chon && (l.source === chon || l.target === chon);
                  return (
                    <g key={`${l.source}-${l.target}`}>
                      <line
                        x1={a.x}
                        y1={a.y}
                        x2={b.x}
                        y2={b.y}
                        stroke={noiBat ? "#171717" : "#d4d4d4"}
                        strokeWidth={noiBat ? 1.6 : 1}
                      />
                      {noiBat && (
                        <text
                          x={(a.x + b.x) / 2}
                          y={(a.y + b.y) / 2 - 6}
                          textAnchor="middle"
                          className="fill-neutral-500 text-[11px]"
                        >
                          {l.label}
                        </text>
                      )}
                    </g>
                  );
                })}

                {nodes.map((n) => {
                  const p = pos.get(n.id);
                  if (!p) return null;
                  const r = n.sang ? banKinh(n.times_taught) : 5;
                  const mo = chon && !noiVoiChon.has(n.id) && n.id !== chon;
                  return (
                    <g
                      key={n.id}
                      transform={`translate(${p.x} ${p.y})`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setChon(n.id === chon ? null : n.id);
                      }}
                      className="cursor-pointer"
                      opacity={mo ? 0.25 : 1}
                    >
                      {n.id === chon && (
                        <circle r={r + 7} fill="none" stroke="#171717" strokeWidth="1.2" opacity="0.35" />
                      )}
                      <circle
                        r={r}
                        fill={n.sang ? "#171717" : "#fff"}
                        stroke={n.sang ? "#171717" : "#d4d4d4"}
                        strokeWidth={n.sang ? 0 : 1.4}
                        strokeDasharray={n.sang ? undefined : "3 3"}
                      />
                      <text
                        y={r + 15}
                        textAnchor="middle"
                        className={`text-[12px] ${n.sang ? "fill-neutral-900 font-medium" : "fill-neutral-400"}`}
                      >
                        {n.concept}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </motion.div>

            <motion.aside {...blurIn} className="lg:sticky lg:top-20 lg:self-start">
              {dangChon ? (
                <ChiTiet node={dangChon} links={links} />
              ) : (
                <div className="rounded-2xl border border-neutral-200 p-4">
                  <p className="m-0 text-[13px] font-medium">Bấm vào một đỉnh</p>
                  <p className="m-0 mt-1 text-[13px] leading-relaxed text-neutral-500">
                    Bạn sẽ thấy đúng câu mình đã nói về khái niệm đó, và mở lại được slide tương ứng.
                  </p>
                  <dl className="m-0 mt-4 space-y-2 text-[13px]">
                    <div className="flex items-center gap-2.5">
                      <span className="size-3 shrink-0 rounded-full bg-neutral-900" />
                      <span className="text-neutral-600">đã giảng được — càng to càng nhiều buổi</span>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <span className="size-3 shrink-0 rounded-full border border-dashed border-neutral-300" />
                      <span className="text-neutral-600">học trò còn tối chỗ này</span>
                    </div>
                  </dl>
                  <p className="m-0 mt-4 text-[12px] text-neutral-400">
                    {data.claims.length} ý đã dạy · {links.length} liên hệ bạn tự nối
                  </p>
                </div>
              )}
            </motion.aside>
          </div>
        )}
      </main>
    </div>
  );
}

function ChiTiet({ node, links }) {
  const noi = links.filter((l) => l.source === node.id || l.target === node.id);
  const cho = node.sang
    ? [{ deck: node.deck, page: node.page }, ...(node.also_on ?? [])].filter((c) => c.deck)
    : [{ deck: node.deck, page: node.page }];

  return (
    <div className="rounded-2xl border border-neutral-200 p-4">
      <p className="m-0 text-[11px] tracking-wide text-neutral-400 uppercase">
        {node.sang ? "Bạn đã dạy học trò" : "Học trò còn tối chỗ này"}
      </p>
      <h2 className="m-0 mt-1 text-[17px] font-semibold tracking-tight">{node.concept}</h2>

      {node.sang ? (
        <>
          <p className="m-0 mt-3 text-[11px] text-neutral-400">Nguyên văn lời bạn</p>
          <blockquote className="m-0 mt-1 border-l-2 border-neutral-200 pl-3 text-[14px] leading-relaxed text-neutral-800">
            {node.said}
          </blockquote>
          <p className="m-0 mt-3 text-[12px] text-neutral-500">
            Giảng lại được ở {node.times_taught} buổi
          </p>
        </>
      ) : (
        <p className="m-0 mt-2 text-[13px] leading-relaxed text-neutral-500">
          Bạn chưa giảng nổi ý này cho học trò. Mở slide rồi thử giảng xem.
        </p>
      )}

      {noi.length > 0 && (
        <>
          <p className="m-0 mt-4 text-[11px] text-neutral-400">Bạn đã tự nối</p>
          <ul className="m-0 mt-1 list-none space-y-2 p-0">
            {noi.map((l) => (
              <li key={`${l.source}-${l.target}`} className="text-[13px] text-neutral-700">
                <span className="font-medium">
                  {l.source} {l.label} {l.target}
                </span>
                <span className="mt-0.5 block text-[12px] text-neutral-500">vì bạn nói: “{l.evidence}”</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {cho.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {cho.map((c) => (
            <Link key={`${c.deck}-${c.page}`} to={`/learn/${encodeURIComponent(c.deck)}?page=${c.page}`}>
              <Button size="sm">Mở slide {c.page}</Button>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
