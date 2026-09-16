// Hiển thị slide PDF và tô sáng đúng vùng đang dạy.
//
// Học viên nhìn slide rồi dạy lại ngay tại đó — đúng bối cảnh dùng thật trên
// VLearn, thay vì một khung chat rời rạc không biết đang nói về cái gì.

import * as pdfjs from "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.6.82/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.6.82/pdf.worker.min.mjs";

const canvas = document.getElementById("slide");
const marks = document.getElementById("marks");
const pageNow = document.getElementById("page-now");
const pageTotal = document.getElementById("page-total");
const pageList = document.getElementById("page-list");

let doc = null;
let current = 1;
let spans = [];
let rendering = false;

export async function loadSlides(url, lessonSpans) {
  spans = lessonSpans.filter((s) => s.page && s.bbox);
  doc = await pdfjs.getDocument(url).promise;
  pageTotal.textContent = doc.numPages;

  const taught = new Set(spans.map((s) => s.page));
  pageList.replaceChildren(
    ...Array.from({ length: doc.numPages }, (_, i) => {
      const li = document.createElement("li");
      li.textContent = `Slide ${i + 1}`;
      if (taught.has(i + 1)) {
        li.classList.add("taught");
        li.title = "Trang đang dạy trong phiên này";
      }
      li.addEventListener("click", () => show(i + 1));
      pageList.append(li);
      return li;
    }),
  );

  await show(sourcePage());
}

export const sourcePage = () => spans[0]?.page ?? 1;

export async function show(n) {
  if (!doc || rendering) return;
  current = Math.min(Math.max(n, 1), doc.numPages);
  rendering = true;
  try {
    const page = await doc.getPage(current);
    // Vẽ vừa bề ngang khung, nhưng nhân devicePixelRatio để không bị rỗ trên
    // màn hình retina.
    const wrapWidth = canvas.parentElement.clientWidth;
    const base = page.getViewport({ scale: 1 });
    const scale = wrapWidth / base.width;
    const viewport = page.getViewport({ scale: scale * devicePixelRatio });

    canvas.width = viewport.width;
    canvas.height = viewport.height;
    canvas.style.width = `${wrapWidth}px`;
    canvas.style.height = `${viewport.height / devicePixelRatio}px`;
    await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;

    drawMarks(scale, base.height);
  } finally {
    rendering = false;
  }

  pageNow.textContent = current;
  [...pageList.children].forEach((li, i) =>
    li.classList.toggle("current", i + 1 === current),
  );
}

function drawMarks(scale, pageHeight) {
  marks.replaceChildren();
  marks.style.width = `${canvas.clientWidth}px`;
  marks.style.height = `${canvas.clientHeight}px`;

  for (const span of spans.filter((s) => s.page === current)) {
    // bbox từ PyMuPDF dùng gốc TRÊN-TRÁI và đơn vị điểm của trang gốc; canvas
    // ở đây cũng vẽ từ trên xuống nên chỉ cần nhân scale, KHÔNG lật trục y.
    // (Lật y là bug kinh điển khi trộn toạ độ PyMuPDF với API gốc dưới-trái
    // của PDF.js — chỗ này không rơi vào vì ta tự vẽ overlay.)
    const [x0, y0, x1, y1] = span.bbox;
    const box = document.createElement("div");
    box.className = "mark";
    box.style.left = `${x0 * scale}px`;
    box.style.top = `${y0 * scale}px`;
    box.style.width = `${(x1 - x0) * scale}px`;
    box.style.height = `${(y1 - y0) * scale}px`;
    box.title = span.span_id;
    marks.append(box);
  }
}

export function step(delta) {
  show(current + delta);
}
