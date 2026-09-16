// Mic capture + WebSocket client — khung tối thiểu, điền phần streaming
// audio thật khi backend đã có provider STT/TTS thật (xem codebase/README.md).

const statusEl = document.getElementById("status");
const startBtn = document.getElementById("start-btn");
const doneBtn = document.getElementById("done-btn");
const transcriptEl = document.getElementById("transcript");

let ws = null;
let mediaRecorder = null;

startBtn.addEventListener("click", async () => {
  ws = new WebSocket(`ws://${location.hostname}:8000/ws/session`);

  ws.onopen = async () => {
    statusEl.textContent = "Đã kết nối — bạn đang giải thích";
    doneBtn.disabled = false;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(e.data);
    };
    mediaRecorder.start(250);
    // TODO: chỉ tự động tách câu bằng VAD phía backend khi đã có; MVP dùng
    // nút "Tôi giải thích xong" tường minh để báo hết lượt (STUDENT_TEACHING
    // / STUDENT_RESPONDING -> CHECKING), tránh cắt lượt sớm khi học viên
    // đang dừng lại suy nghĩ cách diễn đạt.
  };

  ws.onmessage = (event) => {
    // TODO: phân biệt audio chunk (TTS) vs control message (transcript, state)
    transcriptEl.textContent += event.data + "\n";
  };

  ws.onclose = () => {
    statusEl.textContent = "Đã ngắt kết nối";
    doneBtn.disabled = true;
  };
};

doneBtn.addEventListener("click", () => {
  // MVP: báo hết lượt bằng nút bấm tường minh, thay cho VAD/endpointing tự
  // động ban đầu — xem TODO ở trên.
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "explanation_done" }));
    statusEl.textContent = "Đang chờ AI đối chiếu với nguồn...";
  }
});
