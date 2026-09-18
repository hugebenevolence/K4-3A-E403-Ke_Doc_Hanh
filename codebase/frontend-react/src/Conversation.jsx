// Khung giữa: cuộc giảng bài với học trò AI.
//
// Lời học viên là bong bóng bên phải, lời học trò là văn xuôi không khung.
// Trên cùng là tiến trình Chọn · Giảng · Trả lời · Xem lại thay cho đoạn hướng
// dẫn: đoạn hướng dẫn chỉ có ích lần đầu, tiến trình thì lần nào cũng có ích.

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { blurIn, EASE } from "./motion";
import { Button, Kbd, LevelMeter, LiveDot, Stepper, WordsIn } from "./ui";

const STAGES = ["Chọn", "Giảng", "Trả lời", "Xem lại"];

/** Chạm nút nói ngắn hơn ngần này (ms) là "bấm để nói", lâu hơn là "giữ để nói". */
const TAP_MS = 300;

function stageOf(session) {
  if (!session.started) return 0;
  if (session.ended) return 3;
  return session.turns.some((t) => t.role === "student") ? 2 : 1;
}

/** Thẻ trỏ về một vị trí trên slide — bấm là khung phải nhảy tới đúng chỗ.
 *
 *  CỐ Ý không trích nguyên văn đoạn slide. Đo được trên LLM thật: trích dẫn hiện
 *  nguyên văn ngay dưới câu hỏi ngược chính là đáp án, đưa cho đúng người đang
 *  hiểu sai. Thẻ chỉ nói "ở đâu", học viên tự mở ra xem. */
function SourceCard({ span, caption, onOpen }) {
  if (!span?.page) return null;
  return (
    <motion.button
      {...blurIn}
      whileTap={{ scale: 0.99 }}
      onClick={() => onOpen(span)}
      className="group flex w-full items-center gap-3 rounded-xl border border-neutral-200 bg-white p-2 text-left transition-colors hover:border-neutral-400"
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-neutral-100 text-[13px] font-semibold tabular-nums text-neutral-700">
        {span.page}
      </span>
      <span className="min-w-0 flex-1 truncate text-[13px] text-neutral-700">{caption}</span>
      <span className="rounded-md border border-neutral-200 px-2 py-0.5 text-[12px] font-medium text-neutral-700 transition-colors group-hover:border-neutral-900 group-hover:bg-neutral-900 group-hover:text-white">
        Xem
      </span>
    </motion.button>
  );
}

export function StudentTurn({ turn }) {
  return (
    <motion.div {...blurIn} className="flex justify-end">
      <p className="m-0 max-w-[85%] rounded-2xl rounded-br-md bg-neutral-100 px-3.5 py-2.5 text-[14px] leading-relaxed text-neutral-900">
        {turn.text}
      </p>
    </motion.div>
  );
}

export function AgentTurn({ turn, span, live = false, onOpen }) {
  return (
    <motion.div
      {...blurIn}
      className="voice space-y-3 px-4 py-3.5"
      // Viền sáng chỉ chạy đúng lúc câu này đang được đọc thành tiếng. Gắn
      // theo dữ liệu chứ không theo class để CSS giữ hết phần trang trí.
      data-live={live ? "true" : undefined}
    >
      {/* Nhắc lại những ý đã nghe hiểu: học viên thấy phần nào đã ổn trước
          khi bị hỏi phần còn hổng. Chỉ hiện chữ, không đọc thành tiếng. */}
      {turn.understood?.length > 0 && (
        <div className="border-l-2 border-neutral-200 pl-3">
          <p className="m-0 text-[12px] text-neutral-400">Mình hiểu là</p>
          <ul className="m-0 mt-1 list-none space-y-0.5 p-0">
            {turn.understood.map((point, i) => (
              <motion.li
                key={point}
                initial={{ opacity: 0, filter: "blur(3px)" }}
                animate={{ opacity: 1, filter: "blur(0px)" }}
                transition={{ duration: 0.35, delay: i * 0.06, ease: EASE }}
                className="text-[13px] leading-relaxed text-neutral-600"
              >
                {point}
              </motion.li>
            ))}
          </ul>
        </div>
      )}
      <p className={`m-0 text-[14px] leading-relaxed ${turn.filler ? "text-neutral-500" : "text-neutral-900"}`}>
        <WordsIn text={turn.text} />
      </p>
      {span && <SourceCard span={span} caption="Chỗ học trò đang hỏi" onOpen={onOpen} />}
    </motion.div>
  );
}

/** Nói rõ SẼ giảng phần nào trước khi bấm, để không ai bắt đầu một phiên về
 *  chỗ mình không định giảng. */
