// Client phiên dạy-lại.
//
// Luật mic: chỉ mở khi backend báo state cho phép VÀ audio của agent đã phát
// xong. Thiếu vế sau thì mic bắt lại chính giọng agent qua loa, STT sẽ nghe
// agent nói và tưởng là học viên.

const MIC_STATES = new Set(["STUDENT_TEACHING", "STUDENT_RESPONDING"]);

// Phím chốt lượt. Chọn Space vì đây là quy ước sẵn có cho thoại (push-to-talk),
// không đụng bộ gõ tiếng Việt, và không có ô nhập liệu nào trong màn này để
// tranh chấp. Alt+C giữ làm phương án hai cho ai quen tổ hợp phím hơn.
// (Ctrl+Space thì KHÔNG dùng được — nhiều bộ gõ tiếng Việt chiếm phím đó.)
const isTalkKey = (e) =>
  (e.code === "Space" && !e.ctrlKey && !e.metaKey && !e.altKey) ||
  (e.altKey && e.code === "KeyC");

const statusEl = document.getElementById("status");
const startBtn = document.getElementById("start-btn");
const doneBtn = document.getElementById("done-btn");
const transcriptEl = document.getElementById("transcript");
const audioEl = document.getElementById("ai-audio");
const conceptEl = document.getElementById("concept");

let ws = null;
let mediaRecorder = null;
let turnState = null;
const audioQueue = [];
let isPlaying = false;

const inFocusMode = () => document.body.classList.contains("focus");

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
  // Thu hồi URL của clip vừa phát, nếu không một phiên dài sẽ rò bộ nhớ dần.
  if (audioEl.src.startsWith("blob:")) URL.revokeObjectURL(audioEl.src);

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

function skipAgentAudio() {
  // Ngắt lời bằng phím là ý định tường minh của học viên, khác với barge-in tự
  // động bằng VAD (vẫn là stretch goal). Câu agent vừa nói còn trên màn hình
  // nên bỏ qua phần tiếng không mất thông tin.
  audioQueue.length = 0;
  audioEl.pause();
  playNext();
}

function applyMicPolicy() {
  const allowed = MIC_STATES.has(turnState) && !isPlaying;
  doneBtn.disabled = !allowed;

  if (allowed && mediaRecorder?.state === "inactive") {
    mediaRecorder.start(250);
    statusEl.textContent = "Đang nghe bạn giải thích… — nhấn Space khi nói xong";
  } else if (!allowed && mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
  }

  if (!allowed && !isPlaying && turnState) statusEl.textContent = "Học trò AI đang nghĩ…";
}

function sendDone() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "explanation_done" }));
  }
}

function finishTurn() {
  // Chốt hết lượt bằng thao tác tường minh thay cho VAD tự động: học viên hay
  // dừng giữa chừng để nghĩ cách diễn đạt, endpointing tự động sẽ cắt sớm.
  if (ws?.readyState !== WebSocket.OPEN || doneBtn.disabled) return;
  doneBtn.disabled = true;
  statusEl.textContent = "Học trò AI đang nghĩ…";

  if (mediaRecorder?.state === "recording") {
    // stop() đẩy nốt chunk audio cuối qua ondataavailable RỒI mới bắn sự kiện
    // "stop". Gửi explanation_done ngay ở đây là chunk cuối về sau tín hiệu
    // chốt lượt, và bị tính sang lượt kế tiếp — mất đoạn cuối câu học viên nói.
    mediaRecorder.addEventListener("stop", sendDone, { once: true });
    mediaRecorder.stop();
  } else {
    sendDone();
  }
}

document.addEventListener("keydown", (e) => {
  if (!inFocusMode() || !isTalkKey(e) || e.repeat) return;
  // Space cuộn trang, và nếu focus đang nằm trên nút thì còn bấm luôn nút đó.
  e.preventDefault();

  if (isPlaying) skipAgentAudio();
  else finishTurn();
});

doneBtn.addEventListener("click", () => {
  doneBtn.blur(); // trả focus về body, nếu không Space sẽ bấm lại chính nút này
  finishTurn();
});

startBtn.addEventListener("click", async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => {
    if (ws?.readyState === WebSocket.OPEN && e.data.size) ws.send(e.data);
  };

  ws = new WebSocket(`ws://${location.hostname}:8000/ws/session`);
  ws.binaryType = "blob";
  startBtn.disabled = true;
  startBtn.blur();
  document.body.classList.add("focus");

  ws.onmessage = (event) => {
    if (event.data instanceof Blob) return enqueueAudio(event.data);

    const msg = JSON.parse(event.data);
    if (msg.type === "state") {
      turnState = msg.state;
      applyMicPolicy();
    } else if (msg.type === "transcript") {
      log(msg.role, msg.text, msg.filler);
    } else if (msg.type === "error") {
      statusEl.textContent = msg.message;
    } else if (msg.type === "session_end") {
      turnState = null;
      document.body.classList.remove("focus");
      applyMicPolicy();
      statusEl.textContent =
        msg.outcome === "TAUGHT"
          ? "Học trò AI đã hiểu. Xong phiên!"
          : `Kết phiên — nên xem lại ${msg.review_spans.join(", ")}.`;
    }
  };

  ws.onclose = () => {
    turnState = null;
    startBtn.disabled = false;
    document.body.classList.remove("focus");
    applyMicPolicy();
    statusEl.textContent = "Đã ngắt kết nối";
  };
});

// Khái niệm cần dạy lấy từ backend, không chép cứng vào HTML — đổi bài là đổi
// file bài học, không phải sửa hai chỗ.
fetch(`http://${location.hostname}:8000/lesson`)
  .then((r) => r.json())
  .then((l) => (conceptEl.textContent = l.concept))
  .catch(() => (conceptEl.textContent = "(không kết nối được backend)"));
