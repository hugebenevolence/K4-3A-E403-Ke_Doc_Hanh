// Client phiên dạy-lại.
//
// Hai đường vào: gõ chữ hoặc nói. Đường gõ chữ chạy được ngay không cần mic và
// không lẫn lỗi nhận dạng giọng nói — hợp để thử phần sư phạm, và là phương án
// dự phòng nếu mic hỏng giữa buổi demo.
//
// Luật mic: chỉ mở khi backend báo state cho phép VÀ audio của agent đã phát
// xong. Thiếu vế sau thì mic bắt lại chính giọng agent qua loa, STT sẽ nghe
// agent nói và tưởng là học viên.

import { citationBox, indexSpans } from "./evidence.js";
import { loadSlides, setZoom, show, sourcePage, step } from "./slides.js";

const API = `http://${location.hostname}:8000`;
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
const partialEl = $("partial");
const pulseEl = $("pulse");

// Trạng thái hiện ra cho học viên. Không dùng biểu tượng: chữ đọc được bằng
// VoiceOver, dịch được, và không bị hiểu nhầm giữa các nền văn hoá.
function setLive(mode, text) {
  pulseEl.dataset.mode = mode; // idle | listening | working | speaking
  statusEl.textContent = text;
}

let ws = null;
let audioCtx = null;
let micNode = null;
let recording = false;
let turnState = null;
const audioQueue = [];
let isPlaying = false;

const live = () => ws?.readyState === WebSocket.OPEN;
const myTurn = () => MIC_STATES.has(turnState) && !isPlaying;

function log(role, text, filler, citesSpanId) {
  const turn = document.createElement("div");
  turn.className = `line ${role}${filler ? " filler" : ""}`;

  const who = document.createElement("span");
  who.className = "who";
  who.textContent = role === "student" ? "Bạn" : "Học trò AI";
  turn.append(who, document.createTextNode(text));

  // Agent trích slide thì hiện luôn nguyên văn chỗ đó — học viên thấy nó đang
  // dựa vào đúng chữ nào, không phải nói vu vơ.
  const cite = citesSpanId && citationBox(citesSpanId);
  if (cite) turn.append(cite);

  transcriptEl.append(turn);
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
  if (!mine) recording = false; // mic không được ăn lúc agent đang nói

  textInput.disabled = !mine;
  sendBtn.disabled = !mine;
  doneBtn.disabled = !mine || !recording;
  micBtn.disabled = !live() || !mine || recording;

  if (isPlaying) setLive("speaking", "Học trò AI đang nói");
  else if (mine && recording) setLive("listening", "Đang nghe — Space khi bạn nói xong");
  else if (mine) setLive("idle", "Tới lượt bạn");
  else if (turnState) setLive("working", "Học trò AI đang nghĩ");
}

function submitTurn(payload) {
  if (!live()) return;
  ws.send(JSON.stringify(payload));
  turnState = null; // khoá ngay, khỏi gửi hai lần trước khi server kịp trả lời
  applyTurnPolicy();
  setLive("working", "Đang nhận lời bạn");
}

textForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = textInput.value.trim();
  if (!text || !myTurn()) return;
  textInput.value = "";
  submitTurn({ type: "explanation_text", text });
});

textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) textForm.requestSubmit();
});

// Lấy audio bằng AudioWorklet chứ KHÔNG dùng MediaRecorder: MediaRecorder đóng
// gói webm/opus, và chuỗi chunk ghép lại bị Speechmatics từ chối thẳng ("Job
// rejected due to invalid audio"). PCM thô không có container nên không hỏng
// được, lại gửi liên tục nên nhận dạng chạy song song lúc học viên đang nói.
const SAMPLE_RATE = 16000;

async function openMic() {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
  if (audioCtx.sampleRate !== SAMPLE_RATE) {
    // Backend khai cứng 16kHz với Speechmatics; lệch tần số là ra chữ vô nghĩa.
    statusEl.textContent = `Trình duyệt không cho 16kHz (đang ${audioCtx.sampleRate}Hz) — hãy gõ chữ.`;
    return false;
  }
  await audioCtx.audioWorklet.addModule("js/pcm-worklet.js");
  micNode = new AudioWorkletNode(audioCtx, "pcm-worklet");
  micNode.port.onmessage = (e) => {
    if (live() && recording) ws.send(e.data);
  };
  audioCtx.createMediaStreamSource(stream).connect(micNode);
  return true;
}

micBtn.addEventListener("click", async () => {
  micBtn.blur();
  if (!audioCtx && !(await openMic())) return;
  await audioCtx.resume();
  recording = true;
  applyTurnPolicy();
});

