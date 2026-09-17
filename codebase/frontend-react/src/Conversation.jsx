// Khung giữa: cuộc giảng bài với học trò AI.
//
// Theo khuôn hội thoại của ảnh tham chiếu: lời người dùng là bong bóng bên
// phải, lời agent là văn xuôi không khung, trước mỗi câu agent có một dòng
// "đã làm gì, mất bao lâu, vai nào làm". Dòng đó không trang trí — nó là thứ
// cho học viên thấy có một bước đối chiếu với nguồn thật, không phải AI phán.

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { AGENT_OF_STEP } from "./useSession";
import { blurIn, EASE } from "./motion";
import { Badge, Button, Eyebrow, Kbd, LevelMeter, LiveDot, RotatingWords, WordsIn } from "./ui";

function seconds(ms) {
  return Math.max(1, Math.round(ms / 1000));
}

/** Các vai đã tham gia, theo đúng thứ tự, không lặp. */
function agentsOf(steps) {
  const seen = [];
  for (const { step } of steps) {
    const who = AGENT_OF_STEP[step];
    if (who && !seen.includes(who)) seen.push(who);
  }
  return seen;
}

function AgentTrail({ agents }) {
  if (!agents.length) return null;
  return (
    <span className="flex items-center gap-1.5">
      {agents.map((who, i) => (
        <span key={who} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-neutral-300">→</span>}
          <span className="font-medium text-neutral-700">{who}</span>
        </span>
      ))}
    </span>
  );
}

/** Dòng đang làm việc: chữ lấp lánh + số giây chạy. */
function Thinking({ thinking }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const current = thinking.steps.at(-1)?.label ?? "Đang nghe lại lời bạn";
  return (
    <motion.div {...blurIn} className="flex items-center gap-2 text-[12px]">
      <span className="shimmer font-medium">{current}…</span>
      <span className="tabular-nums text-neutral-400">{seconds(now - thinking.startedAt)}s</span>
      <AgentTrail agents={agentsOf(thinking.steps)} />
    </motion.div>
  );
}

/** Thẻ trỏ về một vị trí trên slide — bấm "Mở" là khung phải nhảy tới đúng chỗ.
 *
 *  CỐ Ý không trích nguyên văn đoạn slide. Đo được trên LLM thật: trích dẫn hiện
 *  nguyên văn ngay dưới câu hỏi ngược chính là đáp án, đưa cho đúng người đang
 *  hiểu sai — mọi lớp chặn lộ đáp án ở backend bị đi vòng qua chỗ này. Thẻ chỉ
 *  nói "ở đâu", học viên tự mở ra xem khi đã chịu thử giảng. */
function SourceCard({ span, caption, onOpen }) {
  if (!span?.page) return null;
  return (
    <motion.button
      {...blurIn}
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.99 }}
      onClick={() => onOpen(span)}
      className="group mt-3 flex w-full items-center gap-3 rounded-xl border border-neutral-200 bg-white p-2.5 text-left shadow-[0_1px_2px_rgb(0_0_0/0.04)] transition-shadow hover:shadow-[0_4px_16px_rgb(0_0_0/0.06)]"
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-neutral-100 text-[13px] font-semibold tabular-nums text-neutral-700">
        {span.page}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[13px] font-medium text-neutral-900">Slide {span.page}</span>
        <span className="block truncate text-[12px] text-neutral-500">{caption}</span>
      </span>
      <span className="rounded-md border border-neutral-200 px-2 py-1 text-[12px] font-medium text-neutral-700 transition-colors group-hover:border-neutral-900 group-hover:text-neutral-900">
        Mở
      </span>
    </motion.button>
  );
}

function StudentTurn({ turn }) {
  return (
    <motion.div {...blurIn} className="flex justify-end">
      <p className="m-0 max-w-[85%] rounded-2xl rounded-br-md bg-neutral-100 px-3.5 py-2.5 text-[14px] leading-relaxed text-neutral-900">
        {turn.text}
      </p>
    </motion.div>
  );
}

