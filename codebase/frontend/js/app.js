// Client phiên dạy-lại.
//
// Hai đường vào: gõ chữ hoặc nói. Đường gõ chữ chạy được ngay không cần mic và
// không lẫn lỗi nhận dạng giọng nói — hợp để thử phần sư phạm, và là phương án
// dự phòng nếu mic hỏng giữa buổi demo.
//
// Luật mic: chỉ mở khi backend báo state cho phép VÀ audio của agent đã phát
// xong. Thiếu vế sau thì mic bắt lại chính giọng agent qua loa, STT sẽ nghe
// agent nói và tưởng là học viên.

const MIC_STATES = new Set(["STUDENT_TEACHING", "STUDENT_RESPONDING"]);

// Phím chốt lượt. Space vì đây là quy ước sẵn có cho thoại (push-to-talk),
// không đụng bộ gõ tiếng Việt. Alt+C là phương án hai.
// (Ctrl+Space KHÔNG dùng được — nhiều bộ gõ tiếng Việt chiếm phím đó.)
const isTalkKey = (e) =>
  (e.code === "Space" && !e.ctrlKey && !e.metaKey && !e.altKey) ||
  (e.altKey && e.code === "KeyC");

const $ = (id) => document.getElementById(id);
const statusEl = $("status");
const startBtn = $("start-btn");
const micBtn = $("mic-btn");
const doneBtn = $("done-btn");
const transcriptEl = $("transcript");
const audioEl = $("ai-audio");
const conceptEl = $("concept");
const textForm = $("text-form");
const textInput = $("text-input");
const sendBtn = $("send-btn");

let ws = null;
let mediaRecorder = null;
let turnState = null;
const audioQueue = [];
let isPlaying = false;

const live = () => ws?.readyState === WebSocket.OPEN;
const myTurn = () => MIC_STATES.has(turnState) && !isPlaying;

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
    applyTurnPolicy();
    return;
  }
  isPlaying = true;
  applyTurnPolicy();
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

function applyTurnPolicy() {
  const mine = myTurn();
  const recording = mediaRecorder?.state === "recording";

  textInput.disabled = !mine;
  sendBtn.disabled = !mine;
  doneBtn.disabled = !mine || !recording;
  micBtn.disabled = !live() || !mine || recording;

  if (!mine && recording) mediaRecorder.stop();

  if (isPlaying) statusEl.textContent = "Học trò AI đang nói…";
  else if (mine) statusEl.textContent = recording
    ? "Đang nghe bạn giải thích… — Space khi nói xong"
    : "Tới lượt bạn — gõ chữ hoặc bật micro";
  else if (turnState) statusEl.textContent = "Học trò AI đang nghĩ…";
}

function submitTurn(payload) {
  if (!live()) return;
  ws.send(JSON.stringify(payload));
  turnState = null; // khoá ngay, khỏi gửi hai lần trước khi server kịp trả lời
  applyTurnPolicy();
  statusEl.textContent = "Học trò AI đang nghĩ…";
}

textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = textInput.value.trim();
  if (!text || !myTurn()) return;
  log("student", text, false);
  textInput.value = "";
  submitTurn({ type: "explanation_text", text });
});

textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) textForm.requestSubmit();
});

micBtn.addEventListener("click", async () => {
  micBtn.blur();
  if (!mediaRecorder) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => {
      if (live() && e.data.size) ws.send(e.data);
    };
  }
  if (mediaRecorder.state === "inactive") mediaRecorder.start(250);
  applyTurnPolicy();
});

function finishSpeaking() {
  // Chốt lượt bằng thao tác tường minh thay cho VAD tự động: học viên hay dừng
  // giữa chừng để nghĩ cách diễn đạt, endpointing tự động sẽ cắt sớm.
  if (!live() || mediaRecorder?.state !== "recording") return;
  // stop() đẩy nốt chunk audio cuối qua ondataavailable RỒI mới bắn sự kiện
  // "stop". Gửi explanation_done ngay ở đây là chunk cuối về sau tín hiệu chốt
  // lượt, và bị tính sang lượt kế tiếp — mất đoạn cuối câu học viên nói.
  mediaRecorder.addEventListener(
    "stop",
    () => submitTurn({ type: "explanation_done" }),
    { once: true },
  );
  mediaRecorder.stop();
}

doneBtn.addEventListener("click", () => {
  doneBtn.blur(); // trả focus về body, nếu không Space sẽ bấm lại chính nút này
  finishSpeaking();
});

document.addEventListener("keydown", (e) => {
  if (!document.body.classList.contains("focus") || !isTalkKey(e) || e.repeat) return;
  if (document.activeElement === textInput) return; // đang gõ chữ thì Space là dấu cách
  e.preventDefault();

  if (isPlaying) skipAgentAudio();
  else finishSpeaking();
});

startBtn.addEventListener("click", () => {
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
      applyTurnPolicy();
    } else if (msg.type === "transcript") {
      // Lời học viên gõ đã hiện lúc gửi rồi, khỏi hiện lại.
      if (msg.role !== "student") log(msg.role, msg.text, msg.filler);
    } else if (msg.type === "error") {
      statusEl.textContent = msg.message;
    } else if (msg.type === "session_end") {
      turnState = null;
      document.body.classList.remove("focus");
      applyTurnPolicy();
      statusEl.textContent =
        msg.outcome === "TAUGHT"
          ? "🎉 Học trò AI đã hiểu. Xong phiên!"
          : `Kết phiên — nên xem lại ${msg.review_spans.join(", ")}.`;
    }
  };

  ws.onclose = () => {
    turnState = null;
    startBtn.disabled = false;
    document.body.classList.remove("focus");
    applyTurnPolicy();
    statusEl.textContent = "Đã ngắt kết nối";
  };
});

// Khái niệm cần dạy lấy từ backend, không chép cứng vào HTML — đổi bài là đổi
// file bài học, không phải sửa hai chỗ.
fetch(`http://${location.hostname}:8000/lesson`)
  .then((r) => r.json())
  .then((l) => (conceptEl.textContent = l.concept))
  .catch(() => (conceptEl.textContent = "(không kết nối được backend)"));
