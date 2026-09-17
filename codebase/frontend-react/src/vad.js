// Nhận ra lúc học viên đã nói xong, để họ không phải bấm nút chốt lượt.
//
// Vì sao đáng làm: bắt bấm "Xong" sau mỗi lượt nghe thì có vẻ nhỏ, nhưng nó
// biến một cuộc trò chuyện thành một cái máy đàm — học viên phải nhớ mình đang
// điều khiển thiết bị trong lúc đang cố diễn đạt một ý khó. Đúng lúc cần nghĩ
// nhất thì phần đầu lại bận nhớ thao tác.
//
// NGƯỠNG IM LẶNG KHÔNG PHẢI HẰNG SỐ. Nó do backend gửi xuống theo state
// (domain/session.py): ~2s khi học viên đang tự giảng, nhưng ~6s ngay sau một
// câu hỏi ngược, vì im lặng lúc đó là đang nghĩ chứ không phải đã nói xong.
// Gộp thành một ngưỡng chung là cắt lời học viên đúng lúc họ suy nghĩ.
//
// MỨC NỀN ĐO BẰNG CỰC TIỂU TRƯỢT, KHÔNG PHẢI TRUNG BÌNH TRƯỢT. Bản đầu dùng
// trung bình và test bắt được ngay: học viên nói ngay khi mic vừa bật thì
// chính giọng họ thành mức nền, ngưỡng vọt lên trên giọng nói, và lượt đó
// không bao giờ tự chốt. Cực tiểu thì miễn nhiễm — trong bất kỳ 5 giây nào của
// lời nói tự nhiên đều có khoảng lặng giữa các từ, và khoảng lặng ấy chính là
// mức nền của căn phòng.

/** Nói ngắn hơn mức này thì coi là tiếng động (ho, gõ bàn), không phải một lượt. */
export const MIN_SPEECH_MS = 600;

/** To hơn nền bao nhiêu lần thì tính là tiếng người. */
export const NOISE_FACTOR = 3;

/** Sàn tuyệt đối: phòng cực yên thì nền ~0, nhân mấy cũng vẫn ~0. */
export const MIN_THRESHOLD = 0.008;

/**
 * Số gói dùng để ước lượng mức nền — 40 gói × 128ms ≈ 5 giây.
 *
 * Ngắn hơn thì một câu dài liên tục sẽ lọt hết vào cửa sổ và kéo nền lên. Dài
 * hơn thì phòng ồn phải chờ lâu mới thích nghi. Giới hạn đã biết: ai nói hơn
 * 5 giây mà không có lấy một khoảng lặng 128ms nào thì VAD sẽ điếc — lúc đó
 * vẫn còn nút "Xong" và phím Space.
 */
const FLOOR_WINDOW = 40;

/** Nền giả định lúc chưa đủ dữ liệu: đủ nhỏ để không bỏ sót ai nói nhỏ. */
const DEFAULT_FLOOR = MIN_THRESHOLD / NOISE_FACTOR;

/** Mức RMS coi là "nói to rõ" — dùng để quy về thang 0..1 cho vạch mức âm. */
const FULL_SCALE = 0.15;

export function createVad() {
  return {
    recent: [],
    floor: DEFAULT_FLOOR,
    threshold: MIN_THRESHOLD,
    speaking: false,
    startedAt: 0,
    lastVoiceAt: 0,
  };
}

/** Bắt đầu một lượt nghe mới: quên hết những gì nghe được ở lượt trước. */
export function resetVad(vad) {
  vad.speaking = false;
  vad.startedAt = 0;
  vad.lastVoiceAt = 0;
  // Giữ lại cửa sổ mức nền: tiếng ồn của căn phòng không đổi giữa hai lượt,
  // học lại từ đầu mỗi lượt chỉ làm ngưỡng dao động vô ích.
}

/**
 * Nạp một gói âm thanh. Trả về `"end"` khi học viên đã nói xong, `null` khi
 * chưa có gì để quyết.
 */
export function feedVad(vad, rms, now, silenceMs) {
  vad.recent.push(rms);
  if (vad.recent.length > FLOOR_WINDOW) vad.recent.shift();
  // Chưa đủ một cửa sổ thì chưa tin được cực tiểu — cứ giả định phòng yên, thà
  // nhạy quá còn hơn điếc.
  vad.floor =
    vad.recent.length < FLOOR_WINDOW
      ? Math.min(DEFAULT_FLOOR, ...vad.recent)
      : Math.min(...vad.recent);
  vad.threshold = Math.max(vad.floor * NOISE_FACTOR, MIN_THRESHOLD);

  if (rms > vad.threshold) {
    vad.lastVoiceAt = now;
    if (!vad.speaking) {
      vad.speaking = true;
      vad.startedAt = now;
    }
    return null;
  }

  if (!vad.speaking || now - vad.lastVoiceAt < silenceMs) return null;

  // Đã im đủ lâu. Nhưng nếu cả lượt chỉ dài bằng một tiếng ho thì đó là tiếng
  // động, không phải lượt nói — bỏ qua và chờ tiếp thay vì chốt một lượt rỗng.
  const spoken = vad.lastVoiceAt - vad.startedAt;
  vad.speaking = false;
  return spoken >= MIN_SPEECH_MS ? "end" : null;
}

/** Quy RMS về thang 0..1 để vẽ vạch mức âm. */
export function levelOf(rms) {
  return Math.min(1, rms / FULL_SCALE);
}