function Ready({ target, onTeach, onClearSelection }) {
  const chosen = target.count > 0 && !target.thin;
  // Thứ tự quan trọng: lúc slide còn ĐANG TẢI thì chưa có ô nào, nên "trang này
  // không có gì để giảng" đúng về số học mà sai hoàn toàn về sự thật. Hỏi "đã
  // có slide chưa" trước, rồi mới hỏi "trang này có nội dung không".
  const detail = !target.hasSlides
    ? "Đang mở bộ slide…"
    : !target.teachable
      // Trang bìa và trang phân mục chỉ có tiêu đề: server sẽ từ chối mở phiên,
      // nên nói trước ở đây thay vì để họ bấm rồi mới biết.
      ? "Trang này chỉ có tiêu đề — lật sang một trang có nội dung nhé."
      : chosen
        ? `${target.count} phần đã chọn`
        : target.thin
          ? "Vùng chọn quá ngắn, sẽ giảng cả trang"
          : "Cả trang. Kéo trên slide để chọn một phần.";

  return (
    <div className="flex h-full flex-col justify-center">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div key={target.page} {...blurIn}>
          <p className="m-0 text-[12px] tabular-nums text-neutral-400">Slide {target.page}</p>
          <h2 className="m-0 mt-1 text-[20px] leading-snug font-semibold tracking-tight text-balance text-neutral-900">
            {target.title}
          </h2>
        </motion.div>
      </AnimatePresence>
      <AnimatePresence mode="wait" initial={false}>
        <motion.p key={detail} {...blurIn} className="m-0 mt-2 text-[13px] text-neutral-500">
          {detail}
        </motion.p>
      </AnimatePresence>

      <div className="mt-6 flex items-center gap-2">
        <Button
          variant="primary"
          size="lg"
          onClick={onTeach}
          disabled={!target.hasSlides || !target.teachable}
        >
          Bắt đầu giảng
          <Kbd tone="dark">Enter</Kbd>
        </Button>
        {target.count > 0 && (
          <Button variant="quiet" size="lg" onClick={onClearSelection}>
            Bỏ chọn
          </Button>
        )}
      </div>
    </div>
  );
}

