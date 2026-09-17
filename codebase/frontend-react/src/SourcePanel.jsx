// Khung phải: tài liệu nguồn — ở đây là slide, về sau thêm lời giảng viên.
//
// Vai trò giống khung "artifact" của ảnh tham chiếu: hội thoại ở giữa nói, còn
// thứ đang được bàn tới mở ra ở đây. Bấm "Mở" trong hội thoại là khung này
// nhảy đúng trang và khoanh đúng vùng.

import { useAnimate } from "motion/react";
import { useEffect } from "react";
import SlideView from "./SlideView";
import { API } from "./useSession";
import { EASE } from "./motion";
import { Badge, Button, Separator } from "./ui";

const ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 2];

export default function SourcePanel({
  lesson,
  outline,
  page,
  pages,
  setPage,
  zoomIndex,
  setZoomIndex,
  spotlight,
  setSpotlight,
  focusedSpan,
  focusKey,
  teachingPages,
  sourcePage,
  onPages,
}) {
  const [scope, animate] = useAnimate();
  const title = outline.find((row) => row.page === page)?.title;

  // Đổi trang thì nội dung nhoè rồi rõ lại, thay vì giật sang trang mới —
  // nhưng KHÔNG gỡ SlideView ra lắp lại, vì như thế là tải lại cả file PDF.
  useEffect(() => {
    if (!scope.current) return;
    animate(
      scope.current,
      { opacity: [0.4, 1], filter: ["blur(6px)", "blur(0px)"], y: [4, 0] },
      { duration: 0.4, ease: EASE },
    );
  }, [page, animate, scope]);

  return (
    <section className={`flex min-h-0 min-w-0 flex-col bg-neutral-50/40 ${spotlight ? "spotlight" : ""}`}>
      <div className="flex h-12 shrink-0 items-end gap-1 border-b border-neutral-200 bg-neutral-50/70 px-3">
        {/* Một tab duy nhất — đủ để nói "đây là tài liệu đang mở", không giả
            vờ có nhiều tài liệu khi chưa có. */}
        <div className="-mb-px flex h-9 items-center gap-2 rounded-t-lg border border-b-0 border-neutral-200 bg-white px-3 text-[13px] font-medium text-neutral-900">
          Slide {page}
          <span className="text-neutral-300">/</span>
          <span className="font-normal text-neutral-400">{pages || "–"}</span>
        </div>
        <Button variant="quiet" size="sm" className="mb-1.5 ml-auto" onClick={() => setPage(sourcePage)}>
          Về trang đang dạy
        </Button>
      </div>

      <div className="shrink-0 px-6 pt-5 pb-3">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="m-0 min-w-0 truncate text-[18px] font-semibold tracking-tight text-neutral-900">
            {title || `Slide ${page}`}
          </h2>
          {teachingPages.has(page) && <Badge>Đang dạy</Badge>}
        </div>
        <p className="m-0 mt-0.5 text-[12px] text-neutral-500">
          AI &amp; LLM Foundation · Day 1 · trang {page}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Button size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
            Trước
          </Button>
          <Button size="sm" onClick={() => setPage((p) => Math.min(pages || 1, p + 1))} disabled={page >= pages}>
            Sau
          </Button>
          <Separator />
          <Button size="sm" variant="quiet" onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}>
            −
          </Button>
          <span className="w-10 text-center text-[12px] tabular-nums text-neutral-500">
            {Math.round(ZOOM_STEPS[zoomIndex] * 100)}%
          </span>
          <Button
            size="sm"
            variant="quiet"
            onClick={() => setZoomIndex((z) => Math.min(ZOOM_STEPS.length - 1, z + 1))}
          >
            +
          </Button>
          <Separator />
          <Button size="sm" pressed={spotlight} onClick={() => setSpotlight((s) => !s)}>
            Vùng đang dạy
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-6 pb-6">
        <div ref={scope}>
          {lesson.has_slides ? (
            <SlideView
              url={`${API}/slides.pdf`}
              spans={lesson.spans}
              page={page}
              zoom={ZOOM_STEPS[zoomIndex]}
              focusedSpan={focusedSpan}
              focusKey={focusKey}
              onPages={onPages}
            />
          ) : (
            <p className="text-[13px] text-neutral-400">Chưa cấu hình slide (SLIDES_PDF trong .env)</p>
          )}
        </div>
      </div>
    </section>
  );
}
