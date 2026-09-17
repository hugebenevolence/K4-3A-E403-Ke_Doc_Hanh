// Không gian học của một bộ slide: thanh bên · hội thoại · tài liệu nguồn — bố
// cục ba cột theo ảnh tham chiếu, nền trắng.
//
// Học viên chọn phần nào trên slide thì phiên giảng dựng từ đúng phần đó. Chưa
// chọn gì thì giảng cả trang đang mở.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { api } from "../api";
import Conversation from "../Conversation";
import { markTaught, rememberPage, taughtPages } from "../decks";
import Sidebar from "../Sidebar";
import SourcePanel from "../SourcePanel";
import { useSession } from "../useSession";

const NONE = new Set();
const EMPTY = [];

/** Vùng ít chữ hơn ngần này (đã TRỪ tiêu đề trang) thì không đủ để giảng.
 *
 *  Đo được thật: chọn mỗi tiêu đề slide 12 thì nguồn chấm chỉ còn một dòng, và
 *  câu mở bài quay sang hỏi về một slide khác hẳn. Tiêu đề là tên của phần
 *  giảng, không phải nội dung để giảng — nên mở rộng ra cả trang.
 *
 *  Con số phải khớp `MIN_SOURCE_WORDS` ở backend (app/domain/substance.py), nơi
 *  ghi phép đo dựng ra nó: 58 trang của hai bộ slide, hai trang bìa ra 16 và 18
 *  từ, trang nội dung mỏng nhất kế tiếp ra 29 từ. Lệch nhau thì học viên bấm
 *  được nút rồi mới bị server từ chối. */
const MIN_TEACH_WORDS = 24;

const wordsIn = (text) => text?.match(/[\p{L}\p{N}]+/gu)?.length ?? 0;
/** Gộp khoảng trắng trước khi so — backend so cũng bằng cách này
 *  (`teachable_words`). Chỉ `.trim()` thì tiêu đề bị PDF ngắt làm hai dòng sẽ
 *  không khớp ở client mà vẫn khớp ở server: nút bấm được, server từ chối. */
const sameText = (a, b) => a.replace(/\s+/gu, " ").trim() === b.replace(/\s+/gu, " ").trim();

