// Trình xem slide PDF: kéo khung chọn vùng để giảng, gập vùng đó lại khi đang
// giảng, và khoanh đúng chỗ agent trỏ tới.

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { EASE } from "./motion";
import { pdfjs } from "./pdf";

/** Kéo ngắn hơn ngần này điểm ảnh thì coi là bấm, không phải kéo khung. */
const CLICK_SLOP = 5;

function intersects([ax0, ay0, ax1, ay1], [bx0, by0, bx1, by1]) {
  return ax0 < bx1 && bx0 < ax1 && ay0 < by1 && by0 < ay1;
}

function area([x0, y0, x1, y1]) {
  return (x1 - x0) * (y1 - y0);
}

function contains([x0, y0, x1, y1], [px, py]) {
  return px >= x0 && px <= x1 && py >= y0 && py <= y1;
}

/** Khung bao quanh cả vùng đang giảng. Gộp thành một khung chứ không khoét từng
 *  ô: các ô nằm sát nhau, khoét riêng thì phần chồng lên nhau bị phủ lại. */
function unionBox(boxes) {
  return [
    Math.min(...boxes.map((b) => b[0])),
    Math.min(...boxes.map((b) => b[1])),
    Math.max(...boxes.map((b) => b[2])),
    Math.max(...boxes.map((b) => b[3])),
  ];
}

/** Lề quanh vùng được làm nổi (px), để chữ sát mép không bị nhoè lẹm vào. */
const SPOTLIGHT_PAD = 8;

