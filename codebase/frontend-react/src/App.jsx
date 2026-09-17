// Khung ứng dụng: thanh bên · hội thoại · tài liệu nguồn — bố cục ba cột theo
// ảnh tham chiếu, nền trắng.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Conversation from "./Conversation";
import Sidebar from "./Sidebar";
import SourcePanel from "./SourcePanel";
import { API, useSession } from "./useSession";
import "./styles.css";

export default function App() {
  const [lesson, setLesson] = useState(null);
  const [outline, setOutline] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [zoomIndex, setZoomIndex] = useState(1);
  const [focus, setFocus] = useState({ id: null, n: 0 });
  const [spotlight, setSpotlight] = useState(false);
  const spaceHeld = useRef(false);

  const session = useSession();

  useEffect(() => {
    fetch(`${API}/lesson`)
      .then((r) => r.json())
      .then((data) => {
        setLesson(data);
        const first = data.spans.find((s) => s.page)?.page;
        if (first) setPage(first);
      })
      .catch(() => setLesson({ concept: "(không kết nối được backend)", spans: [] }));
    // Dàn ý chỉ để làm đẹp thanh bên: hỏng thì vẫn học được, chỉ mất tiêu đề.
    fetch(`${API}/slides/outline`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setOutline)
      .catch(() => {});
  }, []);

  const spanById = useMemo(() => new Map((lesson?.spans ?? []).map((s) => [s.span_id, s])), [lesson]);
  const teachingPages = useMemo(
    () => new Set((lesson?.spans ?? []).map((s) => s.page).filter(Boolean)),
    [lesson],
  );
  const sourcePage = useMemo(() => lesson?.spans.find((s) => s.page)?.page ?? 1, [lesson]);

  const open = useCallback((span) => {
    if (span.page) setPage(span.page);
    // Tăng bộ đếm để khung "đáp xuống" chạy lại cả khi mở lại đúng vùng cũ.
    setFocus((f) => ({ id: span.span_id, n: f.n + 1 }));
  }, []);

  // Phím tắt. Bỏ qua khi con trỏ đang ở ô nhập chữ — lúc đó bàn phím thuộc về
  // người đang gõ, không phải về ứng dụng.
  useEffect(() => {
    const typing = () => ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName);

    function onDown(e) {
      if (typing() || e.ctrlKey || e.metaKey) return;
      if (e.code === "Space") {
        e.preventDefault();
        if (e.repeat) return;
        // Space là nút "giữ để nói". Khi agent đang nói thì nó là nút cắt lời:
        // đã hiểu câu hỏi rồi thì không phải ngồi nghe hết.
        if (session.speaking) return session.skipAudio();
        if (session.startTalking({ hold: true })) spaceHeld.current = true;
        return;
      }
      if (e.repeat) return;
      if (e.code === "ArrowLeft") setPage((p) => Math.max(1, p - 1));
      if (e.code === "ArrowRight") setPage((p) => Math.min(pages || 1, p + 1));
      if (e.code === "KeyG") setPage(sourcePage);
      if (e.code === "KeyF") setSpotlight((s) => !s);
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
  }, [session, pages, sourcePage]);

  if (!lesson) {
    return <p className="p-6 font-sans text-[13px] text-neutral-400">Đang tải…</p>;
  }

  return (
    <div className="grid h-screen grid-cols-[240px_minmax(380px,460px)_minmax(0,1fr)] bg-white font-sans text-neutral-900 antialiased">
      <Sidebar
        outline={outline}
        pages={pages}
        page={page}
        teachingPages={teachingPages}
        onPage={setPage}
      />
      <Conversation session={session} lesson={lesson} spanById={spanById} onOpen={open} />
      <SourcePanel
        lesson={lesson}
        outline={outline}
        page={page}
        pages={pages}
        setPage={setPage}
        zoomIndex={zoomIndex}
        setZoomIndex={setZoomIndex}
        spotlight={spotlight}
        setSpotlight={setSpotlight}
        focusedSpan={focus.id}
        focusKey={focus.n}
        teachingPages={teachingPages}
        sourcePage={sourcePage}
        onPages={setPages}
      />

      <audio ref={session.playerRef} onEnded={session.onAudioEnded} onError={session.onAudioEnded} />
    </div>
  );
}
