// Client phiên dạy-lại.
//
// Luật mic: chỉ mở khi backend báo state cho phép VÀ audio của agent đã phát
// xong. Thiếu vế sau thì mic bắt lại chính giọng agent qua loa, STT sẽ nghe
// agent nói và tưởng là học viên.

const MIC_STATES = new Set(["STUDENT_TEACHING", "STUDENT_RESPONDING"]);

const statusEl = document.getElementById("status");
const startBtn = document.getElementById("start-btn");
const doneBtn = document.getElementById("done-btn");
const transcriptEl = document.getElementById("transcript");
const audioEl = document.getElementById("ai-audio");

let ws = null;
let mediaRecorder = null;
let turnState = null;
const audioQueue = [];
let isPlaying = false;

function log(role, text, filler) {
  const line = document.createElement("p");
  line.className = `line ${role}${filler ? " filler" : ""}`;
  line.textContent = `${role === "student" ? "Bạn" : "Học trò AI"}: ${text}`;
  transcriptEl.append(line);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function enqueueAudio(blob) {
  audioQueue.push(blob);
  if (!isPlaying) playNext();
}

function playNext() {
  const blob = audioQueue.shift();
  if (!blob) {
    isPlaying = false;
    applyMicPolicy();
    return;
  }
  isPlaying = true;
  applyMicPolicy();
  audioEl.src = URL.createObjectURL(blob);
  audioEl.play().catch(() => playNext());
}

audioEl.addEventListener("ended", playNext);
audioEl.addEventListener("error", playNext);

function applyMicPolicy() {
  const allowed = MIC_STATES.has(turnState) && !isPlaying;
  doneBtn.disabled = !allowed;

  if (allowed && mediaRecorder?.state === "inactive") {
    mediaRecorder.start(250);
    statusEl.textContent = "Đang nghe bạn giải thích…";
  } else if (!allowed && mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
  }

  if (!allowed && !isPlaying) statusEl.textContent = "Học trò AI đang nghĩ…";
}

startBtn.addEventListener("click", async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => {
    if (ws?.readyState === WebSocket.OPEN && e.data.size) ws.send(e.data);
  };

  ws = new WebSocket(`ws://${location.hostname}:8000/ws/session`);
  ws.binaryType = "blob";
  startBtn.disabled = true;

  ws.onmessage = (event) => {
    if (event.data instanceof Blob) return enqueueAudio(event.data);

    const msg = JSON.parse(event.data);
    if (msg.type === "state") {
      turnState = msg.state;
      applyMicPolicy();
    } else if (msg.type === "transcript") {
      log(msg.role, msg.text, msg.filler);
    } else if (msg.type === "session_end") {
      turnState = null;
      applyMicPolicy();
      statusEl.textContent =
        msg.outcome === "TAUGHT"
          ? "Học trò AI đã hiểu. Xong phiên!"
          : `Kết phiên — nên xem lại đoạn ${msg.source_span}.`;
    }
  };

  ws.onclose = () => {
    turnState = null;
    startBtn.disabled = false;
    applyMicPolicy();
    statusEl.textContent = "Đã ngắt kết nối";
  };
});

doneBtn.addEventListener("click", () => {
  // Chốt hết lượt bằng nút bấm tường minh thay cho VAD tự động: học viên hay
  // dừng giữa chừng để nghĩ cách diễn đạt, endpointing tự động sẽ cắt sớm.
  if (ws?.readyState !== WebSocket.OPEN) return;
  mediaRecorder?.stop();
  ws.send(JSON.stringify({ type: "explanation_done" }));
  doneBtn.disabled = true;
  statusEl.textContent = "Học trò AI đang nghĩ…";
});