function AgentTurn({ turn, span, onOpen, final }) {
  return (
    <motion.div {...blurIn} className="space-y-1.5">
      {turn.worked && (
        <p className="m-0 flex flex-wrap items-center gap-x-2 text-[12px] text-neutral-400">
          Đã nghĩ trong {seconds(turn.worked.ms)}s
          <span className="text-neutral-300">·</span>
          <AgentTrail agents={agentsOf(turn.worked.steps)} />
        </p>
      )}
      <p className="m-0 text-[14px] leading-relaxed text-neutral-800">
        <WordsIn text={turn.text} />
      </p>
      {span && (
        <SourceCard
          span={span}
          caption={final ? "Chỗ bạn vừa giảng" : "Chỗ học trò đang thắc mắc"}
          onOpen={onOpen}
        />
      )}
    </motion.div>
  );
}

function Welcome({ target, onTeach, onClearSelection }) {
  const chosen = target.count > 0 && !target.thin;
  return (
    <motion.div {...blurIn} className="flex h-full flex-col justify-center px-2 py-10">
      <Eyebrow>Kỹ thuật Feynman</Eyebrow>
      <h2 className="m-0 mt-2 text-[28px] leading-[1.15] font-semibold tracking-tight text-neutral-900">
        Giảng lại cho AI
        <br />
        <RotatingWords
          className="text-neutral-400"
          words={["để hiểu thật", "để thấy chỗ hổng", "để nhớ lâu hơn"]}
        />
      </h2>

      <ol className="m-0 mt-7 list-none space-y-3 p-0">
        {[
          ["Chọn phần muốn giảng", "Kéo khung, hoặc bấm vào một ô trên slide bên phải."],
          ["Giảng bằng lời của bạn", "Phần đã chọn sẽ gập lại — nói hoặc gõ mà không nhìn chữ."],
          ["Bị hỏi vặn đúng chỗ hổng", "Học trò AI không giảng hộ, nó chỉ hỏi chỗ bạn nói còn mơ hồ."],
          ["Mở đúng chỗ để xem lại", "Rồi giảng lại, cho tới khi học trò hiểu."],
        ].map(([title, body], i) => (
          <motion.li
            key={title}
            initial={{ opacity: 0, x: -6, filter: "blur(4px)" }}
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.45, delay: 0.15 + i * 0.08, ease: EASE }}
            className="flex gap-3"
          >
            <span className="grid size-6 shrink-0 place-items-center rounded-full border border-neutral-200 text-[11px] font-semibold text-neutral-600">
              {i + 1}
            </span>
            <span>
              <span className="block text-[13px] font-medium text-neutral-900">{title}</span>
              <span className="block text-[12px] leading-relaxed text-neutral-500">{body}</span>
            </span>
          </motion.li>
        ))}
      </ol>

      {/* Nói rõ SẼ giảng phần nào trước khi bấm, để không ai bắt đầu một phiên
          về chỗ mình không định giảng. */}
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={`${chosen ? "chosen" : "page"}-${target.page}`}
          {...blurIn}
          className="mt-7 rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-3"
        >
          <Eyebrow>{chosen ? `${target.count} ô đã chọn · slide ${target.page}` : `Cả slide ${target.page}`}</Eyebrow>
          <p className="m-0 mt-0.5 truncate text-[13px] font-medium text-neutral-900">{target.title}</p>
          {!chosen && target.hasSlides && (
            <p className="m-0 mt-0.5 text-[12px] text-neutral-500">
              {target.thin
                ? "Phần đã chọn chỉ vài chữ, như một dòng tiêu đề — chưa đủ để giảng, nên sẽ giảng cả trang."
                : "Chưa chọn vùng nào — sẽ giảng cả trang đang mở."}
            </p>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="mt-4 flex items-center gap-2">
        <Button variant="primary" size="lg" onClick={onTeach}>
          {chosen ? "Giảng phần đã chọn" : target.hasSlides ? `Giảng cả slide ${target.page}` : "Bắt đầu phiên"}
        </Button>
        {target.count > 0 && (
          <Button variant="quiet" onClick={onClearSelection}>
            Bỏ chọn
          </Button>
        )}
        <span className="ml-auto flex items-center gap-1 text-[12px] text-neutral-400">
          <Kbd>Enter</Kbd> để bắt đầu
        </span>
      </div>
    </motion.div>
  );
}

