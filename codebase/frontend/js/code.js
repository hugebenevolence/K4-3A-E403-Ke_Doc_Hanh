// Trình soạn code cho chế độ dạy-lại-code.
//
// Dùng Monaco (chính editor của VS Code) thay vì tự viết: tô màu cú pháp, đánh
// số dòng, và quan trọng nhất là API decoration để tô sáng đúng khoảng dòng mà
// agent đang bàn tới.
//
// Cùng giao kèo với slides.js — show(), focusSpan(), sourcePage() — nên app.js
// gọi bên nào cũng như nhau.

const CDN = "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min";

let editor = null;
let monaco = null;
let spans = [];
let decorations = null;

function loadMonaco() {
  return new Promise((resolve, reject) => {
    const loader = document.createElement("script");
    loader.src = `${CDN}/vs/loader.min.js`;
    loader.onerror = () => reject(new Error("không tải được Monaco"));
    loader.onload = () => {
      window.require.config({ paths: { vs: `${CDN}/vs` } });
      window.require(["vs/editor/editor.main"], () => resolve(window.monaco));
    };
    document.head.append(loader);
  });
}

export async function loadCode(lesson, host) {
  spans = lesson.spans.filter((s) => s.lines);
  monaco = await loadMonaco();

  editor = monaco.editor.create(host, {
    value: lesson.code,
    language: lesson.language,
    // Học viên ĐƯỢC sửa code: giải thích rồi thử đổi là một phần của việc học.
    readOnly: false,
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    fontSize: 13,
    lineNumbers: "on",
    renderLineHighlight: "none",
    padding: { top: 12, bottom: 12 },
  });

  paint();
}

/** Mã học viên đang có trên màn hình — họ sửa thì lần chấm sau phải theo bản mới. */
export const currentCode = () => editor?.getValue() ?? "";

function paint(focused = null) {
  if (!editor) return;
  decorations = editor.deltaDecorations(
    decorations?.length ? decorations : [],
    spans.map(({ span_id, lines: [from, to] }) => ({
      range: new monaco.Range(from, 1, to, 1),
      options: {
        isWholeLine: true,
        className: span_id === focused ? "code-span focused" : "code-span",
        // Vệt ở lề trái: thấy được vùng đang bàn cả khi đã cuộn ra xa.
        linesDecorationsClassName:
          span_id === focused ? "code-gutter focused" : "code-gutter",
      },
    })),
  );
}

/** Tô đậm một vùng và cuộn tới nó — dùng khi agent trích vào đúng chỗ đó. */
export function focusSpan(spanId) {
  const span = spans.find((s) => s.span_id === spanId);
  paint(spanId);
  if (span) editor?.revealLineInCenter(span.lines[0]);
}

// Bài code không có "trang"; giữ cùng giao kèo với slides.js để app.js không
// phải rẽ nhánh theo loại bài.
export const sourcePage = () => null;
export function show() {}
export function step() {}
export function setZoom() {}
