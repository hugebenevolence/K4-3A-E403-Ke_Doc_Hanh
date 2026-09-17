// Toàn bộ vòng đời một phiên dạy-lại: WebSocket, mic, phát tiếng, trạng thái.
//
// Gom vào một hook vì mấy thứ này ràng buộc nhau chặt. Ví dụ luật mic: chỉ mở
// khi backend cho phép VÀ audio agent đã phát xong — tách rời ra hai chỗ thì
// sớm muộn mic sẽ bắt lại chính giọng agent qua loa, và STT nghe agent nói rồi
// tưởng là học viên.

import { useCallback, useEffect, useRef, useState } from "react";

export const API = `http://${location.hostname}:8000`;
const MIC_STATES = new Set(["STUDENT_TEACHING", "STUDENT_RESPONDING"]);
const SAMPLE_RATE = 16000;

export function useSession() {
  const [turnState, setTurnState] = useState(null);
  const [turns, setTurns] = useState([]);
  const [partial, setPartial] = useState("");
  const [activity, setActivity] = useState(null);
  const [recording, setRecording] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [ended, setEnded] = useState(null);
  const [error, setError] = useState("");

  const ws = useRef(null);
  const audioCtx = useRef(null);
  const queue = useRef([]);
  const player = useRef(null);
  const recordingRef = useRef(false);

  // Giữ bản mới nhất cho callback của AudioWorklet đọc: worklet sống ngoài
  // vòng render nên nó không thấy được state của React.
  useEffect(() => {
    recordingRef.current = recording;
  }, [recording]);

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

  const handle = useCallback(
    (msg) => {
      if (msg.type === "state") {
        setTurnState(msg.state);
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
        setEnded(msg);
      }
    },
    [],
  );

  const start = useCallback(() => {
    setTurns([]);
    setEnded(null);
    setError("");
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
      setRecording(false);
    };
    ws.current = socket;
  }, [handle, playNext]);

  const openMic = useCallback(async () => {
    if (audioCtx.current) return true;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    if (ctx.sampleRate !== SAMPLE_RATE) {
      // Backend khai cứng 16kHz với Speechmatics; lệch tần số là ra chữ vô nghĩa.
      setError(`Trình duyệt không cho 16kHz (đang ${ctx.sampleRate}Hz) — hãy gõ chữ.`);
      return false;
    }
    // PCM thô chứ KHÔNG dùng MediaRecorder: MediaRecorder đóng gói webm/opus và
    // chuỗi chunk ghép lại bị Speechmatics từ chối ("invalid audio").
    await ctx.audioWorklet.addModule("/pcm-worklet.js");
    const node = new AudioWorkletNode(ctx, "pcm-worklet");
    node.port.onmessage = (e) => {
      if (ws.current?.readyState === WebSocket.OPEN && recordingRef.current) {
        ws.current.send(e.data);
      }
    };
    ctx.createMediaStreamSource(stream).connect(node);
    audioCtx.current = ctx;
    return true;
  }, []);

  const send = useCallback((payload) => {
    if (ws.current?.readyState !== WebSocket.OPEN) return;
    ws.current.send(JSON.stringify(payload));
    setTurnState(null); // khoá ngay, khỏi gửi hai lần trước khi server trả lời
    setRecording(false);
    setPartial("");
  }, []);

  const myTurn = MIC_STATES.has(turnState) && !speaking;

  return {
    turns,
    partial,
    activity,
    ended,
    error,
    speaking,
    recording,
    myTurn,
    connected: Boolean(turnState) || Boolean(ended),
    start,
    send,
    setRecording,
    openMic,
    playerRef: player,
    onAudioEnded: playNext,
    skipAudio: () => {
      queue.current.length = 0;
      player.current?.pause();
      playNext();
    },
  };
}
