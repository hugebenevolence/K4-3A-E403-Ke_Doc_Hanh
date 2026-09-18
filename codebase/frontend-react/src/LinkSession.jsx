// Phiên NỐI HAI TRANG, mở ngay trên bản đồ hiểu biết (spec §4c).
//
// Học viên đã giảng được từng trang; giờ giảng cho học trò hai trang đó liên
// quan gì với nhau. Cùng một cơ chế với phiên giảng thường — học trò hỏi đúng
// một câu vào chỗ hổng, không nối hộ — chỉ khác thứ được chấm là MỐI NỐI.
// Nối được thì cạnh hiện lên bản đồ, mang đúng câu học viên vừa nói.

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef } from "react";
import { AgentTurn, Composer, StudentTurn } from "./Conversation";
import { blurIn } from "./motion";
import { Button, LiveDot } from "./ui";
import { useSession } from "./useSession";

export default function LinkSession({ a, b, deckTag, onEnded, onClose }) {
  const session = useSession(undefined);
  const bottom = useRef(null);
  const spaceHeld = useRef(false);
  const { turns, thinking, ended, connected } = session;

  const open = () => session.start([], { mode: "link", a: a.id, b: b.id });

  // Mở phiên ngay khi khung hiện ra: học viên vừa chọn xong hai trang, bắt họ
  // bấm thêm một nút "Bắt đầu" nữa là thừa một bước.
  useEffect(() => {
    open();
    return () => session.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [a.id, b.id]);

  useEffect(() => {
    if (ended) onEnded?.(ended.outcome);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ended]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, thinking, ended, session.partial]);

  // Space giữ để nói — cùng phím với trang học, để tay không phải học lại.
  useEffect(() => {
    const typing = () => ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName);
    function onDown(e) {
      if (e.code !== "Space" || typing() || ended) return;
      e.preventDefault();
      if (e.repeat) return;
      if (session.speaking) return session.skipAudio();
      if (session.startTalking({ hold: true })) spaceHeld.current = true;
    }
    function onUp(e) {
      if (e.code !== "Space" || !spaceHeld.current) return;
      spaceHeld.current = false;
      session.stopTalking();
    }
    addEventListener("keydown", onDown);
    addEventListener("keyup", onUp);
    return () => {
      removeEventListener("keydown", onDown);
      removeEventListener("keyup", onUp);
    };
  }, [session, ended]);

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
  const noiDuoc = ended?.outcome === "TAUGHT";

  return (
    <motion.section
      {...blurIn}
      className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-xl"
      aria-label="Phiên nối hai trang"
    >
      <header className="flex items-start gap-3 border-b border-neutral-200 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="m-0 text-[11px] tracking-wide text-neutral-400 uppercase">Nối hai trang</p>
          <p className="m-0 mt-0.5 text-[14px] leading-snug font-semibold tracking-tight">
            {a.label} <span className="font-normal text-neutral-400">—</span> {b.label}
          </p>
          <p className="m-0 mt-0.5 text-[11px] text-neutral-400">
            {deckTag(a.deck)} tr. {a.page} · {deckTag(b.deck)} tr. {b.page}
          </p>
        </div>
        {status && (
          <div className="shrink-0 pt-0.5">
            <LiveDot mode={status[0]} label={status[1]} />
          </div>
        )}
        <button
          onClick={onClose}
          className="-mr-1 h-7 shrink-0 rounded-md px-2 text-[12px] text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          aria-label="Đóng phiên nối"
        >
          Đóng
        </button>
      </header>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {turns.map((turn, i) =>
          turn.role === "student" ? (
            <StudentTurn key={i} turn={turn} />
          ) : (
            <AgentTurn key={i} turn={turn} live={i === lastAgent && session.speaking && !turn.filler} />
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
          </motion.div>
        )}
        {ended && (
          <motion.div {...blurIn} className="rounded-2xl border border-neutral-200 p-4">
            <p className="m-0 text-[15px] font-semibold tracking-tight">
              {noiDuoc ? "Học trò đã thấy chỗ nối" : "Học trò chưa thấy hai trang nối ở đâu"}
            </p>
            <p className="m-0 mt-0.5 text-[13px] text-neutral-500">
              {noiDuoc
                ? "Mối nối vừa hiện trên bản đồ, kèm đúng câu bạn nói."
                : "Thử nói xem một điều ở trang này kéo theo hay giải thích điều gì ở trang kia."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {noiDuoc ? (
                <Button variant="primary" onClick={onClose}>
                  Xong
                </Button>
              ) : (
                <>
                  <Button variant="primary" onClick={open}>
                    Thử nối lại
                  </Button>
                  <Button onClick={onClose}>Để sau</Button>
                </>
              )}
            </div>
          </motion.div>
        )}
        <div ref={bottom} />
      </div>

      {connected && !ended && <Composer session={session} />}
      <audio ref={session.playerRef} onEnded={session.onAudioEnded} onError={session.onAudioEnded} />
    </motion.section>
  );
}
