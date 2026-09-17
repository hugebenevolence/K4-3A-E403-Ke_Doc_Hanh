// TẠM ẨN — không màn hình nào import file này lúc này.
//
// Dạy-lại-CODE chạy được rồi (backend còn nguyên: prompts/grader_code/,
// fixtures/demo_code_lesson.json), nhưng đường NÓI mới là chỗ sản phẩm đứng
// hay ngã, nên dồn sức vào đó trước. Bật lại bằng ENABLE_CODE_MODE=true ở
// backend rồi cắm lại component này vào App.jsx.
//
// Trình soạn code, dùng Monaco (chính editor của VS Code).
//
// Tô sáng đúng khoảng dòng agent đang bàn tới — đây là điểm khác biệt với mọi
// công cụ code AI khác: nó chỉ chỗ đáng nhìn và hỏi, không viết hộ.

import Editor from "@monaco-editor/react";
import { useEffect, useMemo, useRef, useState } from "react";

export default function CodeView({ lesson, focusedSpan, onChange }) {
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const decorations = useRef(null);
  // Monaco mount xong SAU lần render đầu, nên nếu không có cờ này thì effect vẽ
  // chạy một lần lúc chưa có editor, thoát ra, rồi không bao giờ chạy lại —
  // và không vùng code nào được tô sáng.
  const [ready, setReady] = useState(false);

  // Nếu tính lại mỗi lần render thì mảng luôn "mới", effect chạy vô hạn.
  const spans = useMemo(() => lesson.spans.filter((s) => s.lines), [lesson.spans]);

  useEffect(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!ready || !editor || !monaco) return;

    decorations.current = editor.deltaDecorations(
      decorations.current ?? [],
      spans.map(({ span_id, lines: [from, to] }) => {
        const on = span_id === focusedSpan;
        return {
          range: new monaco.Range(from, 1, to, 1),
          options: {
            isWholeLine: true,
            className: on ? "code-span focused" : "code-span",
            // Vệt lề trái: thấy được vùng đang bàn cả khi đã cuộn ra xa.
            linesDecorationsClassName: on ? "code-gutter focused" : "code-gutter",
          },
        };
      }),
    );

    const target = spans.find((s) => s.span_id === focusedSpan);
    if (target) editor.revealLineInCenter(target.lines[0]);
  }, [focusedSpan, spans, ready]);

  return (
    <div className="min-h-80 flex-1 overflow-hidden rounded-xl border border-neutral-200 bg-white">
      <Editor
        defaultLanguage={lesson.language}
        defaultValue={lesson.code}
        onChange={onChange}
        onMount={(editor, monaco) => {
          editorRef.current = editor;
          monacoRef.current = monaco;
          setReady(true);
        }}
        options={{
          // Học viên ĐƯỢC sửa code: giải thích rồi thử đổi là một phần của học.
          readOnly: false,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 13,
          renderLineHighlight: "none",
          padding: { top: 12, bottom: 12 },
        }}
      />
    </div>
  );
}
