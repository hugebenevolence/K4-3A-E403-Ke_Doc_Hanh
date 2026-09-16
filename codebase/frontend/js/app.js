// Mic capture + WebSocket client — khung tối thiểu, điền phần streaming
// audio thật khi backend đã có provider STT/TTS thật (xem codebase/README.md).

const statusEl = document.getElementById("status");
const startBtn = document.getElementById("start-btn");
const raiseHandBtn = document.getElementById("raise-hand-btn");
const transcriptEl = document.getElementById("transcript");

let ws = null;
let mediaRecorder = null;

startBtn.addEventListener("click", async () => {
  ws = new WebSocket(`ws://${location.hostname}:8000/ws/session`);

  ws.onopen = async () => {
    statusEl.textContent = "Đã kết nối — AI đang nói";
    raiseHandBtn.disabled = false;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(e.data);
    };
    // TODO: chỉ start recorder liên tục khi đã có VAD phía backend để tách
    // "giơ tay tự nhiên bằng giọng" khỏi ồn nền — MVP dùng nút bấm trước.
  };

  ws.onmessage = (event) => {
    // TODO: phân biệt audio chunk (TTS) vs control message (transcript, state)
    transcriptEl.textContent += event.data + "\n";
  };

  ws.onclose = () => {
    statusEl.textContent = "Đã ngắt kết nối";
    raiseHandBtn.disabled = true;
  };
};

raiseHandBtn.addEventListener("click", () => {
  // MVP: ngắt lời bằng nút bấm tường minh, thay cho VAD tự động ban đầu.
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "raise_hand" }));
    mediaRecorder?.start(250);
    statusEl.textContent = "Đang nghe bạn nói...";
  }
});