function finishSpeaking() {
  // Chốt lượt bằng thao tác tường minh thay cho VAD tự động: học viên hay dừng
  // giữa chừng để nghĩ cách diễn đạt, endpointing tự động sẽ cắt sớm.
  if (!live() || !recording) return;
  recording = false;
  partialEl.hidden = true;
  submitTurn({ type: "explanation_done" });
}

doneBtn.addEventListener("click", () => {
  doneBtn.blur(); // trả focus về body, nếu không Space sẽ bấm lại chính nút này
  finishSpeaking();
});

document.addEventListener("keydown", (e) => {
  // Đang gõ chữ thì bàn phím thuộc về ô nhập, không phải phím tắt.
  if (document.activeElement === textInput || e.repeat) return;

  // Phím tắt điều hướng slide, dùng được cả khi chưa mở phiên.
  const shortcuts = {
    ArrowLeft: () => step(-1),
    ArrowRight: () => step(1),
    KeyF: () => toggleFocus(),
    KeyG: () => show(sourcePage()),
  };
  if (!e.ctrlKey && !e.metaKey && !e.altKey && shortcuts[e.code]) {
    e.preventDefault();
    return shortcuts[e.code]();
  }

  if (!document.body.classList.contains("focus") || !isTalkKey(e)) return;
  e.preventDefault();
  if (isPlaying) skipAgentAudio();
  else finishSpeaking();
});

startBtn.addEventListener("click", () => {
  transcriptEl.replaceChildren();
  ws = new WebSocket(`${API.replace("http", "ws")}/ws/session`);
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
    } else if (msg.type === "activity") {
      // Tiến trình THẬT của agent (tên node trong graph), không phải vòng xoay
      // đếm giờ giả. HIG khuyên chỉ báo xác định hơn chỉ báo mơ hồ.
      setLive("working", msg.label);
    } else if (msg.type === "partial") {
      // Chữ chạy theo lời nói, chưa chốt — hiện riêng một dòng mờ để học viên
      // thấy mic đang ăn, và thấy máy nghe ra đúng hay sai ngay lúc đang nói.
      partialEl.hidden = false;
      partialEl.textContent = msg.text;
    } else if (msg.type === "transcript") {
      partialEl.hidden = true;
      log(msg.role, msg.text, msg.filler, msg.cites_span_id);
    } else if (msg.type === "error") {
      statusEl.textContent = msg.message;
    } else if (msg.type === "session_end") {
      turnState = null;
      // Hết phiên mới mở hết nguyên văn: giữa phiên mà in ra ý học viên chưa
      // nói thì họ chỉ việc đọc, mất sạch ý nghĩa của việc hỏi ngược. Hết
      // phiên thì trỏ đúng chỗ cần xem lại lại chính là việc D3 yêu cầu.
      applyTurnPolicy();
      setLive(
        "idle",
        msg.outcome === "TAUGHT"
          ? "Học trò AI đã hiểu — xong phiên"
          : "Kết phiên — còn một chỗ nên xem lại",
      );
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

const focusBtn = $("focus-btn");

/** Chế độ vùng đang dạy: làm mờ phần còn lại của slide.
 *
 * Mục đích là để học viên và agent cùng bàn về ĐÚNG một chỗ. Slide 44 trang
 * với chữ dày đặc thì "ý cốt lõi" dễ trôi mất giữa những thứ xung quanh. */
function toggleFocus(on) {
  const next = on ?? !document.body.classList.contains("spotlight");
  document.body.classList.toggle("spotlight", next);
  focusBtn.setAttribute("aria-pressed", String(next));
  if (next) show(sourcePage());
}

focusBtn.addEventListener("click", () => {
  focusBtn.blur();
  toggleFocus();
});

document.getElementById("prev-page").addEventListener("click", () => step(-1));
document.getElementById("next-page").addEventListener("click", () => step(1));
document.getElementById("zoom-in").addEventListener("click", () => setZoom(1));
document.getElementById("zoom-out").addEventListener("click", () => setZoom(-1));
document
  .getElementById("goto-source")
  .addEventListener("click", () => show(sourcePage()));

// Khái niệm và slide đều lấy từ backend, không chép cứng vào HTML — đổi bài là
// đổi file bài học, không phải sửa hai chỗ.
fetch(`${API}/lesson`)
  .then((r) => r.json())
  .then(async (lesson) => {
    conceptEl.textContent = lesson.concept;
    indexSpans(lesson.spans);
    if (!lesson.has_slides) {
      document.getElementById("no-slides").hidden = false;
      return;
    }
    await loadSlides(`${API}/slides.pdf`, lesson.spans);
  })
  .catch((e) => {
    conceptEl.textContent = "(không kết nối được backend)";
    console.error(e);
  });
