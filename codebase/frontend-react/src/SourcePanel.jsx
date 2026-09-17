// Khung phải: tài liệu nguồn — ở đây là slide, về sau thêm lời giảng viên.
//
// Hai chế độ, tuỳ đang ở đâu trong vòng Feynman:
// - Chưa giảng: kéo khung (hoặc bấm vào một ô) để chọn phần muốn giảng.
// - Đang giảng: vùng đã chọn bị gập lại; bấm "Mở" trong hội thoại hoặc bấm vào
//   vùng gập thì mở ra đúng chỗ — đó là bước quay lại nguồn.

import { AnimatePresence, motion, useAnimate } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { blurIn, EASE } from "./motion";
import SlideView from "./SlideView";
import { API } from "./useSession";
import { Badge, Button, Separator } from "./ui";

const ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 2];

export default function SourcePanel({
  hasSlides,
  outline,
  page,
  pages,
  setPage,
  zoomIndex,
  setZoomIndex,
  spotlight,
  setSpotlight,
  blocks,
  selectable,
  selectedIds,
  coveredIds,
  revealed,
  setRevealed,
  focusedSpan,
  focusKey,
  teachingPages,
  sourcePage,
  onSelect,
  onAbandon,
  onPages,
}) {
  const [scope, animate] = useAnimate();
  const title = outline.find((row) => row.page === page)?.title;
  const inSession = !selectable;
  const [emptyHint, setEmptyHint] = useState(false);
  const hintTimer = useRef(null);

  function showEmptyHint() {
    setEmptyHint(true);
    clearTimeout(hintTimer.current);
    hintTimer.current = setTimeout(() => setEmptyHint(false), 2800);
  }
  useEffect(() => () => clearTimeout(hintTimer.current), []);

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
        {inSession && page !== sourcePage && (
          <Button variant="quiet" size="sm" className="mb-1.5 ml-auto" onClick={() => setPage(sourcePage)}>
            Về trang đang giảng
          </Button>
        )}
      </div>

      <div className="shrink-0 px-6 pt-5 pb-3">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="m-0 min-w-0 truncate text-[18px] font-semibold tracking-tight text-neutral-900">
            {title || `Slide ${page}`}
          </h2>
          {teachingPages.has(page) && <Badge>{inSession ? "Đang giảng" : "Đã chọn"}</Badge>}
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
          {inSession ? (
            <>
              <Button size="sm" pressed={revealed} onClick={() => setRevealed((r) => !r)}>
                {revealed ? "Gập vùng đang giảng" : "Xem lại vùng đang giảng"}
              </Button>
              <Button size="sm" pressed={spotlight} onClick={() => setSpotlight((s) => !s)}>
                Làm mờ phần khác
              </Button>
              {/* Chọn nhầm chỗ, hoặc muốn đổi sang trang khác giảng: bỏ vùng che
                  và quay về chế độ chọn, không phải đợi hết phiên. */}
              <Button size="sm" variant="quiet" onClick={onAbandon}>
                Bỏ che, chọn vùng khác
              </Button>
            </>
          ) : selectedIds.size ? (
            <>
              <Badge tone="strong">{selectedIds.size} ô đã chọn</Badge>
              <Button size="sm" variant="quiet" onClick={() => onSelect([])}>
                Bỏ chọn
              </Button>
            </>
          ) : (
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={emptyHint ? "empty" : "hint"}
                {...blurIn}
                // Lời nhắc phải hiện ngay khi thả chuột, không đợi hiệu ứng dài.
                transition={{ duration: 0.18, ease: EASE }}
                // Một dòng, cắt bớt nếu hẹp: lời nhắc mà xuống dòng thì đẩy slide
                // trôi xuống ngay lúc học viên đang kéo khung trên nó.
                className={`min-w-0 flex-1 truncate text-[12px] ${emptyHint ? "font-medium text-neutral-900" : "text-neutral-500"}`}
              >
                {emptyHint
                  ? "Vùng vừa kéo không có chữ — chữ nằm trong hình thì không chọn được"
                  : "Kéo khung, hoặc bấm vào một ô viền đứt, để chọn phần muốn giảng"}
              </motion.span>
            </AnimatePresence>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-6 pb-6">
        <div ref={scope}>
          {hasSlides ? (
            <SlideView
              url={`${API}/slides.pdf`}
              page={page}
              zoom={ZOOM_STEPS[zoomIndex]}
              blocks={blocks}
              selectable={selectable}
              selectedIds={selectedIds}
              coveredIds={coveredIds}
              revealed={revealed}
              focusedSpan={focusedSpan}
              focusKey={focusKey}
              onSelect={onSelect}
              onEmptyDrag={showEmptyHint}
              onReveal={() => setRevealed(true)}
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
