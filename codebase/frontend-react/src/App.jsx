import { useCallback, useEffect, useMemo, useState } from "react";
import CodeView from "./CodeView";
import SlideView from "./SlideView";
import TeachPanel from "./TeachPanel";
import { Button, Eyebrow, LiveDot, Separator } from "./ui";
import { API, useSession } from "./useSession";
import "./styles.css";

const ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 2];

export default function App() {
  const [lesson, setLesson] = useState(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [zoomIndex, setZoomIndex] = useState(1);
  const [focusedSpan, setFocusedSpan] = useState(null);
  const [spotlight, setSpotlight] = useState(false);
  const [code, setCode] = useState("");

  const session = useSession();
  const isCode = lesson?.kind === "code";

  useEffect(() => {
    fetch(`${API}/lesson`)
      .then((r) => r.json())
      .then((data) => {
        setLesson(data);
        setCode(data.code ?? "");
        const first = data.spans.find((s) => s.page)?.page;
        if (first) setPage(first);
      })
      .catch(() => setLesson({ concept: "(không kết nối được backend)", spans: [] }));
  }, []);

  const spanById = useMemo(
    () => new Map((lesson?.spans ?? []).map((s) => [s.span_id, s])),
    [lesson],
  );
  const sourcePage = useMemo(
    () => lesson?.spans.find((s) => s.page)?.page ?? 1,
    [lesson],
  );

  const jump = useCallback((span) => {
    if (span.page) setPage(span.page);
    setFocusedSpan(span.span_id);
  }, []);

  // Phím tắt. Bỏ qua khi con trỏ đang ở ô nhập chữ — lúc đó bàn phím thuộc về
  // người đang gõ, không phải về ứng dụng.
  useEffect(() => {
    function onKey(e) {
      const typing = ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName);
      if (typing || e.repeat || e.ctrlKey || e.metaKey) return;

      if (e.code === "Space") {
        e.preventDefault();
        if (session.speaking) return session.skipAudio();
        if (session.recording) session.send({ type: "explanation_done", code });
        return;
      }
      if (isCode) return; // bài code không có trang để lật
      if (e.code === "ArrowLeft") setPage((p) => Math.max(1, p - 1));
      if (e.code === "ArrowRight") setPage((p) => Math.min(pages || 1, p + 1));
      if (e.code === "KeyG") setPage(sourcePage);
      if (e.code === "KeyF") setSpotlight((s) => !s);
    }
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [session, isCode, pages, sourcePage, code]);

  if (!lesson) {
    return <p className="p-6 text-[13px] text-neutral-400">Đang tải…</p>;
  }

  const [mode, label] = session.speaking
    ? ["speaking", "Học trò AI đang nói"]
    : session.recording
      ? ["listening", "Đang nghe — Space khi bạn nói xong"]
      : session.activity
        ? ["working", session.activity]
        : session.myTurn
          ? ["idle", "Tới lượt bạn"]
          : session.connected
            ? ["working", "Học trò AI đang nghĩ"]
            : ["idle", "Chưa kết nối"];

  return (
    <div
      className={`flex h-screen flex-col bg-neutral-50 text-neutral-900 antialiased ${
        spotlight ? "spotlight" : ""
      }`}
    >
      <header className="flex shrink-0 items-center gap-6 border-b border-neutral-200 bg-white px-5 py-3">
        <div>
          <Eyebrow>AI &amp; LLM Foundation</Eyebrow>
          <h1 className="m-0 text-[19px] font-semibold tracking-tight">
            {lesson.concept}
          </h1>
        </div>
        <LiveDot mode={mode} label={label} />
      </header>

      <div
        className={`grid min-h-0 flex-1 ${
          isCode ? "grid-cols-[minmax(0,1fr)_400px]" : "grid-cols-[172px_minmax(0,1fr)_400px]"
        }`}
      >
        {!isCode && (
          <aside className="overflow-y-auto border-r border-neutral-200 bg-white p-4">
            <div className="mb-2">
              <Eyebrow>Slide</Eyebrow>
            </div>
            <ol className="m-0 list-none p-0 text-[13px]">
              {Array.from({ length: pages }, (_, i) => {
                const n = i + 1;
                const taught = lesson.spans.some((s) => s.page === n);
                return (
                  <li
                    key={n}
                    onClick={() => setPage(n)}
                    className={`cursor-pointer rounded-lg px-2.5 py-1.5 ${
                      n === page
                        ? "bg-neutral-900 text-white"
                        : "text-neutral-600 hover:bg-neutral-100"
                    }`}
                  >
                    Slide {n}
                    {taught && (
                      <span
                        className={n === page ? "text-neutral-300" : "text-neutral-400"}
                      >
                        {" "}
                        · đang dạy
                      </span>
                    )}
                  </li>
                );
              })}
            </ol>
          </aside>
        )}

        <main className="flex min-w-0 flex-col gap-3 p-4">
          <div className="flex shrink-0 items-center gap-2 overflow-x-auto rounded-xl border border-neutral-200 bg-white px-2 py-1.5">
            {isCode ? (
              <span className="text-[13px] text-neutral-600">
                Giải thích đoạn code này cho học trò AI
              </span>
            ) : (
              <>
                <Button onClick={() => setPage((p) => Math.max(1, p - 1))}>Trước</Button>
                <span className="whitespace-nowrap text-[13px] text-neutral-600">
                  Slide <b>{page}</b> / {pages || "–"}
                </span>
                <Button onClick={() => setPage((p) => Math.min(pages || 1, p + 1))}>
                  Sau
                </Button>
                <Separator />
                <Button onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}>
                  Thu nhỏ
                </Button>
                <span className="whitespace-nowrap text-[13px] text-neutral-600">
                  {Math.round(ZOOM_STEPS[zoomIndex] * 100)}%
                </span>
                <Button
                  onClick={() =>
                    setZoomIndex((z) => Math.min(ZOOM_STEPS.length - 1, z + 1))
                  }
                >
                  Phóng to
                </Button>
                <Separator />
                <Button pressed={spotlight} onClick={() => setSpotlight((s) => !s)}>
                  Vùng đang dạy
                </Button>
                <Button variant="quiet" className="ml-auto" onClick={() => setPage(sourcePage)}>
                  Về trang đang dạy
                </Button>
              </>
            )}
          </div>

          {isCode ? (
            <CodeView lesson={lesson} focusedSpan={focusedSpan} onChange={setCode} />
          ) : lesson.has_slides ? (
            <SlideView
              url={`${API}/slides.pdf`}
              spans={lesson.spans}
              page={page}
              zoom={ZOOM_STEPS[zoomIndex]}
              focusedSpan={focusedSpan}
              onPages={setPages}
            />
          ) : (
            <p className="text-[13px] text-neutral-400">
              Chưa cấu hình slide (SLIDES_PDF trong .env)
            </p>
          )}
        </main>

        <TeachPanel
          session={{ ...session, code: isCode ? code : undefined }}
          spanById={spanById}
          onJump={jump}
        />
      </div>

      <audio
        ref={session.playerRef}
        onEnded={session.onAudioEnded}
        onError={session.onAudioEnded}
      />
    </div>
  );
}
