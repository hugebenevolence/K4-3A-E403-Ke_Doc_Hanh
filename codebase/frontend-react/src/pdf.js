// PDF.js cấu hình một lần cho cả app: trình xem slide và ảnh thu nhỏ ở thư viện
// dùng chung worker, và chung một bản tài liệu đã tải cho mỗi bộ slide.

import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { deckPdf } from "./api";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export { pdfjs };

const docs = new Map();

/** Tài liệu PDF của một bộ slide, tải một lần rồi dùng lại cho mọi ảnh thu nhỏ. */
export function deckDocument(slug) {
  if (!docs.has(slug)) {
    const promise = pdfjs.getDocument(deckPdf(slug)).promise;
    // Tải hỏng (mất mạng, hết phiên) thì lần sau thử lại, đừng giữ lỗi mãi.
    promise.catch(() => docs.delete(slug));
    docs.set(slug, promise);
  }
  return docs.get(slug);
}
