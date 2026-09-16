// Trích dẫn slide: box gắn dưới câu của agent, và panel căn cứ sau mỗi lượt.
//
// Đây là phần làm cho hệ thống "thật": thay vì ném ra một câu hỏi, nó cho thấy
// ĐÚNG chữ nào trên slide mà nó đang dựa vào, kèm đường nhảy tới chỗ đó.
// Dữ liệu là thật — `evidence` do node chấm trả về chính là căn cứ model dùng
// để quyết định.
//
// LUẬT LỘ ĐÁP ÁN, quan trọng hơn cả phần hiển thị:
//
//   Giữa phiên, KHÔNG hiện nguyên văn của ý học viên CHƯA nói tới. Cả cơ chế
//   hỏi ngược là để họ tự tìm ra ý đó; in nó ra ngay cạnh câu hỏi thì học viên
//   chỉ việc đọc, và 15 điểm "không lộ đáp án" mất trắng.
//
//   Hết phiên thì hiện hết — lúc đó chỉ đúng chỗ cần xem lại là việc track D3
//   yêu cầu ("gợi ý học viên xem lại đoạn nào").

import { focusSpan, show } from "./slides.js";

const panel = document.getElementById("evidence");
const list = document.getElementById("evidence-list");

let spanIndex = new Map();
let revealAll = false;

export function indexSpans(spans) {
  spanIndex = new Map(spans.map((s) => [s.span_id, s]));
}

export function clearEvidence() {
  panel.hidden = true;
  list.replaceChildren();
}

export function revealEverything() {
  revealAll = true;
}

export function resetReveal() {
  revealAll = false;
}

function jumpButton(span, label) {
  const button = document.createElement("button");
  button.className = "jump";
  button.textContent = label;
  button.addEventListener("click", () => {
    show(span.page);
    focusSpan(span.span_id);
  });
  return button;
}

/** Box trích dẫn gắn ngay dưới một câu của agent. */
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
  if (span.page) box.append(jumpButton(span, "Xem trên slide"));
  return box;
}

export function renderEvidence(evidence) {
  if (!evidence?.length) return clearEvidence();

  list.replaceChildren(
    ...evidence.map((item) => {
      const span = spanIndex.get(item.span_id);
      const covered = item.covered_by_student;
      const li = document.createElement("li");
      li.className = covered ? "covered" : "missing";

      const state = document.createElement("span");
      state.className = "state-dot";
      // Chữ chứ không chỉ màu — HIG yêu cầu phản hồi không phụ thuộc riêng vào
      // màu sắc, để người mù màu và VoiceOver vẫn nhận được.
      state.textContent = covered ? "Bạn đã nói tới" : "Còn một ý chưa nói";
      li.append(state);

      const showText = covered || revealAll;
      if (showText && span) {
        const quote = document.createElement("blockquote");
        quote.textContent = span.text;
        li.append(quote);
        if (span.page) li.append(jumpButton(span, `Xem trên slide ${span.page}`));
      } else {
        const hint = document.createElement("p");
        hint.className = "withheld";
        hint.textContent = "Ý này còn để dành cho bạn tự nói ra.";
        li.append(hint);
      }
      return li;
    }),
  );
  panel.hidden = false;
}
