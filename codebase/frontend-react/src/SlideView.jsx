// Trình xem slide PDF, tô khung đúng vùng đang dạy.

import * as pdfjs from "pdfjs-dist";
import { useCallback, useEffect, useRef, useState } from "react";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export default function SlideView({ url, spans, page, zoom, focusedSpan, onPages }) {
  const canvas = useRef(null);
  const [doc, setDoc] = useState(null);
  const [marks, setMarks] = useState([]);

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

  const render = useCallback(async () => {
    if (!doc || !canvas.current) return;
    const pdfPage = await doc.getPage(Math.min(Math.max(page, 1), doc.numPages));

    const width = canvas.current.parentElement.clientWidth * zoom;
    const base = pdfPage.getViewport({ scale: 1 });
    const scale = width / base.width;
    // Nhân devicePixelRatio để không bị rỗ trên màn hình retina.
    const viewport = pdfPage.getViewport({ scale: scale * devicePixelRatio });

    canvas.current.width = viewport.width;
    canvas.current.height = viewport.height;
    canvas.current.style.width = `${width}px`;
    canvas.current.style.height = `${viewport.height / devicePixelRatio}px`;
    await pdfPage.render({
      canvasContext: canvas.current.getContext("2d"),
      viewport,
    }).promise;

    // bbox của PyMuPDF dùng gốc TRÊN-TRÁI, overlay này cũng vẽ từ trên xuống
    // nên chỉ nhân scale, KHÔNG lật trục y. (Lật y là bug kinh điển khi trộn
    // với API gốc dưới-trái của PDF.js — chỗ này không rơi vào vì tự vẽ.)
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
  }, [doc, page, zoom, spans]);

  useEffect(() => {
    render();
  }, [render]);

  return (
    <div className="relative w-full self-start overflow-hidden rounded-xl border border-neutral-200 bg-white leading-[0]">
      <canvas ref={canvas} className="block w-full" />
      <div className="pointer-events-none absolute inset-0">
        {marks.map((m) => (
          <div
            key={m.span_id}
            className={`mark${m.span_id === focusedSpan ? " focused" : ""}`}
            style={m.style}
          />
        ))}
      </div>
    </div>
  );
}
