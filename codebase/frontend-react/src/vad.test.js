// VAD sai thì hỏng im lặng: không có lỗi nào hiện ra, chỉ có học viên bị cắt
// lời hoặc ngồi chờ mãi không thấy gì. Mà đo bằng tay thì phải nói vào mic
// đúng nhịp — không lặp lại được. Nên chạy bằng chuỗi mức âm giả.

import { describe, expect, it } from "vitest";
import { createVad, feedVad, MIN_SPEECH_MS, MIN_THRESHOLD, resetVad } from "./vad";

const FRAME_MS = 128; // đúng một gói của worklet
const QUIET = 0.002; // phòng yên
const LOUD = 0.05; // nói bình thường
const FAN = 0.02; // máy chiếu/điều hoà chạy đều

const rep = (rms, ms) => Array(Math.ceil(ms / FRAME_MS)).fill(rms);

/** Nạp một chuỗi mức âm, trả về các sự kiện theo thứ tự. */
function play(vad, frames, silenceMs, startAt = 0) {
  const events = [];
  let now = startAt;
  for (const rms of frames) {
    const e = feedVad(vad, rms, now, silenceMs);
    if (e) events.push(e);
    now += FRAME_MS;
  }
  return events;
}

describe("feedVad", () => {
  it("chốt lượt khi học viên nói xong rồi im", () => {
    const events = play(
      createVad(),
      [...rep(QUIET, 500), ...rep(LOUD, 2000), ...rep(QUIET, 3000)],
      2000,
    );
    expect(events).toEqual(["end"]);
  });

  it("nói ngay khi mic vừa bật vẫn chốt được lượt", () => {
    // Lỗi thật của bản đầu: mức nền học bằng trung bình trượt nên chính giọng
    // học viên thành nền, ngưỡng vọt lên trên giọng nói, lượt không bao giờ
    // chốt. Học viên hăng hái nhất lại là người bị kẹt.
    const events = play(createVad(), [...rep(LOUD, 2000), ...rep(QUIET, 3000)], 2000);
    expect(events).toEqual(["end"]);
  });

  it("chờ đúng ngưỡng của state chứ không phải một ngưỡng chung", () => {
    // Cùng một chuỗi âm thanh, chỉ khác ngưỡng: đây chính là luật sư phạm ở
    // domain/session.py — im lặng sau câu hỏi ngược là đang nghĩ, không phải
    // đã nói xong. Ngập ngừng 3 giây phải bị chốt ở 2s mà không bị chốt ở 6s.
    const frames = [...rep(LOUD, 1000), ...rep(QUIET, 3000)];

    expect(play(createVad(), frames, 2000)).toEqual(["end"]);
    expect(play(createVad(), frames, 6000)).toEqual([]);
  });

  it("bỏ qua tiếng động ngắn thay vì chốt một lượt rỗng", () => {
    // Một tiếng ho rồi im. Chốt ở đây là gửi lên một lượt không có chữ nào, và
    // học viên mất oan một lượt hỏi ngược.
    const vad = createVad();
    expect(play(vad, [...rep(LOUD, 200), ...rep(QUIET, 3000)], 2000)).toEqual([]);
    expect(vad.speaking).toBe(false);
  });

  it("vẫn nghe tiếp sau một tiếng động ngắn", () => {
    const events = play(
      createVad(),
      [...rep(LOUD, 200), ...rep(QUIET, 3000), ...rep(LOUD, 1500), ...rep(QUIET, 3000)],
      2000,
    );
    expect(events).toEqual(["end"]);
  });

  it("MIN_SPEECH_MS là ngưỡng thật, không phải số trang trí", () => {
    const tail = rep(QUIET, 3000);
    const short = [...rep(LOUD, Math.floor(MIN_SPEECH_MS * 0.5)), ...tail];
    const long = [...rep(LOUD, Math.ceil(MIN_SPEECH_MS * 1.5)), ...tail];

    expect(play(createVad(), short, 2000)).toEqual([]);
    expect(play(createVad(), long, 2000)).toEqual(["end"]);
  });

  it("học được tiếng ồn đều của phòng và thôi coi nó là tiếng người", () => {
    // Phòng có máy chiếu kêu đều. Ngưỡng cố định sẽ nghe cái quạt thành người
    // nói và không bao giờ chốt được lượt nào.
    const vad = createVad();
    play(vad, rep(FAN, 8000), 2000);
    expect(vad.threshold).toBeGreaterThan(FAN);
  });

  it("nói trong phòng ồn vẫn nghe ra", () => {
    const vad = createVad();
    const primeMs = 6000;
    play(vad, rep(FAN, primeMs), 2000); // để nó học nền trước
    const events = play(
      vad,
      [...rep(0.12, 1500), ...rep(FAN, 3000)],
      2000,
      primeMs,
    );
    expect(events).toEqual(["end"]);
  });

  it("ngưỡng không bị chính giọng học viên kéo lên", () => {
    const vad = createVad();
    play(vad, rep(QUIET, 1000), 2000);
    const before = vad.threshold;
    play(vad, rep(LOUD, 3000), 2000, 1000);
    expect(vad.threshold).toBeCloseTo(before, 5);
  });

  it("phòng cực yên vẫn có sàn tuyệt đối", () => {
    const vad = createVad();
    play(vad, rep(0, 8000), 2000);
    expect(vad.threshold).toBe(MIN_THRESHOLD);
  });

  it("resetVad quên lượt cũ nhưng nhớ tiếng ồn của phòng", () => {
    const vad = createVad();
    play(vad, [...rep(FAN, 6000), ...rep(0.12, 1000)], 2000);
    const { floor } = vad;

    resetVad(vad);
    expect(vad.speaking).toBe(false);
    expect(vad.floor).toBe(floor);
  });
});
