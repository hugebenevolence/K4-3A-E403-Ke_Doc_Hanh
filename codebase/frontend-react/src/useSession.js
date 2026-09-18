// Toàn bộ vòng đời một phiên dạy-lại: WebSocket, mic, phát tiếng, trạng thái.
//
// Gom vào một hook vì mấy thứ này ràng buộc nhau chặt. Ví dụ luật mic: chỉ thu
// khi backend cho phép, audio agent đã phát xong, VÀ học viên đang nhấn để nói
// — tách rời ra nhiều chỗ thì sớm muộn mic sẽ thu lúc agent đang nói.

import { useCallback, useEffect, useRef, useState } from "react";
import { AUTH_EXPIRED, socketUrl } from "./api";
import { createVad, feedVad, levelOf, resetVad } from "./vad";

/** Server đóng WebSocket bằng mã này khi token hết hạn. */
const CLOSE_UNAUTHORIZED = 4401;
const SAMPLE_RATE = 16000;

/** Mã học viên riêng của trình duyệt này — dùng khi server không bật đăng
 *  nhập; bật rồi thì server lấy tên thành viên làm mã.
 *
 *  Không có nó thì server dùng chung một hồ sơ "demo" cho MỌI người, và agent
 *  nói với người lần đầu vào rằng "buổi trước bạn có nhắc chỗ này" — một sản
 *  phẩm dạy về hallucination lại tự bịa ra trí nhớ. */
export function studentId() {
  try {
    let id = localStorage.getItem("giang-lai-student");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("giang-lai-student", id);
    }
    return id;
  } catch {
    return "khach";
  }
}

/** Dự phòng khi server chưa kịp gửi ngưỡng của state hiện tại. */
const DEFAULT_SILENCE_MS = 2000;

/** Bước nào của graph là việc của vai nào — để hội thoại hiện ra được "ai vừa
 *  làm gì", thay vì một hộp đen im lặng vài giây. */
export const AGENT_OF_STEP = {
  open: "Học trò AI",
  grade: "Người đối chiếu",
  ask_followup: "Học trò AI",
  close_taught: "Học trò AI",
  close_review: "Học trò AI",
};