export default function SlideView({
  source,
  page,
  zoom,
  blocks,
  selectable,
  selectedIds,
  coveredIds,
  spotlight = false,
  revealedIds,
  focusedSpan,
  focusKey = 0,
  onSelect,
  onEmptyDrag,
  onToggleReveal,
  onPages,
}) {
  const canvas = useRef(null);
  const frame = useRef(null);
  const task = useRef(null);
  const drag = useRef(null);
  const [doc, setDoc] = useState(null);
  const [width, setWidth] = useState(0);
  const [scale, setScale] = useState(0);
  const [pageSize, setPageSize] = useState([0, 0]);
  // Đếm số lần vẽ xong: bản sao sắc nét của vùng đang giảng phải chép lại mỗi
  // khi canvas gốc vẽ lại (đổi trang, zoom, co giãn cửa sổ).
  const [renders, setRenders] = useState(0);
  const crop = useRef(null);
  const [hovered, setHovered] = useState(null);
  const [box, setBox] = useState(null);

  // source = { url, httpHeaders }: file slide nằm sau đăng nhập nên phải gửi
  // kèm token. Nơi gọi giữ nguyên object giữa các lần render, không thì mỗi
  // lần lật trang là tải lại cả file PDF.
  useEffect(() => {
    let cancelled = false;
    const loading = pdfjs.getDocument(source);
    loading.promise.then((d) => {
      if (cancelled) return;
      setDoc(d);
      onPages(d.numPages);
    }, () => {});
    return () => {
      cancelled = true;
      loading.destroy();
    };
  }, [source, onPages]);

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
    setPageSize([base.width, base.height]);
    setScale(next);
    setRenders((n) => n + 1);
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

  // Điểm nằm trong nhiều ô (chữ đặt đè lên hình) thì chọn ô NHỎ nhất: ảnh
  // timeline phủ gần cả trang ở slide 5–9, lấy ô đầu tiên là cú bấm nào vào chữ
  // cũng thành chọn cả hình.
  const blockAt = (pt) =>
    blocks
      .filter((b) => contains(b.bbox, pt))
      .sort((a, b) => area(a.bbox) - area(b.bbox))[0];

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

  // Làm mờ phần khác: nhoè và nhạt mọi thứ NGOÀI vùng đang giảng.
  //
  // Bản đầu lọc xám cả canvas — vùng đang giảng cũng nằm trên canvas đó nên cả
  // trang cùng xám, chẳng có gì nổi lên. Bản thứ hai phủ backdrop-filter khoét
  // lỗ bằng clip-path, nhưng Chrome vẫn làm nhoè cả phần trong lỗ. Cách chắc
  // chắn: nhoè cả canvas, rồi chép phần điểm ảnh sắc nét của đúng vùng đó lên
  // một canvas nhỏ đặt đè lên trên (CSS filter không đụng tới điểm ảnh gốc).
  const focusBlocks = selectable ? [] : blocks.filter((b) => selectedIds.has(b.span_id));
  const [pageW, pageH] = [pageSize[0] * scale, pageSize[1] * scale];
  const focusBox =
    spotlight && focusBlocks.length && scale
      ? unionBox(focusBlocks.map((b) => b.bbox)).map((v) => v * scale)
      : null;
  const hole = focusBox && [
    Math.max(0, focusBox[0] - SPOTLIGHT_PAD),
    Math.max(0, focusBox[1] - SPOTLIGHT_PAD),
    Math.min(pageW, focusBox[2] + SPOTLIGHT_PAD),
    Math.min(pageH, focusBox[3] + SPOTLIGHT_PAD),
  ];
  const holeKey = hole ? hole.map((v) => v.toFixed(1)).join(",") : "";

  useEffect(() => {
    const src = canvas.current;
    const dst = crop.current;
    if (!holeKey || !src || !dst || !pageW) return;
    const [x0, y0, x1, y1] = holeKey.split(",").map(Number);
    const ratio = src.width / pageW; // điểm ảnh canvas trên mỗi px CSS
    dst.width = Math.round((x1 - x0) * ratio);
    dst.height = Math.round((y1 - y0) * ratio);
    dst.getContext("2d").drawImage(src, x0 * ratio, y0 * ratio, dst.width, dst.height, 0, 0, dst.width, dst.height);
  }, [holeKey, renders, pageW]);

  return (
    <div
      ref={frame}
      className={`group/slide relative mx-auto w-fit select-none overflow-hidden rounded-xl border border-neutral-200 bg-white leading-0 shadow-[0_1px_3px_rgb(0_0_0/0.04),0_8px_24px_rgb(0_0_0/0.04)] ${
        selectable ? "cursor-crosshair" : ""
      }`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={() => !drag.current && setHovered(null)}
    >
      <canvas
        ref={canvas}
        className={`block transition-[filter] duration-300 ${hole ? "blur-[3px] grayscale" : ""}`}
      />

      <AnimatePresence>
        {hole && (
          <motion.div
            key="veil"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="pointer-events-none absolute inset-0 bg-white/55"
          />
        )}
      </AnimatePresence>
      {hole && (
        <motion.canvas
          ref={crop}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, ease: EASE }}
          style={{ left: hole[0], top: hole[1], width: hole[2] - hole[0], height: hole[3] - hole[1] }}
          className="pointer-events-none absolute rounded-lg shadow-[0_0_0_1px_rgb(0_0_0/0.08),0_12px_32px_rgb(0_0_0/0.14)]"
        />
      )}

      {scale > 0 && (
        <div className="pointer-events-none absolute inset-0">
          {/* Khi đang chọn: viền quanh mọi ô chọn được, để học viên thấy slide
              được chia thành những ô nào. Chỉ hiện khi rê chuột vào slide —
              viền đứt phủ kín cả trang lúc chỉ đang đọc thì rối mắt. */}
          {selectable &&
            // Hình vẽ trước (nằm dưới), ô chữ vẽ sau (nằm trên): ô chữ đặt đè lên
            // hình vẫn nhìn thấy viền của chính nó.
            [...blocks].sort((a, b) => (a.kind === "figure" ? -1 : 0) - (b.kind === "figure" ? -1 : 0)).map((b) => {
              const on = selectedIds.has(b.span_id);
              const hover = b.span_id === hovered;
              const figure = b.kind === "figure";
              const idle = !on && !hover;
              return (
                <div
                  key={b.span_id}
                  style={style(b.bbox)}
                  className={`absolute rounded-md border transition duration-200 ${
                    on
                      ? "border-neutral-900 bg-neutral-900/7"
                      : hover
                        ? "border-neutral-600 bg-neutral-900/4"
                        : figure
                          ? "border-dotted border-neutral-500/70"
                          : "border-dashed border-neutral-400/60"
                  } ${idle ? "opacity-0 group-hover/slide:opacity-100" : ""}`}
                >
                  {/* Nhãn "Hình": sơ đồ và ảnh cũng giảng được, không chỉ chữ —
                      và nhìn là biết ô này là cả hình, không phải một dòng chữ. */}
                  {figure && (
                    <span
                      className={`absolute top-1 left-1 rounded px-1.5 py-0.5 text-[10px] leading-none font-medium ${
                        on || hover ? "bg-neutral-900 text-white" : "bg-white/90 text-neutral-600 ring-1 ring-neutral-300"
                      }`}
                    >
                      Hình
                    </span>
                  )}
                </div>
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
          được. Mỗi ô bật tắt riêng: bấm để xem đúng chỗ đang bí, xem xong bấm
          lại để che và giảng tiếp — không phải lên thanh công cụ tìm nút. */}
      {scale > 0 &&
        covered.map((b) => {
          const open = revealedIds.has(b.span_id);
          // Nhãn chỉ hiện trên ô đủ rộng. Slide sơ đồ có hàng chục nhãn chữ
          // tí hon; nhét chữ vào từng ô là ra một đống nhãn đè lên nhau.
          const roomy = (b.bbox[2] - b.bbox[0]) * scale >= 150 && (b.bbox[3] - b.bbox[1]) * scale >= 26;
          return (
            <button
              key={`cover-${b.span_id}`}
              style={style(b.bbox)}
              onClick={() => onToggleReveal(b.span_id)}
              aria-pressed={open}
              title={open ? "Bấm để che lại" : "Bấm để xem"}
              className="group/cover absolute grid cursor-pointer place-items-center rounded-md"
            >
              <AnimatePresence>
                {!open && (
                  // Che "kéo rèm" từ trái sang, mở thì rút về — nhìn là biết
                  // vùng này đang bị che chứ không phải slide vẽ lỗi.
                  <motion.span
                    key="cover"
                    className="cover absolute inset-0 rounded-md"
                    initial={{ opacity: 0, clipPath: "inset(0 100% 0 0 round 6px)" }}
                    animate={{ opacity: 1, clipPath: "inset(0 0% 0 0 round 6px)" }}
                    exit={{ opacity: 0, clipPath: "inset(0 0 0 100% round 6px)" }}
                    transition={{ duration: 0.45, ease: EASE }}
                  />
                )}
              </AnimatePresence>
              {/* Đang mở: viền đứt hiện khi rê chuột, để biết bấm vào đây là che lại. */}
              {open && (
                <span className="absolute inset-0 rounded-md border-[1.5px] border-dashed border-transparent transition-colors group-hover/cover:border-neutral-900/70" />
              )}
              {roomy && (
                <span
                  className={`relative rounded-full bg-neutral-900 px-2.5 py-1 text-[11px] leading-none font-medium whitespace-nowrap text-white shadow-sm transition-opacity duration-200 ${
                    open ? "opacity-0 group-hover/cover:opacity-100" : ""
                  }`}
                >
                  {open ? "Bấm để che" : "Bấm để xem"}
                </span>
              )}
            </button>
          );
        })}
    </div>
  );
}
