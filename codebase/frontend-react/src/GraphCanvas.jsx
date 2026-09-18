// Không gian bản đồ kiểu Obsidian: mô phỏng lực chạy liên tục, kéo thả trang,
// kéo nền để di chuyển, cuộn để phóng to quanh con trỏ.
//
// Chỉ lo phần "không gian" — dữ liệu, phiên nối và khung chi tiết nằm ở trang
// Graph. Luật của bản đồ vẫn giữ nguyên (spec §4c): cạnh chỉ đến từ mối nối học
// viên đã giảng được. Việc gom các trang của cùng một buổi học vào một vùng là
// cách XẾP CHỖ, không vẽ thêm cạnh nào.

import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
} from "d3-force";
import { motion } from "motion/react";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import { EASE } from "./motion";

const K_MIN = 0.25;
const K_MAX = 3;
/** Phóng to quá ngần này thì trang chưa học mới hiện nhãn — nhìn toàn cảnh mà
 *  hiện hết nhãn thì thành đám chữ, đúng lời chê "hairball" của đồ thị Obsidian. */
const K_LABEL = 2;
/** Kéo quá ngần này điểm ảnh mới tính là kéo; ít hơn là một cú bấm. */
const DRAG_PX = 4;
/** Con trỏ cách một trang sáng trong ngần này điểm ảnh MÀN HÌNH là thả lên nó —
 *  tính theo màn hình để thu nhỏ bản đồ rồi vẫn thả trúng. */
const DROP_PX = 26;

/** Cỡ chữ trên màn hình kẹp trong [min, max] px dù phóng to hay thu nhỏ: nhìn
 *  toàn cảnh vẫn đọc được tên trang, phóng sát vào chữ cũng không to như biển
 *  quảng cáo. Trả về cỡ trong toạ độ thế giới (trước khi nhân k). */
const chu = (px, k, min = 11, max = 16) => Math.min(max, Math.max(min, px * k)) / k;

export function radiusOf(n) {
  if (n.level === "da_hieu" || n.level === "vung") return 9 + Math.min(n.times_taught || 1, 5) * 2.4;
  if (n.level === "can_sua") return 7;
  if (n.level === "dang_hoc") return 5.5;
  return 4;
}

const isLit = (n) => n?.level === "da_hieu" || n?.level === "vung";

/** Tâm của từng buổi học trên một vòng tròn dẹt, bắt đầu từ bên trái: màn hình
 *  nằm ngang nên hai buổi thì đặt trái — phải, các buổi tách vùng rõ ràng. */
function deckCenters(decks) {
  if (decks.length <= 1) return new Map(decks.map((d) => [d, { x: 0, y: 0 }]));
  const r = 260 + 60 * decks.length;
  return new Map(
    decks.map((d, i) => {
      const a = Math.PI + (i / decks.length) * Math.PI * 2;
      return [d, { x: Math.cos(a) * r, y: Math.sin(a) * r * 0.6 }];
    }),
  );
}