export default function Learn() {
  const { slug } = useParams();
  const [params, setParams] = useSearchParams();
  const [deck, setDeck] = useState(null);
  const [outline, setOutline] = useState([]);
  const [blocks, setBlocks] = useState([]);
  const [page, setPage] = useState(() => Math.max(1, Number(params.get("page")) || 1));
  const [pages, setPages] = useState(0);
  const [zoomIndex, setZoomIndex] = useState(1);
  const [focus, setFocus] = useState({ id: null, n: 0 });
  // Vùng đang chọn (chưa giảng) và vùng của phiên đang chạy — hai thứ khác
  // nhau: đang giảng dở mà lật sang trang khác xem thì không được mất vùng cũ.
  const [selection, setSelection] = useState({ page: null, ids: [] });
  const [active, setActive] = useState([]);
  const [taught, setTaught] = useState(() => taughtPages(slug));
  // Những ô đang giảng mà học viên đã bấm mở ra xem; còn lại vẫn bị che.
  const [revealedIds, setRevealedIds] = useState(NONE);
  const spaceHeld = useRef(false);

  const session = useSession(slug);
  const inSession = session.started && !session.ended;

  useEffect(() => {
    let cancelled = false;
    const path = `/decks/${encodeURIComponent(slug)}`;
    Promise.all([api("/decks"), api(`${path}/outline`), api(`${path}/blocks`)])
      .then(([decks, rows, spans]) => {
        if (cancelled) return;
        setOutline(rows);
        setBlocks(spans);
        setDeck(decks.find((d) => d.slug === slug) ?? { slug, title: slug, subtitle: "" });
      })
      .catch((err) => !cancelled && setDeck({ error: err.status === 404 ? "missing" : err.message }));
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Trang đang xem nằm trên thanh địa chỉ: gửi link cho bạn cùng nhóm là mở
  // đúng slide, tải lại trang không bị đưa về slide 1.
  useEffect(() => {
    if (params.get("page") !== String(page)) setParams({ page: String(page) }, { replace: true });
    rememberPage(slug, page);
  }, [page, params, setParams, slug]);

  const byId = useMemo(() => new Map(blocks.map((b) => [b.span_id, b])), [blocks]);
  const blocksOnPage = useMemo(() => blocks.filter((b) => b.page === page), [blocks, page]);
  const titleOf = useCallback((p) => outline.find((row) => row.page === p)?.title || `Slide ${p}`, [outline]);

  const selectedHere = useMemo(
    () => (selection.page === page ? selection.ids : EMPTY),
    [selection, page],
  );
  const shownIds = useMemo(() => new Set(inSession ? active : selectedHere), [inSession, active, selectedHere]);
  const sessionPage = byId.get(active[0])?.page ?? page;
  const selectionPage = selection.ids.length ? selection.page : null;
  const teachingPages = useMemo(
    () => new Set([inSession || session.ended ? sessionPage : selectionPage].filter(Boolean)),
    [inSession, session.ended, sessionPage, selectionPage],
  );

  const select = useCallback((ids) => setSelection({ page, ids }), [page]);

  // Bỏ ô trùng tiêu đề trang khi đếm: tiêu đề là TÊN của phần cần giảng, không
  // phải nội dung để giảng. Đếm cả nó thì trang bìa vượt ngưỡng nhờ đúng dòng
  // chữ mà học viên không có gì để nói về nó — đó là phiên hỏng 2e6d52f3.
  const bodyWords = useCallback(
    (ids) => {
      const head = titleOf(page);
      return ids.reduce((n, id) => {
        const text = byId.get(id)?.text ?? "";
        return sameText(text, head) ? n : n + wordsIn(text);
      }, 0);
    },
    [byId, page, titleOf],
  );

  const selectedWords = useMemo(() => bodyWords(selectedHere), [bodyWords, selectedHere]);
  // Cả trang cũng không đủ chữ (trang bìa, trang phân mục): nới ra cũng chẳng
  // còn gì để nới, và server sẽ từ chối thật — nên chặn ngay ở nút bấm.
  const pageTeachable = useMemo(
    () =>
      blocksOnPage.some((b) => b.kind === "figure") ||
      bodyWords(blocksOnPage.map((b) => b.span_id)) >= MIN_TEACH_WORDS,
    [blocksOnPage, bodyWords],
  );
  // Ngưỡng chữ chỉ áp cho ô CHỮ. Một sơ đồ gần như không có chữ trong PDF
  // nhưng lại là nguyên một ý để giảng — đếm chữ thì slide nào cũng bị coi là
  // "quá ngắn" và bị mở ra cả trang.
  const hasFigure = useMemo(
    () => selectedHere.some((id) => byId.get(id)?.kind === "figure"),
    [selectedHere, byId],
  );
  const thin = selectedHere.length > 0 && !hasFigure && selectedWords < MIN_TEACH_WORDS;

  /** Bắt đầu giảng: vùng đã chọn, hoặc cả trang đang mở nếu chưa chọn gì hay
   *  vùng chọn quá mỏng. */
  const teach = useCallback(() => {
    // Chặn ở đây chứ không chỉ ở nút: phím Enter cũng vào đúng hàm này.
    if (!pageTeachable) return;
    const ids = selectedHere.length && !thin ? selectedHere : blocksOnPage.map((b) => b.span_id);
    setActive(ids);
    setSelection({ page, ids });
    setRevealedIds(NONE);
    setFocus((f) => ({ id: null, n: f.n }));
    session.start(ids);
  }, [selectedHere, thin, pageTeachable, blocksOnPage, page, session]);

  /** Kết thúc phiên đang dở (nếu có) và quay về chọn vùng. Giữ nguyên trang
   *  đang xem, để học viên chọn ngay trên trang họ vừa lật tới. */
  const restart = useCallback(() => {
    session.reset();
    setRevealedIds(NONE);
    setSelection({ page: null, ids: [] });
  }, [session]);

  /** Giảng lại đúng phần vừa giảng: che lại và mở phiên mới. */
  const retry = useCallback(() => {
    session.reset();
    setRevealedIds(NONE);
    setFocus((f) => ({ id: null, n: f.n }));
    setPage(sessionPage);
    session.start(active);
  }, [session, active, sessionPage]);

  // Giảng được thì ghi lại, để thanh bên và thư viện hiện tiến độ.
  const outcome = session.ended?.outcome;
  useEffect(() => {
    if (outcome !== "TAUGHT") return;
    markTaught(slug, sessionPage);
    setTaught(taughtPages(slug));
  }, [outcome, slug, sessionPage]);

  const open = useCallback(
    (span) => {
      const where = byId.get(span.span_id) ?? span;
      if (where.page) setPage(where.page);
      // Bấm "Xem" là bước quay lại nguồn của Feynman: mở đúng ô được nhắc tới
      // (hoặc cả vùng, nếu thẻ trỏ ra ngoài vùng đang che).
      setRevealedIds((prev) =>
        active.includes(span.span_id) ? new Set([...prev, span.span_id]) : new Set(active),
      );
      // Tăng bộ đếm để khung "đáp xuống" chạy lại cả khi mở lại đúng vùng cũ.
      setFocus((f) => ({ id: span.span_id, n: f.n + 1 }));
    },
    [byId, active],
  );

  // Phím tắt. Bỏ qua khi con trỏ đang ở ô nhập chữ — lúc đó bàn phím thuộc về
  // người đang gõ, không phải về ứng dụng.
  useEffect(() => {
    const typing = () => ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName);

    function onDown(e) {
      if (typing() || e.ctrlKey || e.metaKey) return;
      if (e.code === "Space" && inSession) {
        e.preventDefault();
        if (e.repeat) return;
        // Space là nút "giữ để nói". Khi agent đang nói thì nó là nút cắt lời:
        // đã hiểu câu hỏi rồi thì không phải ngồi nghe hết.
        if (session.speaking) return session.skipAudio();
        if (session.startTalking({ hold: true })) spaceHeld.current = true;
        return;
      }
      if (e.repeat) return;
      // Enter trên một nút đang được focus đã tự bấm nút đó rồi — bắt đầu phiên
      // thêm lần nữa ở đây là một phím làm hai việc.
      const onButton = document.activeElement?.tagName === "BUTTON";
      if (!inSession && e.code === "Enter" && !onButton && blocks.length) return teach();
      if (!inSession && e.code === "Escape") return setSelection({ page: null, ids: [] });
      if (e.code === "ArrowLeft") setPage((p) => Math.max(1, p - 1));
      if (e.code === "ArrowRight") setPage((p) => Math.min(pages || 1, p + 1));
      if (e.code === "KeyG" && inSession) setPage(sessionPage);
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
  }, [session, inSession, pages, sessionPage, teach, blocks.length]);

  if (deck?.error) {
    return (
      <div className="grid min-h-screen place-items-center bg-white px-4 font-sans">
        <div className="text-center">
          <p className="m-0 text-[15px] font-medium text-neutral-900">
            {deck.error === "missing" ? "Không tìm thấy bài học này" : deck.error}
          </p>
          <Link to="/library" className="mt-3 inline-block text-[13px] text-neutral-500 underline hover:text-neutral-900">
            Về thư viện
          </Link>
        </div>
      </div>
    );
  }
  if (!deck) {
    return <p className="p-6 font-sans text-[13px] text-neutral-400">Đang tải…</p>;
  }

  const target = {
    page,
    title: titleOf(page),
    count: selectedHere.length,
    thin,
    teachable: pageTeachable,
    hasSlides: blocks.length > 0,
  };
  // Giảng xong một trang thì đi tiếp được ngay, không phải tìm lại trong dàn ý.
  const next =
    sessionPage < pages
      ? () => {
          restart();
          setPage(sessionPage + 1);
        }
      : null;

  return (
    <div className="grid h-screen grid-cols-[240px_minmax(380px,460px)_minmax(0,1fr)] bg-white font-sans text-neutral-900 antialiased">
      <Sidebar
        deck={deck}
        outline={outline}
        pages={pages}
        page={page}
        teachingPages={teachingPages}
        taught={taught}
        onPage={setPage}
      />
      <Conversation
        session={session}
        target={target}
        spanById={byId}
        onTeach={teach}
        onClearSelection={() => setSelection({ page: null, ids: [] })}
        onRestart={restart}
        onRetry={retry}
        onNext={next}
        onOpen={open}
      />
      <SourcePanel
        deck={deck}
        outline={outline}
        page={page}
        pages={pages}
        setPage={setPage}
        zoomIndex={zoomIndex}
        setZoomIndex={setZoomIndex}
        blocks={blocksOnPage}
        selectable={!inSession}
        selectedIds={shownIds}
        coveredIds={inSession ? shownIds : NONE}
        revealedIds={revealedIds}
        setRevealedIds={setRevealedIds}
        focusedSpan={focus.id}
        focusKey={focus.n}
        sourcePage={sessionPage}
        onSelect={select}
        onAbandon={restart}
        onPages={setPages}
      />

      <audio ref={session.playerRef} onEnded={session.onAudioEnded} onError={session.onAudioEnded} />
    </div>
  );
}
