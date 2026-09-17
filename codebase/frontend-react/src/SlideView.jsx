// Trình xem slide PDF: kéo khung chọn vùng để giảng, gập vùng đó lại khi đang
// giảng, và khoanh đúng chỗ agent trỏ tới.

import { AnimatePresence, motion } from "motion/react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { useCallback, useEffect, useRef, useState } from "react";
import { EASE } from "./motion";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/** Kéo ngắn hơn ngần này điểm ảnh thì coi là bấm, không phải kéo khung. */
const CLICK_SLOP = 5;

function intersects([ax0, ay0, ax1, ay1], [bx0, by0, bx1, by1]) {
  return ax0 < bx1 && bx0 < ax1 && ay0 < by1 && by0 < ay1;
}

function contains([x0, y0, x1, y1], [px, py]) {
  return px >= x0 && px <= x1 && py >= y0 && py <= y1;
}

export default function SlideView({
  url,
  page,
  zoom,
  blocks,
  selectable,
  selectedIds,
  coveredIds,
  revealed,
  focusedSpan,
  focusKey = 0,
  onSelect,
  onEmptyDrag,
  onReveal,
  onPages,
}) {
  const canvas = useRef(null);
  const frame = useRef(null);
  const task = useRef(null);
  const drag = useRef(null);
  const [doc, setDoc] = useState(null);
  const [width, setWidth] = useState(0);
  const [scale, setScale] = useState(0);
  const [hovered, setHovered] = useState(null);
  const [box, setBox] = useState(null);

  useEffect(() => {
    let cancelled = false;
    pdfjs.getDocument(url).promise.then((d) => {
      if (cancelled) return;
      setDoc(d);
      onPages(d.numPages);
    });
    return () => {
      cancelled = true;
    };
  }, [url, onPages]);

  // Vẽ lại theo bề ngang thật của khung. Bố cục ba cột co giãn theo cửa sổ, nên
  // vẽ một lần lúc mở là slide nhoè khi phóng to cửa sổ và tràn khi thu nhỏ.
  useEffect(() => {
    const el = frame.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const render = useCallback(async () => {
    if (!doc || !canvas.current || !width) return;
    const pdfPage = await doc.getPage(Math.min(Math.max(page, 1), doc.numPages));

    const cssWidth = width * zoom;
    const base = pdfPage.getViewport({ scale: 1 });
    const next = cssWidth / base.width;
    // Nhân devicePixelRatio để không bị rỗ trên màn hình retina.
    const viewport = pdfPage.getViewport({ scale: next * devicePixelRatio });

    // Kéo giãn cửa sổ bắn ra hàng loạt lần vẽ liên tiếp; PDF.js báo lỗi nếu
    // hai lần vẽ cùng dùng một canvas. Huỷ lần cũ trước khi vẽ lần mới.
    task.current?.cancel();
    canvas.current.width = viewport.width;
    canvas.current.height = viewport.height;
    canvas.current.style.width = `${cssWidth}px`;
    canvas.current.style.height = `${viewport.height / devicePixelRatio}px`;
    const current = pdfPage.render({ canvasContext: canvas.current.getContext("2d"), viewport });
    task.current = current;
    try {
      await current.promise;
    } catch (err) {
      if (err?.name === "RenderingCancelledException") return;
      throw err;
    }
    setScale(next);
  }, [doc, page, zoom, width]);

  useEffect(() => {
    render();
  }, [render]);

  // bbox của PyMuPDF dùng gốc TRÊN-TRÁI, overlay cũng vẽ từ trên xuống nên chỉ
  // nhân scale, KHÔNG lật trục y.
  const style = ([x0, y0, x1, y1]) => ({
    left: x0 * scale,
    top: y0 * scale,
    width: (x1 - x0) * scale,
    height: (y1 - y0) * scale,
  });

  /** Toạ độ chuột → toạ độ PDF (điểm), cùng hệ với bbox. */
  function toPdf(e) {
    const r = frame.current.getBoundingClientRect();
    return [(e.clientX - r.left) / scale, (e.clientY - r.top) / scale];
  }

  const blockAt = (pt) => blocks.find((b) => contains(b.bbox, pt));

  function onPointerDown(e) {
    if (!selectable || !scale || e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { start: toPdf(e), screen: [e.clientX, e.clientY] };
  }

  function onPointerMove(e) {
    if (!selectable || !scale) return;
    const pt = toPdf(e);
    if (!drag.current) {
      setHovered(blockAt(pt)?.span_id ?? null);
      return;
    }
    const [sx, sy] = drag.current.start;
    const rect = [Math.min(sx, pt[0]), Math.min(sy, pt[1]), Math.max(sx, pt[0]), Math.max(sy, pt[1])];
    setBox(rect);
    // Hiện ngay những ô sẽ được chọn trong lúc còn đang kéo, để học viên chỉnh
    // khung trước khi thả tay chứ không phải thả ra rồi mới biết mình chọn gì.
    onSelect(blocks.filter((b) => intersects(b.bbox, rect)).map((b) => b.span_id));
  }

  function onPointerUp(e) {
    if (!drag.current) return;
    const started = drag.current;
    const [x, y] = started.screen;
    const moved = Math.hypot(e.clientX - x, e.clientY - y);
    drag.current = null;
    setBox(null);
    if (moved < CLICK_SLOP) {
      // Bấm vào một ô = chọn đúng ô đó. Dữ liệu chatlog cho thấy học viên hay
      // chỉ bôi một thuật ngữ, nên một cú bấm phải đủ, không bắt kéo khung.
      const hit = blockAt(toPdf(e));
      onSelect(hit ? [hit.span_id] : []);
      return;
    }
    // Kéo trúng hình minh hoạ: chữ nằm trong ảnh thì PDF không có text, nên
    // không có ô nào để chọn. Im lặng ở đây là học viên tưởng tính năng hỏng.
    const [sx, sy] = started.start;
    const pt = toPdf(e);
    const rect = [Math.min(sx, pt[0]), Math.min(sy, pt[1]), Math.max(sx, pt[0]), Math.max(sy, pt[1])];
    if (!blocks.some((b) => intersects(b.bbox, rect))) onEmptyDrag?.();
  }

  const covered = blocks.filter((b) => coveredIds.has(b.span_id));

  return (
    <div
      ref={frame}
      className={`relative w-fit select-none overflow-hidden rounded-xl border border-neutral-200 bg-white leading-0 shadow-[0_1px_3px_rgb(0_0_0/0.04),0_8px_24px_rgb(0_0_0/0.04)] ${
        selectable ? "cursor-crosshair" : ""
      }`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={() => !drag.current && setHovered(null)}
    >
      <canvas ref={canvas} className="block" />

      {scale > 0 && (
        <div className="pointer-events-none absolute inset-0">
          {/* Khi đang chọn: viền mờ quanh mọi ô chọn được, để học viên thấy
              slide được chia thành những ô nào trước khi kéo. */}
          {selectable &&
            blocks.map((b) => {
              const on = selectedIds.has(b.span_id);
              const hover = b.span_id === hovered;
              return (
                <div
                  key={b.span_id}
                  style={style(b.bbox)}
                  className={`absolute rounded-md border transition-colors duration-150 ${
                    on
                      ? "border-neutral-900 bg-neutral-900/7"
                      : hover
                        ? "border-neutral-600 bg-neutral-900/4"
                        : "border-dashed border-neutral-400/60"
                  }`}
                />
              );
            })}

          {/* Trong phiên: chỉ còn khung quanh vùng đang giảng, để vẫn biết mình
              đang giảng chỗ nào. */}
          {!selectable &&
            blocks
              .filter((b) => selectedIds.has(b.span_id))
              .map((b) => (
                <div
                  key={b.span_id === focusedSpan ? `${b.span_id}-${focusKey}` : b.span_id}
                  style={style(b.bbox)}
                  className={`mark${b.span_id === focusedSpan ? " focused" : ""}`}
                />
              ))}

          {box && (
            <div
              style={style(box)}
              className="absolute rounded-md border border-neutral-900 bg-neutral-900/4"
            />
          )}
        </div>
      )}

      {/* Gập vùng đang giảng: Feynman bảo "đừng nhìn ghi chú" — nhìn chữ trên
          slide mà đọc lại thì không còn là giảng, và bộ chấm không phân biệt
          được. Bấm vào thì mở ra (bước xem lại nguồn). */}
      <AnimatePresence>
        {scale > 0 &&
          !revealed &&
          covered.map((b) => (
            <motion.button
              key={`cover-${b.span_id}`}
              style={style(b.bbox)}
              initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
              animate={{ opacity: 1, backdropFilter: "blur(8px)" }}
              exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
              transition={{ duration: 0.35, ease: EASE }}
              onClick={onReveal}
              title="Đang giảng phần này — bấm để xem lại"
              className="absolute flex items-center justify-center overflow-hidden rounded-md border border-neutral-200 bg-neutral-100/85 px-2 text-[11px] leading-none font-medium text-neutral-500 hover:text-neutral-900"
            >
              {/* Ô nhỏ (như một dòng link) không đủ chỗ cho cả câu: cắt bớt
                  thay vì để chữ tràn ra đè lên phần slide bên ngoài. */}
              <span className="truncate">Đang giảng phần này · bấm để xem lại</span>
            </motion.button>
          ))}
      </AnimatePresence>
    </div>
  );
}
