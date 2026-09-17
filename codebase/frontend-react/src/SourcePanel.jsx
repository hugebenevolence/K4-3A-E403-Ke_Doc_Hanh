// Khung phải: slide đang học.
//
// Hai chế độ, tuỳ đang ở đâu trong vòng Feynman:
// - Chưa giảng: kéo khung (hoặc bấm vào một ô) để chọn phần muốn giảng.
// - Đang giảng: vùng đã chọn bị che lại; bấm "Xem" trong hội thoại hoặc bấm vào
//   vùng che thì mở ra đúng chỗ — đó là bước quay lại nguồn.

import { AnimatePresence, motion, useAnimate } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { deckPdf } from "./api";
import { blurIn, EASE } from "./motion";
import SlideView from "./SlideView";
import { Badge, Button, Separator } from "./ui";

const ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 2];
const COACHED_KEY = "giang-lai-coached";

function wasCoached() {
  try {
    return localStorage.getItem(COACHED_KEY) === "1";
  } catch {
    return false;
  }
}

export default function SourcePanel({
  deck,
  outline,
  page,
  pages,
  setPage,
  zoomIndex,
  setZoomIndex,
  blocks,
  selectable,
  selectedIds,
  coveredIds,
  revealedIds,
  setRevealedIds,
  focusedSpan,
  focusKey,
  sourcePage,
  onSelect,
  onAbandon,
  onPages,
}) {
  const [scope, animate] = useAnimate();
  const source = useMemo(() => deckPdf(deck.slug), [deck.slug]);
  const title = outline.find((row) => row.page === page)?.title || `Slide ${page}`;
  const inSession = !selectable;
  const allRevealed = coveredIds.size > 0 && [...coveredIds].every((id) => revealedIds.has(id));
  function toggleReveal(id) {
    setRevealedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const [emptyHint, setEmptyHint] = useState(false);
  const hintTimer = useRef(null);
  function showEmptyHint() {
    setEmptyHint(true);
    clearTimeout(hintTimer.current);
    hintTimer.current = setTimeout(() => setEmptyHint(false), 2400);
  }
  useEffect(() => () => clearTimeout(hintTimer.current), []);

  // Lời nhắc "kéo để chọn" chỉ hiện tới lần chọn đầu tiên trên máy này: người
  // đã chọn được một lần thì không cần được nhắc nữa.
  const [coached, setCoached] = useState(wasCoached);
  function select(ids) {
    if (ids.length && !coached) {
      setCoached(true);
      try {
        localStorage.setItem(COACHED_KEY, "1");
      } catch {
        // Không lưu được thì lần sau nhắc lại, không sao.
      }
    }
    onSelect(ids);
  }

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

  const hint = emptyHint
    ? "Vùng này không có nội dung để chọn"
    : selectable && !coached && selectedIds.size === 0
      ? "Kéo trên slide để chọn phần muốn giảng"
      : null;

  return (
    <section className="flex min-h-0 min-w-0 flex-col bg-neutral-50">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-neutral-200 bg-white px-4">
        <h2 className="m-0 min-w-0 truncate text-[13px] font-medium text-neutral-900">{title}</h2>
        {inSession && page === sourcePage && <Badge>Đang giảng</Badge>}

        <div className="ml-auto flex shrink-0 items-center gap-1">
          {inSession && page !== sourcePage && (
            <Button variant="quiet" size="sm" onClick={() => setPage(sourcePage)}>
              Về trang đang giảng
            </Button>
          )}
          <Button
            size="sm"
            variant="quiet"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            aria-label="Trang trước"
            title="Trang trước (←)"
          >
            ←
          </Button>
          <span className="min-w-14 text-center text-[12px] tabular-nums text-neutral-500">
            {page} / {pages || "–"}
          </span>
          <Button
            size="sm"
            variant="quiet"
            onClick={() => setPage((p) => Math.min(pages || 1, p + 1))}
            disabled={page >= pages}
            aria-label="Trang sau"
            title="Trang sau (→)"
          >
            →
          </Button>
          <Separator />
          <Button
            size="sm"
            variant="quiet"
            onClick={() => setZoomIndex((z) => Math.max(0, z - 1))}
            disabled={zoomIndex === 0}
            aria-label="Thu nhỏ"
          >
            −
          </Button>
          <span className="w-10 text-center text-[12px] tabular-nums text-neutral-500">
            {Math.round(ZOOM_STEPS[zoomIndex] * 100)}%
          </span>
          <Button
            size="sm"
            variant="quiet"
            onClick={() => setZoomIndex((z) => Math.min(ZOOM_STEPS.length - 1, z + 1))}
            disabled={zoomIndex === ZOOM_STEPS.length - 1}
            aria-label="Phóng to"
          >
            +
          </Button>
        </div>
      </header>

      {/* Công cụ chỉ có nghĩa khi đang giảng: xem phần bị che, hoặc bỏ phiên để
          chọn chỗ khác. */}
      <AnimatePresence initial={false}>
        {inSession && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="shrink-0 overflow-hidden border-b border-neutral-200 bg-white"
          >
            <div className="flex items-center gap-1.5 px-4 py-2">
              <Button
                size="sm"
                pressed={allRevealed}
                onClick={() => setRevealedIds(allRevealed ? new Set() : new Set(coveredIds))}
              >
                {allRevealed ? "Che lại tất cả" : "Xem tất cả"}
              </Button>
              <Button size="sm" variant="quiet" className="ml-auto" onClick={onAbandon}>
                Chọn phần khác
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative min-h-0 flex-1 overflow-auto p-6">
        <div ref={scope}>
          <SlideView
            source={source}
            page={page}
            zoom={ZOOM_STEPS[zoomIndex]}
            blocks={blocks}
            selectable={selectable}
            selectedIds={selectedIds}
            coveredIds={coveredIds}
            revealedIds={revealedIds}
            focusedSpan={focusedSpan}
            focusKey={focusKey}
            onSelect={select}
            onEmptyDrag={showEmptyHint}
            onToggleReveal={toggleReveal}
            onPages={onPages}
          />
        </div>

        {/* Lời nhắc nổi trên slide thay vì một câu dài trên thanh công cụ: nằm
            đúng chỗ cần làm, và biến mất khi đã làm được. */}
        <AnimatePresence>
          {hint && (
            <motion.div
              key={hint}
              {...blurIn}
              transition={{ duration: 0.25, ease: EASE }}
              className="pointer-events-none sticky bottom-2 z-10 mt-4 flex justify-center"
            >
              <span className="rounded-full bg-neutral-900 px-3.5 py-2 text-[13px] font-medium text-white shadow-[0_8px_24px_rgb(0_0_0/0.2)]">
                {hint}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