export function useSession(deck) {
  const [turnState, setTurnState] = useState(null);
  const [micOpen, setMicOpen] = useState(false);
  const [turns, setTurns] = useState([]);
  const [partial, setPartial] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [level, setLevel] = useState(0);
  const [ended, setEnded] = useState(null);
  const [error, setError] = useState("");
  const [micDenied, setMicDenied] = useState(false);
  const [started, setStarted] = useState(false);
  const [micReady, setMicReady] = useState(false);
  // Nhấn để nói, không tự bật mic: 9–16h là giờ dùng cao điểm, tức đang ngồi
  // trong lớp. Mic tự thu là thu luôn giọng giảng viên và bạn bên cạnh.
  const [talking, setTalking] = useState(false);
  // Chế độ im lặng: không đụng tới mic, chỉ gõ chữ.
  const [silent, setSilent] = useState(false);
  // Agent đang làm gì cho lượt hiện tại — để hiện "Đang đối chiếu… 3s" rồi
  // chốt thành "Đã nghĩ trong 4s", như dòng "Worked for 9s" của ảnh tham chiếu.
  const [thinking, setThinking] = useState(null);

  const ws = useRef(null);
  const audioCtx = useRef(null);
  const micStream = useRef(null);
  const queue = useRef([]);
  const player = useRef(null);
  const thinkingRef = useRef(null);

  // Worklet và callback của nó sống ngoài vòng render nên không thấy được
  // state của React — mọi thứ chúng đọc phải đi qua ref.
  const recordingRef = useRef(false);
  const holdRef = useRef(false);
  const silenceMsRef = useRef(DEFAULT_SILENCE_MS);
  const vad = useRef(createVad());
  const finishRef = useRef(() => {});

  const beginThinking = useCallback((step, label) => {
    const next = { startedAt: Date.now(), steps: step ? [{ step, label }] : [] };
    thinkingRef.current = next;
    setThinking(next);
  }, []);

  // Hàm có tên để tự gọi lại được: nếu tham chiếu qua biến `playNext` bên
  // ngoài thì đó là đọc một binding đang khởi tạo dở.
  const playNext = useCallback(function next() {
    const el = player.current;
    if (el?.src.startsWith("blob:")) URL.revokeObjectURL(el.src);
    const blob = queue.current.shift();
    if (!blob) return setSpeaking(false);
    setSpeaking(true);
    el.src = URL.createObjectURL(blob);
    // Trình duyệt chặn phát tự động thì bỏ đoạn đó, sang đoạn sau, đừng kẹt.
    el.play().catch(next);
  }, []);

  const send = useCallback(
    (payload) => {
      if (ws.current?.readyState !== WebSocket.OPEN) return;
      ws.current.send(JSON.stringify(payload));
      setMicOpen(false); // khoá ngay, khỏi gửi hai lần trước khi server trả lời
      setTurnState(null);
      setPartial("");
      setTalking(false);
      setError("");
      beginThinking(null);
    },
    [beginThinking],
  );

  // VAD chạy trong callback của worklet, tức ngoài vòng render, nên nó không
  // gọi thẳng `send` được (sẽ dính bản `send` của một lần render cũ).
  useEffect(() => {
    finishRef.current = () => send({ type: "explanation_done" });
  }, [send]);

  const handle = useCallback((msg) => {
    if (msg.type === "state") {
      setTurnState(msg.state);
      setMicOpen(Boolean(msg.mic_open));
      // Ngưỡng im lặng là luật sư phạm, do domain quyết — xem send_state()
      // trong app/main.py. Frontend chỉ thi hành, không tự đặt con số.
      silenceMsRef.current = msg.silence_ms ?? DEFAULT_SILENCE_MS;
    } else if (msg.type === "activity") {
      // Chỉ nuôi `thinking` — nó giữ cả danh sách bước và mốc thời gian, nên
      // một state thứ hai chỉ chép lại nhãn mới nhất là thừa và sớm muộn lệch.
      const cur = thinkingRef.current;
      if (cur && cur.steps.at(-1)?.step !== msg.step) {
        const next = { ...cur, steps: [...cur.steps, { step: msg.step, label: msg.label }] };
        thinkingRef.current = next;
        setThinking(next);
      }
    } else if (msg.type === "partial") {
      setPartial(msg.text);
    } else if (msg.type === "transcript") {
      setPartial("");
      const cur = thinkingRef.current;
      const agentDone = msg.role === "agent" && !msg.filler && cur;
      setTurns((prev) => [
        ...prev,
        agentDone ? { ...msg, worked: { ms: Date.now() - cur.startedAt, steps: cur.steps } } : msg,
      ]);
      if (agentDone) {
        thinkingRef.current = null;
        setThinking(null);
      }
    } else if (msg.type === "error") {
      setError(msg.message);
      thinkingRef.current = null;
      setThinking(null);
    } else if (msg.type === "session_end") {
      setTurnState(null);
      setMicOpen(false);
      setEnded(msg);
      thinkingRef.current = null;
      setThinking(null);
    }
  }, []);

  const openMic = useCallback(async () => {
    if (audioCtx.current) return true;
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
    } catch {
      setMicDenied(true);
      setSilent(true);
      return false;
    }

    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    if (ctx.sampleRate !== SAMPLE_RATE) {
      // Backend khai cứng 16kHz với Speechmatics; lệch tần số là ra chữ vô nghĩa.
      setError(`Trình duyệt không cho 16kHz (đang ${ctx.sampleRate}Hz) — hãy gõ chữ.`);
      stream.getTracks().forEach((t) => t.stop());
      setMicDenied(true);
      setSilent(true);
      return false;
    }

    // PCM thô chứ KHÔNG dùng MediaRecorder: MediaRecorder đóng gói webm/opus và
    // chuỗi chunk ghép lại bị Speechmatics từ chối ("invalid audio").
    await ctx.audioWorklet.addModule("/pcm-worklet.js");
    const node = new AudioWorkletNode(ctx, "pcm-worklet");
    node.port.onmessage = ({ data }) => {
      if (!recordingRef.current) return;
      if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(data.pcm);

      setLevel(levelOf(data.rms));
      const said = feedVad(vad.current, data.rms, performance.now(), silenceMsRef.current);
      // Đang GIỮ phím thì học viên tự quyết lúc nào xong; ngập ngừng giữa
      // chừng không được phép tự chốt hộ họ.
      if (said === "end" && !holdRef.current) finishRef.current();
    };
    ctx.createMediaStreamSource(stream).connect(node);
    audioCtx.current = ctx;
    micStream.current = stream;
    return true;
  }, []);

  const closeMic = useCallback(() => {
    micStream.current?.getTracks().forEach((t) => t.stop());
    audioCtx.current?.close();
    micStream.current = null;
    audioCtx.current = null;
    setMicReady(false);
  }, []);

  /** Mở phiên cho đúng các ô học viên đã chọn trên slide.
   *
   *  `extra` là tham số riêng của từng loại phiên — phiên nối hai trang trên
   *  bản đồ gửi `{ mode: "link", a, b }` và không có bộ slide nào. */
  const start = useCallback((spanIds = [], extra = {}) => {
    setTurns([]);
    setEnded(null);
    setError("");
    setStarted(true);
    beginThinking("open", "Soạn câu mở đầu");

    const query = { student_id: studentId(), deck, ...extra };
    if (spanIds.length) query.spans = spanIds.join(",");
    // URLSearchParams biến `undefined` thành chữ "undefined": server sẽ đi tìm
    // một bộ slide tên như vậy và báo lỗi.
    for (const k of Object.keys(query)) if (query[k] == null) delete query[k];
    const socket = new WebSocket(socketUrl("/ws/session", query));
    socket.binaryType = "blob";
    socket.onmessage = (e) => {
      if (e.data instanceof Blob) {
        queue.current.push(e.data);
        if (!player.current?.src || player.current.paused) playNext();
        return;
      }
      handle(JSON.parse(e.data));
    };
    socket.onclose = (e) => {
      if (e.code === CLOSE_UNAUTHORIZED) dispatchEvent(new Event(AUTH_EXPIRED));
      // "Giảng lại" đóng kết nối cũ và mở ngay kết nối mới: tin đóng của kết
      // nối cũ về sau không được tắt mic của phiên mới.
      if (ws.current !== socket) return;
      setTurnState(null);
      setMicOpen(false);
      setTalking(false);
    };
    ws.current = socket;
  }, [deck, handle, playNext, beginThinking]);

  /** Quay về chọn phần khác để giảng. */
  const reset = useCallback(() => {
    ws.current?.close();
    ws.current = null;
    queue.current.length = 0;
    player.current?.pause();
    thinkingRef.current = null;
    setThinking(null);
    setTurns([]);
    setEnded(null);
    setError("");
    setTurnState(null);
    setMicOpen(false);
    setTalking(false);
    setSpeaking(false);
    setStarted(false);
  }, []);

  const myTurn = micOpen && !speaking;

  // Đang thu hay không là thứ SUY RA được, không phải state riêng. Giữ thành
  // state riêng thì sớm muộn có một nhánh quên cập nhật, và cái quên đó nghĩa
  // là mic thu trong lúc agent đang nói.
  const recording = myTurn && talking && !silent && micReady;

  // Xin quyền mic ngay khi vào phiên — cú bấm "Bắt đầu" là cử chỉ người dùng
  // chắc chắn có. Xin muộn hơn thì hộp thoại của trình duyệt nhảy ra đúng lúc
  // học viên vừa nhấn để nói. Mở mic KHÔNG có nghĩa là thu: chưa nhấn thì
  // không byte nào được gửi đi.
  useEffect(() => {
    if (!started || silent || micReady) return;
    let cancelled = false;
    openMic().then((ok) => {
      if (ok && !cancelled) setMicReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, [started, silent, micReady, openMic]);

  // Giữ bản mới nhất cho callback của worklet, và quên lượt trước — không quên
  // thì khoảng lặng cuối lượt trước bị tính tiếp và lượt mới chốt ngay khi mở.
  useEffect(() => {
    recordingRef.current = recording;
    if (recording) resetVad(vad.current);
  }, [recording]);

  const startTalking = useCallback(
    ({ hold = false } = {}) => {
      if (!myTurn || silent || !micReady) return false;
      holdRef.current = hold;
      setError("");
      setTalking(true);
      return true;
    },
    [myTurn, silent, micReady],
  );

  /** Chạm nhanh vào nút nói thay vì giữ: vẫn đang thu, nhưng thôi coi là giữ —
   *  im lặng đủ lâu thì tự gửi, hoặc bấm "Xong". */
  const releaseHold = useCallback(() => {
    holdRef.current = false;
  }, []);

  const stopTalking = useCallback(() => {
    if (!talking) return;
    holdRef.current = false;
    send({ type: "explanation_done" });
  }, [talking, send]);

  // Trả mic lại ngay khi phiên kết thúc, và khi rời trang. Thiếu chỗ này thì
  // chấm ghi âm của trình duyệt vẫn sáng sau khi đã học xong.
  useEffect(() => {
    if (!ended) return;
    const id = setTimeout(closeMic, 0);
    return () => clearTimeout(id);
  }, [ended, closeMic]);
  useEffect(() => closeMic, [closeMic]);

  return {
    turns,
    partial,
    thinking,
    ended,
    error,
    speaking,
    recording,
    talking,
    level,
    myTurn,
    silent,
    micReady,
    micDenied,
    started,
    connected: Boolean(turnState) || Boolean(ended) || started,
    start,
    reset,
    send,
    startTalking,
    releaseHold,
    stopTalking,
    setSilent,
    playerRef: player,
    onAudioEnded: playNext,
    skipAudio: () => {
      queue.current.length = 0;
      player.current?.pause();
      playNext();
    },
  };
}