/** Băm tên thành số ổn định: cùng một bản đồ thì mở lần nào cũng ra cùng hình. */
function hash(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

const GraphCanvas = forwardRef(function GraphCanvas(
  {
    nodes,
    links,
    deckLabel,
    here,
    selectedId,
    selectedEdge,
    connectFrom,
    linking,
    query,
    newEdge,
    onSelectNode,
    onSelectEdge,
    onBackground,
    onDropConnect,
    rightInset = 0,
  },
  ref,
) {
  const wrap = useRef(null);
  // 0 cho tới khi đo được thật: vừa màn hình theo một cỡ đoán là lệch hẳn trên điện thoại.
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [t, setT] = useState({ x: 400, y: 300, k: 1 });
  const tRef = useRef(t);
  tRef.current = t;
  const [, setFrame] = useState(0);
  const [hover, setHover] = useState(null);
  const [dragging, setDragging] = useState(null); // { id, moved, target }
  const sim = useRef(null);
  const simNodes = useRef(new Map());
  const drag = useRef(null);
  const pan = useRef(null);
  const anim = useRef(null);

  // ---- kích thước khung -------------------------------------------------
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setSize({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const decks = useMemo(() => [...new Set(nodes.map((n) => n.deck))], [nodes]);
  const centers = useMemo(() => deckCenters(decks), [decks]);

  // Trang đang bị kéo không đẩy, không va ai: nếu không, trang đích sẽ tự trôi
  // ra xa đúng lúc học viên đưa trang kia tới gần để thả nối.
  const charge = useCallback((d) => (d.id === drag.current?.id ? 0 : isLit(d) ? -180 : -40), []);
  const collide = useCallback((d) => (d.id === drag.current?.id ? 0 : radiusOf(d) + (isLit(d) ? 24 : 16)), []);

  // ---- mô phỏng lực ------------------------------------------------------
  useEffect(() => {
    // Giữ vị trí cũ của những trang đã có, để thêm một cạnh mới không làm cả
    // bản đồ nhảy về chỗ khác.
    const cu = simNodes.current;
    const moi = new Map();
    for (const n of nodes) {
      const old = cu.get(n.id);
      const c = centers.get(n.deck) ?? { x: 0, y: 0 };
      const a = hash(n.id) * Math.PI * 2;
      const r = 40 + hash(`${n.id}#`) * 160;
      moi.set(n.id, old ? Object.assign(old, { ...n, x: old.x, y: old.y }) : { ...n, x: c.x + Math.cos(a) * r, y: c.y + Math.sin(a) * r });
    }
    simNodes.current = moi;
    const list = [...moi.values()];
    const lk = links
      .filter((l) => moi.has(l.source?.id ?? l.source) && moi.has(l.target?.id ?? l.target))
      .map((l) => ({ ...l, source: l.source?.id ?? l.source, target: l.target?.id ?? l.target }));

    if (!sim.current) {
      sim.current = forceSimulation()
        .velocityDecay(0.35)
        .on("tick", () => setFrame((f) => (f + 1) % 1e9));
    }
    const s = sim.current;
    s.nodes(list)
      .force(
        "link",
        forceLink(lk)
          .id((d) => d.id)
          .distance(140)
          .strength(0.35),
      )
      .force("charge", forceManyBody().strength(charge).distanceMax(400))
      .force("collide", forceCollide(collide))
      .force("x", forceX((d) => centers.get(d.deck)?.x ?? 0).strength(0.08))
      .force("y", forceY((d) => centers.get(d.deck)?.y ?? 0).strength(0.08));
    s.alpha(cu.size ? 0.4 : 1).restart();
    if (!cu.size) s.tick(200); // lần đầu: chạy trước cho gần yên, khỏi nhìn cả bản đồ tự bung ra
  }, [nodes, links, centers, charge, collide]);

  /** Đọc lại độ đẩy/va sau khi đổi trang đang kéo — d3 lưu sẵn chúng lúc khởi tạo. */
  const refreshForces = () => {
    sim.current?.force("charge")?.strength(charge);
    sim.current?.force("collide")?.radius(collide);
  };

  useEffect(() => () => sim.current?.stop(), []);

  // ---- biến đổi khung nhìn -------------------------------------------------
  const toWorld = useCallback((sx, sy) => {
    const { x, y, k } = tRef.current;
    return { x: (sx - x) / k, y: (sy - y) / k };
  }, []);

  const animateTo = useCallback((target) => {
    cancelAnimationFrame(anim.current);
    const from = tRef.current;
    const t0 = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - t0) / 450);
      const e = 1 - (1 - p) ** 3;
      setT({
        x: from.x + (target.x - from.x) * e,
        y: from.y + (target.y - from.y) * e,
        k: from.k + (target.k - from.k) * e,
      });
      if (p < 1) anim.current = requestAnimationFrame(step);
    };
    anim.current = requestAnimationFrame(step);
  }, []);

  const fit = useCallback(
    (ids) => {
      const pts = [...simNodes.current.values()].filter((n) => !ids || ids.includes(n.id));
      if (!pts.length) return;
      const xs = pts.map((n) => n.x);
      const ys = pts.map((n) => n.y);
      const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
      const pad = 120;
      const k = Math.max(K_MIN, Math.min(1.6, size.w / (x1 - x0 + pad * 2), size.h / (y1 - y0 + pad * 2)));
      animateTo({ k, x: size.w / 2 - ((x0 + x1) / 2) * k, y: size.h / 2 - ((y0 + y1) / 2) * k });
    },
    [size, animateTo],
  );

  // Phần khung còn nhìn thấy: khung chi tiết bên phải che mất một dải, nên
  // "đưa trang vào giữa" là giữa phần còn lại chứ không phải giữa màn hình.
  const inset = size.w >= 800 ? rightInset : 0;

  const focus = useCallback(
    (id) => {
      const n = simNodes.current.get(id);
      if (!n) return;
      const k = Math.max(tRef.current.k, 1.4);
      animateTo({ k, x: (size.w - inset) / 2 - n.x * k, y: size.h / 2 - n.y * k });
    },
    [size, inset, animateTo],
  );

  // Trang vừa chọn mà nằm khuất sau khung chi tiết thì trượt nó ra, giữ nguyên độ phóng.
  useEffect(() => {
    const n = selectedId && simNodes.current.get(selectedId);
    if (!n) return;
    const { x, y, k } = tRef.current;
    const sx = x + n.x * k;
    const sy = y + n.y * k;
    if (sx > 40 && sx < size.w - inset - 40 && sy > 40 && sy < size.h - 40) return;
    animateTo({ k, x: (size.w - inset) / 2 - n.x * k, y: size.h / 2 - n.y * k });
  }, [selectedId, inset, size, animateTo]);

  const zoomBy = useCallback(
    (f) => {
      const { x, y, k } = tRef.current;
      const k2 = Math.max(K_MIN, Math.min(K_MAX, k * f));
      const cx = size.w / 2;
      const cy = size.h / 2;
      animateTo({ k: k2, x: cx - ((cx - x) * k2) / k, y: cy - ((cy - y) * k2) / k });
    },
    [size, animateTo],
  );

  useImperativeHandle(ref, () => ({ fit, focus, zoomBy }), [fit, focus, zoomBy]);

  // Mở lần đầu: vừa màn hình. Màn hẹp thì chỉ vừa các trang đã sáng — vừa cả
  // vành trang chưa học thì mọi thứ bé như hạt bụi.
  const daMo = useRef(false);
  useEffect(() => {
    if (daMo.current || !nodes.length || size.w < 50) return;
    daMo.current = true;
    const sang = nodes.filter(isLit).map((n) => n.id);
    const id = setTimeout(() => fit(size.w < 640 && sang.length ? sang : undefined), 60);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes.length, size.w, fit]);

  // ---- chuột: cuộn để phóng to, kéo nền để di chuyển ------------------------
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      cancelAnimationFrame(anim.current);
      const r = el.getBoundingClientRect();
      const cx = e.clientX - r.left;
      const cy = e.clientY - r.top;
      setT(({ x, y, k }) => {
        const k2 = Math.max(K_MIN, Math.min(K_MAX, k * Math.exp(-e.deltaY * 0.0012)));
        return { k: k2, x: cx - ((cx - x) * k2) / k, y: cy - ((cy - y) * k2) / k };
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const local = (e) => {
    const r = wrap.current.getBoundingClientRect();
    return { sx: e.clientX - r.left, sy: e.clientY - r.top };
  };

  const onNodeDown = (e, n) => {
    if (e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    const { sx, sy } = local(e);
    const sn = simNodes.current.get(n.id);
    drag.current = { id: n.id, sx, sy, moved: false, target: null };
    sn.fx = sn.x;
    sn.fy = sn.y;
    sim.current.alphaTarget(0.25).restart();
    setDragging({ id: n.id, moved: false, target: null });
  };

  const onMove = (e) => {
    const { sx, sy } = local(e);
    if (drag.current) {
      const d = drag.current;
      if (!d.moved) {
        if (Math.hypot(sx - d.sx, sy - d.sy) <= DRAG_PX) return;
        d.moved = true;
        refreshForces();
      }
      const w = toWorld(sx, sy);
      const sn = simNodes.current.get(d.id);
      sn.fx = w.x;
      sn.fy = w.y;
      // Đang kéo một trang sáng: tìm trang sáng gần con trỏ nhất để thả nối.
      let target = null;
      if (isLit(sn)) {
        let best = Infinity;
        for (const o of simNodes.current.values()) {
          if (o.id === d.id || !isLit(o)) continue;
          const dist = Math.hypot(o.x - w.x, o.y - w.y);
          if (dist < DROP_PX / tRef.current.k + radiusOf(o) && dist < best) {
            best = dist;
            target = o.id;
          }
        }
      }
      d.target = target;
      setDragging({ id: d.id, moved: true, target });
      return;
    }
    if (pan.current) {
      const p = pan.current;
      if (!p.moved && Math.hypot(sx - p.sx, sy - p.sy) > DRAG_PX) p.moved = true;
      setT((cur) => ({ ...cur, x: p.x0 + (sx - p.sx), y: p.y0 + (sy - p.sy) }));
    }
  };

  const onUp = () => {
    if (drag.current) {
      const d = drag.current;
      const sn = simNodes.current.get(d.id);
      // Thả ra là trả trang về cho mô phỏng, như Obsidian: nó tự tìm chỗ nghỉ.
      if (sn) {
        sn.fx = null;
        sn.fy = null;
      }
      sim.current.alphaTarget(0);
      drag.current = null;
      if (d.moved) refreshForces();
      setDragging(null);
      if (!d.moved) onSelectNode?.(d.id);
      else if (d.target) onDropConnect?.(d.id, d.target);
      return;
    }
    if (pan.current) {
      if (!pan.current.moved) onBackground?.();
      pan.current = null;
    }
  };

  const onBgDown = (e) => {
    if (e.button !== 0) return;
    cancelAnimationFrame(anim.current);
    const { sx, sy } = local(e);
    pan.current = { sx, sy, x0: tRef.current.x, y0: tRef.current.y, moved: false };
  };

  // ---- ai sáng, ai mờ ----------------------------------------------------
  const all = [...simNodes.current.values()];
  const byId = simNodes.current;
  const lk = links.map((l) => ({
    ...l,
    s: byId.get(l.source?.id ?? l.source),
    d: byId.get(l.target?.id ?? l.target),
    key: [l.source?.id ?? l.source, l.target?.id ?? l.target].sort().join("|"),
  }));

  // Đang kéo thì không làm mờ theo trang dưới chuột — trang đích phải luôn rõ.
  const tam = linking || dragging?.moved ? null : (connectFrom ?? hover ?? selectedId ?? null);
  const hangXom = useMemo(() => {
    if (!tam || !isLit(byId.get(tam)) || !lk.some((l) => l.s?.id === tam || l.d?.id === tam)) return null;
    const s = new Set([tam]);
    for (const l of lk) {
      if (l.s?.id === tam) s.add(l.d?.id);
      if (l.d?.id === tam) s.add(l.s?.id);
    }
    return s;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tam, links, nodes]);

  const keoSang = dragging?.moved && isLit(byId.get(dragging.id));
  const q = (query || "").trim().toLowerCase();
  const khop = (n) => q && `${n.label} ${n.title}`.toLowerCase().includes(q);
  const canhChon = selectedEdge ? lk.find((l) => l.key === selectedEdge) : null;

  const moDinh = (n) => {
    if (linking) return n.id !== linking[0] && n.id !== linking[1];
    if (connectFrom) return n.id !== connectFrom && !isLit(n);
    if (q) return !khop(n);
    if (canhChon) return n.id !== canhChon.s?.id && n.id !== canhChon.d?.id;
    return hangXom ? !hangXom.has(n.id) : false;
  };

  const hienNhan = (n) =>
    isLit(n) ||
    n.level === "can_sua" ||
    t.k >= K_LABEL ||
    n.id === hover ||
    n.id === here ||
    n.id === selectedId ||
    hangXom?.has(n.id) ||
    khop(n);

  const preview =
    (connectFrom && hover && hover !== connectFrom && isLit(byId.get(hover)) && [connectFrom, hover]) ||
    (dragging?.target && [dragging.id, dragging.target]) ||
    null;

  return (
    <div
      ref={wrap}
      className={`absolute inset-0 touch-none select-none ${pan.current ? "cursor-grabbing" : "cursor-grab"}`}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerLeave={onUp}
    >
      <svg width={size.w} height={size.h} className="block" onPointerDown={onBgDown} role="application" aria-label="Bản đồ hiểu biết">
        <defs>
          <pattern id="luoi" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform={`translate(${t.x} ${t.y}) scale(${t.k})`}>
            <circle cx="1" cy="1" r="0.9" fill="#e5e5e5" />
          </pattern>
        </defs>
        <rect width={size.w} height={size.h} fill="url(#luoi)" />

        <g transform={`translate(${t.x} ${t.y}) scale(${t.k})`}>
          {/* Nhãn vùng của từng buổi học — chữ lớn, rất nhạt, nằm dưới mọi thứ. */}
          {decks.length > 1 &&
            decks.map((d) => {
              const pts = all.filter((n) => n.deck === d);
              if (!pts.length) return null;
              const x = pts.reduce((s, n) => s + n.x, 0) / pts.length;
              const size = chu(24, t.k, 15, 30);
              const y = Math.min(...pts.map((n) => n.y - radiusOf(n))) - size * 1.4;
              return (
                <text
                  key={d}
                  x={x}
                  y={y}
                  textAnchor="middle"
                  fontSize={size}
                  className="fill-neutral-300 font-semibold tracking-tight"
                  pointerEvents="none"
                >
                  {deckLabel?.(d) ?? d}
                </text>
              );
            })}

          {lk.map((l) => {
            if (!l.s || !l.d) return null;
            const noiBat = selectedEdge ? selectedEdge === l.key : !!hangXom && (l.s.id === tam || l.d.id === tam);
            const mo = linking || (!noiBat && (hangXom || selectedEdge || q));
            return (
              <g key={l.key}>
                <motion.line
                  x1={l.s.x}
                  y1={l.s.y}
                  x2={l.d.x}
                  y2={l.d.y}
                  initial={l.key === newEdge ? { pathLength: 0 } : false}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.9, ease: EASE }}
                  stroke={noiBat ? "#171717" : "#a3a3a3"}
                  strokeWidth={(noiBat ? 2.2 : 1.4) / Math.sqrt(t.k)}
                  opacity={mo ? 0.2 : 1}
                />
                <line
                  x1={l.s.x}
                  y1={l.s.y}
                  x2={l.d.x}
                  y2={l.d.y}
                  stroke="transparent"
                  strokeWidth={14 / t.k}
                  className="cursor-pointer"
                  onPointerDown={(e) => e.stopPropagation()}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectEdge?.(l.key);
                  }}
                >
                  <title>{`“${l.evidence}”`}</title>
                </line>
              </g>
            );
          })}

          {linking && byId.get(linking[0]) && byId.get(linking[1]) && (
            <motion.line
              x1={byId.get(linking[0]).x}
              y1={byId.get(linking[0]).y}
              x2={byId.get(linking[1]).x}
              y2={byId.get(linking[1]).y}
              stroke="#171717"
              strokeWidth={1.8 / Math.sqrt(t.k)}
              strokeDasharray="6 6"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
              pointerEvents="none"
            />
          )}
          {preview && byId.get(preview[0]) && byId.get(preview[1]) && (
            <line
              x1={byId.get(preview[0]).x}
              y1={byId.get(preview[0]).y}
              x2={byId.get(preview[1]).x}
              y2={byId.get(preview[1]).y}
              stroke="#171717"
              strokeWidth={1.6 / Math.sqrt(t.k)}
              strokeDasharray="5 5"
              pointerEvents="none"
            />
          )}

          {all.map((n) => {
            const r = radiusOf(n);
            const lit = isLit(n);
            const mo = moDinh(n);
            const chon = n.id === selectedId;
            const dich = dragging?.target === n.id || (connectFrom && hover === n.id && lit && n.id !== connectFrom);
            return (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y})`}
                opacity={mo ? 0.18 : 1}
                style={{ transition: "opacity 200ms" }}
                className={`outline-none ${dragging?.id === n.id ? "cursor-grabbing" : "cursor-pointer"}`}
                tabIndex={0}
                role="button"
                aria-label={n.title}
                onPointerDown={(e) => onNodeDown(e, n)}
                onPointerEnter={() => setHover(n.id)}
                onPointerLeave={() => setHover((h) => (h === n.id ? null : h))}
                onFocus={() => setHover(n.id)}
                onBlur={() => setHover((h) => (h === n.id ? null : h))}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectNode?.(n.id);
                  }
                }}
              >
                <title>{n.title}</title>
                {n.id === here && (
                  <circle
                    r={r + 13}
                    fill="none"
                    stroke="#171717"
                    strokeWidth={1}
                    strokeDasharray="2 3"
                    pointerEvents="none"
                  />
                )}
                {n.id === connectFrom && (
                  <motion.circle
                    r={r + 10}
                    fill="none"
                    stroke="#171717"
                    strokeWidth="1.4"
                    animate={{ opacity: [0.6, 0.15, 0.6], scale: [0.9, 1.15, 0.9] }}
                    transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                  />
                )}
                {keoSang && lit && n.id !== dragging.id && !dich && (
                  <circle r={r + 7} fill="none" stroke="#a3a3a3" strokeWidth={1.2 / t.k} strokeDasharray="3 3" />
                )}
                {(chon || dich || (hover === n.id && !mo)) && n.id !== connectFrom && (
                  <circle
                    r={r + 7}
                    fill="none"
                    stroke={chon || dich ? "#171717" : "#a3a3a3"}
                    strokeWidth="1.4"
                    strokeDasharray={dich ? "4 3" : undefined}
                  />
                )}
                {/* Ô bấm rộng hơn chấm: chấm của trang chưa học chỉ 4px. */}
                <circle r={Math.max(r, 11)} fill="transparent" />
                {n.level === "vung" && <circle r={r + 3.5} fill="none" stroke="#171717" strokeWidth="1.2" />}
                <circle
                  r={r}
                  fill={lit ? "#171717" : n.level === "dang_hoc" ? "#d4d4d4" : "#fff"}
                  stroke={n.level === "can_sua" ? "#171717" : n.level === "moi" ? "#c4c4c4" : "none"}
                  strokeWidth={n.level === "can_sua" ? 2 : 1.2}
                  strokeDasharray={n.level === "moi" ? "2.5 2.5" : undefined}
                />
                {hienNhan(n) && (
                  <text
                    y={r + 4 / t.k + chu(12, t.k)}
                    textAnchor="middle"
                    fontSize={chu(12, t.k)}
                    stroke="#fff"
                    strokeWidth={4 / t.k}
                    strokeLinejoin="round"
                    paintOrder="stroke"
                    className={lit || n.level === "can_sua" ? "fill-neutral-900 font-medium" : "fill-neutral-500"}
                    pointerEvents="none"
                  >
                    {n.label || n.title}
                  </text>
                )}
                {lit && t.k >= 0.8 && (
                  <text
                    y={r + 4 / t.k + chu(12, t.k) + chu(10, t.k, 10, 13) * 1.3}
                    textAnchor="middle"
                    fontSize={chu(10, t.k, 10, 13)}
                    stroke="#fff"
                    strokeWidth={4 / t.k}
                    strokeLinejoin="round"
                    paintOrder="stroke"
                    className="fill-neutral-400"
                    pointerEvents="none"
                  >
                    {deckLabel?.(n.deck, true)} · tr. {n.page}
                  </text>
                )}
              </g>
            );
          })}

          {/* "Bạn đang ở đây" vẽ sau cùng, dạng nhãn đen: nằm trên mọi nhãn khác
              nên không bao giờ bị tên một trang bên cạnh đè lên. */}
          {here &&
            byId.get(here) &&
            (() => {
              const n = byId.get(here);
              const fs = chu(11, t.k);
              const h = fs * 1.9;
              const w = fs * 9.4;
              return (
                <g
                  transform={`translate(${n.x} ${n.y - radiusOf(n) - 13 - h / 2 - 4 / t.k})`}
                  opacity={moDinh(n) ? 0.35 : 1}
                  pointerEvents="none"
                >
                  <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={h / 2} fill="#171717" />
                  <text textAnchor="middle" dominantBaseline="central" fontSize={fs} className="fill-white font-medium">
                    Bạn đang ở đây
                  </text>
                </g>
              );
            })()}
        </g>
      </svg>
    </div>
  );
});

export default GraphCanvas;
