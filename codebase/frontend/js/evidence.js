// Panel "agent đối chiếu với slide".
//
// Đây là phần làm cho hệ thống "thật": thay vì chỉ ném ra một câu hỏi, nó cho
// thấy ĐÚNG những ý nào trên slide agent đã xét, ý nào bạn đã nói tới, ý nào
// chưa — kèm nguyên văn chữ trên slide và đường nhảy tới đúng chỗ đó.
//
// Dữ liệu là thật: `evidence` do node chấm trả về, chính là căn cứ model dùng
// để quyết định. Không có gì được dựng lên cho đẹp.
//
// Theo HIG (patterns/feedback): đặt phản hồi trạng thái NGAY CẠNH thứ mà nó mô
// tả, để người dùng nắm được mà không phải rời khỏi việc đang làm.

import { show } from "./slides.js";

const panel = document.getElementById("evidence");
const list = document.getElementById("evidence-list");

let spanIndex = new Map();

export function indexSpans(spans) {
  spanIndex = new Map(spans.map((s) => [s.span_id, s]));
}

export function clearEvidence() {
  panel.hidden = true;
  list.replaceChildren();
}

export function renderEvidence(evidence) {
  if (!evidence?.length) return clearEvidence();

  list.replaceChildren(
    ...evidence.map((item) => {
      const span = spanIndex.get(item.span_id);
      const li = document.createElement("li");
      li.className = item.covered_by_student ? "covered" : "missing";

      const mark = document.createElement("span");
      mark.className = "state-dot";
      // Chữ chứ không chỉ màu — HIG yêu cầu phản hồi không phụ thuộc riêng
      // vào màu sắc, để người mù màu và VoiceOver vẫn nhận được.
      mark.textContent = item.covered_by_student ? "Đã nói" : "Chưa nói";

      const quote = document.createElement("blockquote");
      quote.textContent = span?.text ?? item.quote ?? "";

      li.append(mark, quote);

      if (span?.page) {
        const jump = document.createElement("button");
        jump.className = "jump";
        jump.textContent = `Xem trên slide ${span.page}`;
        jump.addEventListener("click", () => show(span.page));
        li.append(jump);
      }
      return li;
    }),
  );
  panel.hidden = false;
}
