// Cột phải: hội thoại dạy-lại và các nút điều khiển lượt nói.

import { useState } from "react";
import { Button, Eyebrow } from "./ui";

function Citation({ span, onJump }) {
  if (!span) return null;
  const where = span.page
    ? `Slide ${span.page}`
    : span.lines
      ? `Dòng ${span.lines[0]}–${span.lines[1]}`
      : "Nguồn";

  return (
    <figure className="mt-2 mb-0 mx-0 rounded-lg bg-neutral-100 border-l-2 border-neutral-900 px-3 py-2">
      <figcaption>
        <Eyebrow>{where}</Eyebrow>
      </figcaption>
      <blockquote className="m-0 mt-1 text-[13px] text-neutral-600">
        {span.text}
      </blockquote>
      <button
        onClick={() => onJump(span)}
        className="mt-2 text-[13px] text-neutral-900 underline underline-offset-2 hover:text-neutral-500"
      >
        {span.page ? "Xem trên slide" : "Xem trong code"}
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
  const { turns, partial, myTurn, recording } = session;

  function submitText(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || !myTurn) return;
    setDraft("");
    session.send({ type: "explanation_text", text, code: session.code });
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
        {session.ended && (
          <p className="m-0 font-semibold">
            {session.ended.outcome === "TAUGHT"
              ? "Học trò AI đã hiểu. Xong phiên."
              : "Kết phiên — còn một chỗ nên xem lại."}
          </p>
        )}
      </div>

      {(partial || session.error) && (
        <p className="m-0 rounded-lg bg-neutral-100 px-3 py-2 text-[13px] italic text-neutral-500">
          {session.error || partial}
        </p>
      )}

      <div className="flex items-center gap-2">
        <Button variant="primary" onClick={session.start} disabled={session.connected}>
          Bắt đầu phiên
        </Button>
        <Button
          onClick={async () => (await session.openMic()) && session.setRecording(true)}
          disabled={!myTurn || recording}
        >
          Bật micro
        </Button>
        <Button
          onClick={() => session.send({ type: "explanation_done", code: session.code })}
          disabled={!myTurn || !recording}
        >
          Xong
        </Button>
        <kbd className="ml-auto rounded border border-b-2 border-neutral-200 px-1.5 py-0.5 text-[11px] text-neutral-400">
          Space
        </kbd>
      </div>

      <form className="flex gap-2" onSubmit={submitText}>
        <textarea
          rows={2}
          value={draft}
          disabled={!myTurn}
          placeholder="…hoặc gõ lời giải thích (Ctrl+Enter để gửi)"
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
    </section>
  );
}