function Ending({ ended, spanById, onOpen, onRetry, onRestart, onNext }) {
  const taught = ended.outcome === "TAUGHT";
  const review = (ended.review_spans ?? []).map((id) => spanById.get(id)).filter(Boolean);
  return (
    <motion.div {...blurIn} className="rounded-2xl border border-neutral-200 p-4">
      <p className="m-0 text-[15px] font-semibold tracking-tight text-neutral-900">
        {taught ? "Học trò đã hiểu phần này" : "Học trò chưa hiểu hết"}
      </p>
      <p className="m-0 mt-0.5 text-[13px] text-neutral-500">
        {taught ? (
          <>
            Bạn đã giảng đủ ý — học trò vừa nhớ thêm trang này.{" "}
            <Link to="/graph" className="text-neutral-900 underline underline-offset-2">
              Xem bản đồ
            </Link>
          </>
        ) : (
          "Xem lại những chỗ dưới đây rồi giảng lại."
        )}
      </p>
      {review.length > 0 && (
        <div className="mt-3 space-y-2">
          {review.map((span) => (
            <SourceCard key={span.span_id} span={span} caption="Cần xem lại" onOpen={onOpen} />
          ))}
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {taught ? (
          onNext && (
            <Button variant="primary" onClick={onNext}>
              Slide tiếp theo
            </Button>
          )
        ) : (
          <Button variant="primary" onClick={onRetry}>
            Giảng lại
          </Button>
        )}
        <Button onClick={onRestart}>Chọn phần khác</Button>
      </div>
    </motion.div>
  );
}

export function Composer({ session }) {
  const [draft, setDraft] = useState("");
  const latest = useRef(session);
  useEffect(() => {
    latest.current = session;
  });
  const { myTurn, recording, speaking, micReady, micDenied, level, partial } = session;

  function submit(e) {
    e?.preventDefault();
    const text = draft.trim();
    if (!text || !myTurn) return;
    setDraft("");
    session.send({ type: "explanation_text", text });
  }

  /** Giữ nút để nói, thả ra là gửi; chạm nhanh thì nói tới khi im lặng.
   *  Nghe pointerup trên cả cửa sổ: nút nói biến mất ngay khi bắt đầu thu,
   *  nên sự kiện thả tay không còn về tới nó. */
  function onTalkDown(e) {
    if (e.button !== 0 || !session.startTalking({ hold: true })) return;
    const pressed = performance.now();
    const up = () => {
      removeEventListener("pointerup", up);
      removeEventListener("pointercancel", up);
      if (performance.now() - pressed < TAP_MS) latest.current.releaseHold();
      else latest.current.stopTalking();
    };
    addEventListener("pointerup", up);
    addEventListener("pointercancel", up);
  }

  return (
    <div className="border-t border-neutral-200 p-3">
      <AnimatePresence mode="wait" initial={false}>
        {recording ? (
          <motion.div
            key="listening"
            {...blurIn}
            transition={{ duration: 0.2, ease: EASE }}
            className="rounded-2xl border border-neutral-900 p-3"
          >
            <div className="flex items-center gap-3">
              <LevelMeter level={level} />
              <span className="text-[13px] font-medium text-neutral-900">Đang nghe</span>
              <Button size="sm" variant="primary" className="ml-auto" onClick={() => session.stopTalking()}>
                Xong
              </Button>
            </div>
            {/* Lời đang nói hiện ngay: sai thì nói lại tại đây, trước khi gửi. */}
            <p className="m-0 mt-2 min-h-11 text-[14px] leading-relaxed text-neutral-600">
              {partial || <span className="text-neutral-300">…</span>}
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="typing"
            {...blurIn}
            transition={{ duration: 0.2, ease: EASE }}
            className={`rounded-2xl border bg-white transition-colors ${
              myTurn ? "border-neutral-300 focus-within:border-neutral-900" : "border-neutral-200"
            }`}
          >
            <textarea
              rows={2}
              value={draft}
              disabled={!myTurn}
              placeholder={myTurn ? "Nhập câu trả lời" : ""}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit(e);
              }}
              className="block w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-[14px] leading-relaxed text-neutral-900 outline-none placeholder:text-neutral-400 disabled:cursor-not-allowed"
            />
            <div className="flex items-center gap-1.5 px-2 pb-2">
              {micDenied ? (
                <span className="px-1.5 text-[12px] text-neutral-400">Không dùng được mic</span>
              ) : (
                <Button
                  size="sm"
                  disabled={!myTurn || !micReady}
                  onPointerDown={onTalkDown}
                  // Bàn phím (Enter trên nút đang focus) không có pointerdown.
                  onClick={(e) => e.detail === 0 && session.startTalking()}
                  title="Giữ để nói, thả ra để gửi"
                >
                  Giữ để nói
                  <Kbd>Space</Kbd>
                </Button>
              )}
              {speaking && (
                <Button size="sm" variant="quiet" onClick={session.skipAudio}>
                  Bỏ qua
                </Button>
              )}
              <Button
                size="sm"
                variant="primary"
                className="ml-auto"
                disabled={!myTurn || !draft.trim()}
                onClick={submit}
              >
                Gửi
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Conversation({
  session,
  target,
  spanById,
  onTeach,
  onClearSelection,
  onRestart,
  onRetry,
  onNext,
  onOpen,
}) {
  const bottom = useRef(null);
  const { turns, thinking, ended, connected } = session;

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, thinking, ended, session.partial]);

  const status = session.speaking
    ? ["speaking", "Đang nói"]
    : session.recording
      ? ["listening", "Đang nghe"]
      : thinking
        ? ["working", "Đang xử lý"]
        : ended || !connected
          ? null
          : session.myTurn
            ? ["idle", "Tới lượt bạn"]
            : ["working", "Đang kết nối"];

  const lastAgent = turns.findLastIndex((t) => t.role === "agent");

  return (
    <section className="flex min-h-0 flex-col border-r border-neutral-200 bg-white">
      <header className="flex h-12 shrink-0 items-center gap-4 border-b border-neutral-200 px-4">
        <div className="min-w-0 flex-1">
          <Stepper steps={STAGES} current={stageOf(session)} />
        </div>
        {status && (
          <div className="w-28 shrink-0 whitespace-nowrap">
            <LiveDot mode={status[0]} label={status[1]} />
          </div>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        {!connected ? (
          <Ready target={target} onTeach={onTeach} onClearSelection={onClearSelection} />
        ) : (
          <div className="space-y-5">
            {turns.map((turn, i) =>
              turn.role === "student" ? (
                <StudentTurn key={i} turn={turn} />
              ) : (
                <AgentTurn
                  key={i}
                  turn={turn}
                  live={i === lastAgent && session.speaking && !turn.filler}
                  // Câu chốt phiên không kèm thẻ: thẻ kết quả bên dưới đã chỉ
                  // đúng những chỗ cần xem lại, hiện hai lần là thừa.
                  span={ended && i === lastAgent ? null : spanById.get(turn.cites_span_id)}
                  onOpen={onOpen}
                />
              ),
            )}
            <AnimatePresence>
              {thinking && (
                <motion.p key="thinking" {...blurIn} className="m-0 text-[13px]">
                  <span className="shimmer font-medium">{thinking.steps.at(-1)?.label ?? "Đang xử lý"}</span>
                </motion.p>
              )}
            </AnimatePresence>
            {session.error && (
              <motion.div {...blurIn} className="rounded-xl bg-neutral-100 px-3.5 py-2.5 text-[13px] text-neutral-700">
                {session.error}
                {/* Hỏng ngay từ đầu thì phải có đường quay lại, không thì kẹt ở một phiên rỗng. */}
                {!turns.length && (
                  <Button size="sm" className="mt-2 block" onClick={onRestart}>
                    Chọn lại
                  </Button>
                )}
              </motion.div>
            )}
            {ended && (
              <Ending
                ended={ended}
                spanById={spanById}
                onOpen={onOpen}
                onRetry={onRetry}
                onRestart={onRestart}
                onNext={onNext}
              />
            )}
            <div ref={bottom} />
          </div>
        )}
      </div>

      {connected && !ended && <Composer session={session} />}
    </section>
  );
}
