// Cột phải: hội thoại dạy-lại và chỗ học viên nói/gõ.

import { useState } from "react";
import { Button, Eyebrow, LevelMeter } from "./ui";

function Citation({ span, onJump }) {
  if (!span) return null;

  return (
    <figure className="mt-2 mb-0 mx-0 rounded-lg bg-neutral-100 border-l-2 border-neutral-900 px-3 py-2">
      <figcaption>
        <Eyebrow>{span.page ? `Slide ${span.page}` : "Nguồn"}</Eyebrow>
      </figcaption>
      <blockquote className="m-0 mt-1 text-[13px] text-neutral-600">{span.text}</blockquote>
      <button
        onClick={() => onJump(span)}
        className="mt-2 text-[13px] text-neutral-900 underline underline-offset-2 hover:text-neutral-500"
      >
        Xem trên slide
      </button>
    </figure>
  );
}

function Turn({ turn, spanById, onJump }) {
  const mine = turn.role === "student";
  return (
    <div className={`mb-4 ${turn.filler ? "text-neutral-400 italic" : ""}`}>
      <Eyebrow>{mine ? "Bạn" : "Học trò AI"}</Eyebrow>
      <p className={`m-0 mt-0.5 ${mine ? "font-semibold" : ""}`}>{turn.text}</p>
      <Citation span={spanById.get(turn.cites_span_id)} onJump={onJump} />
    </div>
  );
}

export default function TeachPanel({ session, spanById, onJump }) {
  const [draft, setDraft] = useState("");
  const { turns, partial, myTurn, recording, silent, level } = session;

  function submitText(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || !myTurn) return;
    setDraft("");
    session.send({ type: "explanation_text", text });
  }

  return (
    <section className="flex flex-col gap-3 overflow-y-auto border-l border-neutral-200 bg-white p-4">
      <p className="m-0 rounded-lg bg-neutral-100 px-3 py-2.5 text-[13px] text-neutral-600">
        Giải thích bằng lời của bạn, đừng đọc lại. Học trò AI sẽ hỏi lại chỗ nó chưa
        hiểu. Đây là buổi luyện tập — không ai chấm điểm bạn.
      </p>

      <div
        aria-live="polite"
        className="flex-1 min-h-32 overflow-y-auto rounded-xl border border-neutral-200 p-3 text-[15px]"
      >
        {turns.map((turn, i) => (
          <Turn key={i} turn={turn} spanById={spanById} onJump={onJump} />
        ))}
        {/* Chữ chạy theo lời đang nói. Để ngay dưới các lượt đã xong, cùng cỡ
            chữ — học viên thấy lời mình đang thành hình đúng chỗ nó sẽ nằm,
            chứ không phải một dòng ghi chú lạc ở đáy màn hình. */}
        {partial && <p className="m-0 mb-4 text-neutral-400">{partial}</p>}
        {session.ended && (
          <p className="m-0 font-semibold">
            {session.ended.outcome === "TAUGHT"
              ? "Học trò AI đã hiểu. Xong phiên."
              : "Kết phiên — còn một chỗ nên xem lại."}
          </p>
        )}
      </div>

      {session.error && (
        <p className="m-0 rounded-lg bg-neutral-100 px-3 py-2 text-[13px] italic text-neutral-500">
          {session.error}
        </p>
      )}

      {/* Vạch mức âm đứng trước cả chữ chạy: nó nhúc nhích ngay khi có tiếng,
          còn chữ thì mất 1–2 giây mới về. Không có nó, khoảng lặng đầu lượt là
          lúc học viên không biết mic có ăn hay không và thường nói lại từ đầu. */}
      {recording && (
        <div className="flex items-center gap-3 rounded-lg border border-neutral-900 px-3 py-2">
          <LevelMeter level={level} />
          <span className="text-[13px] text-neutral-600">Đang nghe</span>
          <Button className="ml-auto" onClick={() => session.send({ type: "explanation_done" })}>
            Xong
          </Button>
        </div>
      )}

      {!session.connected && (
        <Button variant="primary" onClick={session.start}>
          Bắt đầu phiên
        </Button>
      )}

      {/* Gõ chữ luôn có mặt, không phải chỉ khi mic hỏng: 9–16h là giờ dùng cao
          điểm, tức đang ngồi trong lớp. Bắt buộc phải nói ra miệng là loại bỏ
          phần lớn bối cảnh dùng thật. */}
      <form className="flex gap-2" onSubmit={submitText}>
        <textarea
          rows={2}
          value={draft}
          disabled={!myTurn}
          placeholder={
            silent ? "Gõ lời giải thích (Ctrl+Enter để gửi)" : "…hoặc gõ, nếu chỗ bạn ngồi không nói được"
          }
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitText(e);
          }}
          className="flex-1 resize-y rounded-lg border border-neutral-200 px-3 py-2 text-[13px] outline-none focus:border-neutral-900 disabled:bg-neutral-100"
        />
        <Button variant="primary" type="submit" disabled={!myTurn || !draft.trim()}>
          Gửi
        </Button>
      </form>

      <label className="flex items-center gap-2 text-[13px] text-neutral-500">
        <input
          type="checkbox"
          checked={silent}
          onChange={(e) => session.setSilent(e.target.checked)}
          className="accent-neutral-900"
        />
        Chế độ im lặng — không bật mic, chỉ gõ chữ
        {session.micDenied && " (mic không dùng được)"}
      </label>
    </section>
  );
}