function Ending({ ended, spanById, onOpen, onRestart }) {
  const taught = ended.outcome === "TAUGHT";
  const review = (ended.review_spans ?? []).map((id) => spanById.get(id)).filter(Boolean);
  return (
    <motion.div {...blurIn} className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
      <div className="flex items-center gap-2">
        <Badge tone={taught ? "strong" : "neutral"}>{taught ? "Đã giảng được" : "Chưa xong"}</Badge>
        <span className="text-[13px] font-medium text-neutral-900">
          {taught ? "Học trò AI đã hiểu." : "Còn chỗ nên xem lại trước khi giảng tiếp."}
        </span>
      </div>
      {/* Bước "quay lại nguồn" của Feynman: chỉ tới đúng chỗ còn thiếu. */}
      {review.map((span) => (
        <SourceCard key={span.span_id} span={span} caption="Xem lại đoạn này rồi giảng lại" onOpen={onOpen} />
      ))}
      <Button className="mt-3" onClick={onRestart}>
        Giảng phần khác
      </Button>
    </motion.div>
  );
}

function Composer({ session }) {
  const [draft, setDraft] = useState("");
  const { myTurn, recording, silent, speaking, thinking, connected, micReady, level, partial } = session;

  function submit(e) {
    e?.preventDefault();
    const text = draft.trim();
    if (!text || !myTurn) return;
    setDraft("");
    session.send({ type: "explanation_text", text });
  }

  const placeholder = !connected
    ? "Bắt đầu phiên để giảng"
    : speaking
      ? "Học trò AI đang nói…  Space để bỏ qua"
      : thinking
        ? "Học trò AI đang nghĩ…"
        : !myTurn
          ? "Chờ một chút…"
          : silent
            ? "Gõ lời giảng của bạn — Ctrl+Enter để gửi"
            : "Giữ Space để nói, hoặc gõ ở đây";

  return (
    <div className="border-t border-neutral-200 bg-white p-3">
      <motion.div
        layout
        transition={{ duration: 0.3, ease: EASE }}
        className={`rounded-2xl border bg-white shadow-[0_1px_3px_rgb(0_0_0/0.05)] transition-colors ${
          recording ? "border-neutral-900" : "border-neutral-200 focus-within:border-neutral-400"
        }`}
      >
        <AnimatePresence mode="wait" initial={false}>
          {recording ? (
            <motion.div key="listening" {...blurIn} className="px-3.5 pt-3 pb-1">
              <div className="flex items-center gap-3">
                <LevelMeter level={level} />
                <span className="text-[13px] font-medium text-neutral-900">Đang nghe</span>
                <span className="text-[12px] text-neutral-400">thả Space hoặc bấm Gửi khi xong</span>
              </div>
              {/* Lời đang nói hiện ngay trong ô nhập — học viên thấy máy nghe
                  ra chữ gì trước khi gửi, sai thì nói lại ngay tại đây. */}
              <p className="m-0 mt-2 min-h-10 text-[14px] leading-relaxed text-neutral-500">
                {partial || <span className="text-neutral-300">…</span>}
              </p>
            </motion.div>
          ) : (
            <motion.textarea
              key="typing"
              {...blurIn}
              rows={2}
              value={draft}
              disabled={!myTurn}
              placeholder={placeholder}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit(e);
              }}
              className="block w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-[14px] leading-relaxed text-neutral-900 outline-none placeholder:text-neutral-400 disabled:cursor-not-allowed"
            />
          )}
        </AnimatePresence>

        <div className="flex items-center gap-2 px-2 pb-2">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg px-1.5 py-1 text-[12px] text-neutral-500 hover:text-neutral-800">
            <input
              type="checkbox"
              checked={silent}
              onChange={(e) => session.setSilent(e.target.checked)}
              className="peer sr-only"
            />
            {/* Công tắc tự vẽ bằng Tailwind: checkbox gốc trông lạc giữa giao diện. */}
            <span className="relative h-4 w-7 rounded-full bg-neutral-200 transition-colors peer-checked:bg-neutral-900 after:absolute after:top-0.5 after:left-0.5 after:size-3 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-3" />
            Chế độ im lặng
            {session.micDenied && <span className="text-neutral-400">· mic không dùng được</span>}
          </label>

          <div className="ml-auto flex items-center gap-1.5">
            {!silent && (
              <Button
                size="sm"
                pressed={recording}
                disabled={!recording && (!myTurn || !micReady)}
                onClick={() => (recording ? session.stopTalking() : session.startTalking())}
                aria-label={recording ? "Gửi lời vừa nói" : "Bấm để nói"}
              >
                {recording ? "Gửi" : "Nói"}
                {!recording && <Kbd>Space</Kbd>}
              </Button>
            )}
            {!recording && (
              <Button size="sm" variant="primary" disabled={!myTurn || !draft.trim()} onClick={submit}>
                Gửi chữ
              </Button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default function Conversation({
  session,
  concept,
  target,
  spanById,
  onTeach,
  onClearSelection,
  onRestart,
  onOpen,
}) {
  const bottom = useRef(null);
  const { turns, thinking, ended, connected } = session;

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, thinking, ended, session.partial]);

  const [mode, label] = session.speaking
    ? ["speaking", "Học trò AI đang nói"]
    : session.recording
      ? ["listening", "Đang nghe bạn giảng"]
      : thinking
        ? ["working", session.activity ?? "Học trò AI đang nghĩ"]
        : ended
          ? ["idle", "Đã kết thúc phiên"]
          : session.myTurn
            ? ["idle", "Tới lượt bạn giảng"]
            : connected
              ? ["working", "Đang kết nối"]
              : ["idle", "Chưa bắt đầu"];

  const lastAgent = turns.findLastIndex((t) => t.role === "agent");

  return (
    <section className="flex min-h-0 flex-col border-r border-neutral-200 bg-white">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-neutral-200 px-4">
        <p className="m-0 min-w-0 flex-1 truncate text-[13px] font-medium text-neutral-900">
          {connected ? concept : "Phiên giảng mới"}
        </p>
        <LiveDot mode={mode} label={label} />
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        {!connected ? (
          <Welcome target={target} onTeach={onTeach} onClearSelection={onClearSelection} />
        ) : (
          <div className="space-y-5">
            {turns.map((turn, i) =>
              turn.role === "student" ? (
                <StudentTurn key={i} turn={turn} />
              ) : (
                <AgentTurn
                  key={i}
                  turn={turn}
                  span={spanById.get(turn.cites_span_id)}
                  final={Boolean(ended) && i === lastAgent}
                  onOpen={onOpen}
                />
              ),
            )}
            <AnimatePresence>{thinking && <Thinking key="thinking" thinking={thinking} />}</AnimatePresence>
            {session.error && (
              <motion.div {...blurIn} className="rounded-xl bg-neutral-100 px-3.5 py-2.5 text-[13px] text-neutral-600">
                {session.error}
                {/* Hỏng ngay từ đầu (vd vùng chọn không còn khớp slide) thì
                    phải có đường quay lại, không thì kẹt ở một phiên rỗng. */}
                {!turns.length && (
                  <Button size="sm" className="mt-2 block" onClick={onRestart}>
                    Chọn lại
                  </Button>
                )}
              </motion.div>
            )}
            {ended && <Ending ended={ended} spanById={spanById} onOpen={onOpen} onRestart={onRestart} />}
            <div ref={bottom} />
          </div>
        )}
      </div>

      <Composer session={session} />
    </section>
  );
}
