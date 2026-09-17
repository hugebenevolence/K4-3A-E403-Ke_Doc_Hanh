// Box trích dẫn slide gắn dưới câu của agent.
//
// Cố ý KHÔNG có panel "đối chiếu từng ý": nó chiếm nửa màn hình để kể lại thứ
// học viên vừa nói, trong khi việc chính của họ là DẠY. Và nó từng gây hại
// thật — bộ chấm đánh nhầm là "đã nói tới" thì panel in luôn nguyên văn đáp án
// ra, thành ra vừa khen sai vừa lộ bài.
//
// Một box gọn dưới câu agent là đủ: thấy nó dựa vào chữ nào, nhảy tới được chỗ
// đó, hết. Xem lại toàn bộ căn cứ là việc của log phiên cho giảng viên.

import { focusSpan, show } from "./slides.js";

let spanIndex = new Map();

export function indexSpans(spans) {
  spanIndex = new Map(spans.map((s) => [s.span_id, s]));
}

export function citationBox(spanId) {
  const span = spanIndex.get(spanId);
  if (!span) return null;

  const box = document.createElement("figure");
  box.className = "citation";

  const label = document.createElement("figcaption");
  label.textContent = span.page ? `Slide ${span.page}` : "Nguồn";

  const quote = document.createElement("blockquote");
  quote.textContent = span.text;

  box.append(label, quote);

  if (span.page) {
    const jump = document.createElement("button");
    jump.className = "jump";
    jump.textContent = "Xem trên slide";
    jump.addEventListener("click", () => {
      show(span.page);
      focusSpan(span.span_id);
    });
    box.append(jump);
  }
  return box;
}
