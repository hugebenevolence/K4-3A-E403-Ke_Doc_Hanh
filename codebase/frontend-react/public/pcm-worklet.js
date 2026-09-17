// Lấy audio thô từ mic, đổi sang PCM 16-bit để gửi thẳng lên STT realtime.
//
// Vì sao không dùng MediaRecorder: nó đóng gói webm/opus, và chuỗi chunk ghép
// lại bị Speechmatics từ chối ("Job rejected due to invalid audio"). PCM thô
// không có container nên không có gì để hỏng — mỗi gói byte tự nó đã hợp lệ.

class PCMWorklet extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    // Float32 [-1,1] -> Int16 little-endian, đúng định dạng pcm_s16le.
    const pcm = new Int16Array(channel.length);
    for (let i = 0; i < channel.length; i++) {
      const clamped = Math.max(-1, Math.min(1, channel[i]));
      pcm[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    }
    this.port.postMessage(pcm.buffer, [pcm.buffer]);
    return true;
  }
}

registerProcessor("pcm-worklet", PCMWorklet);
