// Toàn bộ vòng đời một phiên dạy-lại: WebSocket, mic, phát tiếng, trạng thái.
//
// Gom vào một hook vì mấy thứ này ràng buộc nhau chặt. Ví dụ luật mic: chỉ mở
// khi backend cho phép VÀ audio agent đã phát xong — tách rời ra hai chỗ thì
// sớm muộn mic sẽ bắt lại chính giọng agent qua loa, và STT nghe agent nói rồi
// tưởng là học viên.

import { useCallback, useEffect, useRef, useState } from "react";
import { createVad, feedVad, levelOf, resetVad } from "./vad";

export const API = `http://${location.hostname}:8000`;
const SAMPLE_RATE = 16000;

/** Dự phòng khi server chưa kịp gửi ngưỡng của state hiện tại. */
const DEFAULT_SILENCE_MS = 2000;

export function useSession() {
  const [turnState, setTurnState] = useState(null);
  const [micOpen, setMicOpen] = useState(false);
  const [turns, setTurns] = useState([]);
  const [partial, setPartial] = useState("");
  const [activity, setActivity] = useState(null);
  const [started, setStarted] = useState(false);
  const [micReady, setMicReady] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [level, setLevel] = useState(0);
  const [ended, setEnded] = useState(null);
  const [error, setError] = useState("");
  const [micDenied, setMicDenied] = useState(false);
  // Chế độ im lặng: 9–16h là giờ cao điểm dùng VLearn, tức đang ngồi trong lớp
  // — không ai nói to vào máy được. Không có đường này thì sản phẩm chỉ dùng
  // được ở nhà, mà ở nhà thì ít người học hơn hẳn.
  const [silent, setSilent] = useState(false);

  const ws = useRef(null);
  const audioCtx = useRef(null);
  const micStream = useRef(null);
  const queue = useRef([]);
  const player = useRef(null);

  // Worklet và callback của nó sống ngoài vòng render nên không thấy được
  // state của React — mọi thứ chúng đọc phải đi qua ref.
  const recordingRef = useRef(false);
  const silenceMsRef = useRef(DEFAULT_SILENCE_MS);
  const vad = useRef(createVad());
  const finishRef = useRef(() => {});

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

  const send = useCallback((payload) => {
    if (ws.current?.readyState !== WebSocket.OPEN) return;
    ws.current.send(JSON.stringify(payload));
    setMicOpen(false); // khoá ngay, khỏi gửi hai lần trước khi server trả lời
    setTurnState(null);
    setPartial("");
  }, []);

  // VAD chạy trong callback của worklet, tức ngoài vòng render, nên nó không
  // gọi thẳng `send` được (sẽ dính bản `send` của lần render nào đó). Cho nó
  // gọi qua ref, ref luôn trỏ tới bản mới nhất.
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
      setActivity(null);
    } else if (msg.type === "activity") {
      setActivity(msg.label);
    } else if (msg.type === "partial") {
      setPartial(msg.text);
    } else if (msg.type === "transcript") {
      setPartial("");
      setTurns((prev) => [...prev, msg]);
    } else if (msg.type === "error") {
      setError(msg.message);
    } else if (msg.type === "session_end") {
      setTurnState(null);
      setMicOpen(false);
      setEnded(msg);
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
      if (feedVad(vad.current, data.rms, performance.now(), silenceMsRef.current) === "end") {
        finishRef.current();
      }
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

  const start = useCallback(() => {
    setTurns([]);
    setEnded(null);
    setError("");
    setStarted(true);

    const socket = new WebSocket(`${API.replace("http", "ws")}/ws/session`);
    socket.binaryType = "blob";
    socket.onmessage = (e) => {
      if (e.data instanceof Blob) {
        queue.current.push(e.data);
        if (!player.current?.src || player.current.paused) playNext();
        return;
      }
      handle(JSON.parse(e.data));
    };
    socket.onclose = () => {
      setTurnState(null);
      setMicOpen(false);
    };
    ws.current = socket;
  }, [handle, playNext]);

  const myTurn = micOpen && !speaking;

  // Đang thu hay không là thứ SUY RA được, không phải state riêng: nó đúng bằng
  // "tới lượt mình, không ở chế độ im lặng, và mic đã sẵn sàng". Giữ thành
  // state riêng thì sớm muộn sẽ có một nhánh quên cập nhật, và cái quên đó
  // nghĩa là mic thu trong lúc agent đang nói.
  const recording = myTurn && !silent && micReady;

  // Mở mic ngay khi vào phiên, rồi thôi — thay vì bắt bấm "Bật micro" mỗi lượt.
  // Chạy cả khi học viên đang ở chế độ im lặng rồi giữa chừng mới tắt nó đi
  // (ra khỏi lớp, về chỗ ngồi riêng); lúc đó mic còn chưa hề được mở.
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

  // Giữ bản mới nhất cho callback của worklet đọc, và quên những gì nghe được
  // ở lượt trước — không quên thì khoảng lặng cuối lượt trước bị tính tiếp vào
  // lượt này và lượt mới chốt ngay khi vừa mở.
  useEffect(() => {
    recordingRef.current = recording;
    if (recording) resetVad(vad.current);
  }, [recording]);

  // Trả mic lại ngay khi phiên kết thúc, và khi rời trang. Thiếu chỗ này thì
  // chấm ghi âm của trình duyệt vẫn sáng sau khi đã học xong — học viên có lý
  // do để nghĩ là bị nghe lén, và họ đúng khi nghĩ vậy.
  useEffect(() => {
    if (!ended) return;
    const id = setTimeout(closeMic, 0);
    return () => clearTimeout(id);
  }, [ended, closeMic]);
  useEffect(() => closeMic, [closeMic]);

  return {
    turns,
    partial,
    activity,
    ended,
    error,
    speaking,
    recording,
    level,
    myTurn,
    silent,
    micDenied,
    connected: Boolean(turnState) || Boolean(ended),
    start,
    send,
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
