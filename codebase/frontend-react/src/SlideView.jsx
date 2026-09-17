// Trình xem slide PDF, tô khung đúng vùng đang dạy.

import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { useCallback, useEffect, useRef, useState } from "react";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export default function SlideView({ url, spans, page, zoom, focusedSpan, focusKey = 0, onPages }) {
  const canvas = useRef(null);
  const frame = useRef(null);
  const task = useRef(null);
  const [doc, setDoc] = useState(null);
  const [marks, setMarks] = useState([]);
  const [width, setWidth] = useState(0);

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
    const scale = cssWidth / base.width;
    // Nhân devicePixelRatio để không bị rỗ trên màn hình retina.
    const viewport = pdfPage.getViewport({ scale: scale * devicePixelRatio });

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

    // bbox của PyMuPDF dùng gốc TRÊN-TRÁI, overlay này cũng vẽ từ trên xuống
    // nên chỉ nhân scale, KHÔNG lật trục y.
    setMarks(
      spans
        .filter((s) => s.page === page && s.bbox)
        .map(({ span_id, bbox: [x0, y0, x1, y1] }) => ({
          span_id,
          style: {
            left: `${x0 * scale}px`,
            top: `${y0 * scale}px`,
            width: `${(x1 - x0) * scale}px`,
            height: `${(y1 - y0) * scale}px`,
          },
        })),
    );
  }, [doc, page, zoom, spans, width]);

  useEffect(() => {
    render();
  }, [render]);

  return (
    <div
      ref={frame}
      className="relative w-fit max-w-none overflow-hidden rounded-xl border border-neutral-200 bg-white leading-0 shadow-[0_1px_3px_rgb(0_0_0/0.04),0_8px_24px_rgb(0_0_0/0.04)]"
    >
      <canvas ref={canvas} className="block" />
      <div className="pointer-events-none absolute inset-0">
        {marks.map((m) => (
          <div
            // key đổi theo vùng đang chọn để animation "đáp xuống" chạy lại
            // mỗi lần học viên bấm Mở, kể cả khi mở lại đúng vùng cũ.
            key={m.span_id === focusedSpan ? `${m.span_id}-${focusKey}` : m.span_id}
            className={`mark${m.span_id === focusedSpan ? " focused" : ""}`}
            style={m.style}
          />
        ))}
      </div>
    </div>
  );
}
