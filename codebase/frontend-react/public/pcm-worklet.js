// Lấy audio thô từ mic: đổi sang PCM 16-bit cho STT, và đo mức âm cho VAD.
//
// Vì sao không dùng MediaRecorder: nó đóng gói webm/opus, và chuỗi chunk ghép
// lại bị Speechmatics từ chối ("Job rejected due to invalid audio"). PCM thô
// không có container nên không có gì để hỏng — mỗi gói byte tự nó đã hợp lệ.
//
// Gom trước khi gửi: process() chạy mỗi 128 mẫu, tức 125 lần/giây ở 16kHz.
// Gửi thẳng là 125 khung WebSocket mỗi giây, gói nào cũng 256 byte dữ liệu kèm
// cả phần đầu khung. Gom thành 128ms thì còn ~8 gói/giây mà độ trễ thêm không
// đáng kể so với max_delay 2s của Speechmatics.
//
// Mức âm đo ngay tại đây vì đây là chỗ DUY NHẤT thấy được từng mẫu. Luồng
// chính chỉ nhận một con số mỗi gói, không phải tự đi tính lại trên mảng.

const CHUNK_SAMPLES = 2048; // 16 lần process() = 128ms ở 16kHz

class PCMWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buf = new Float32Array(CHUNK_SAMPLES);
    this._filled = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;

    for (let i = 0; i < channel.length; i++) {
      this._buf[this._filled++] = channel[i];
      if (this._filled === CHUNK_SAMPLES) this._flush();
    }
    return true;
  }

  _flush() {
    const n = this._filled;
    this._filled = 0;

    // RMS trên Float32 [-1,1]: im lặng ~0.001, nói bình thường ~0.02–0.2.
    // Dùng thẳng thang này cho ngưỡng ở luồng chính, khỏi đổi đơn vị.
    let sum = 0;
    const pcm = new Int16Array(n);
    for (let i = 0; i < n; i++) {
      const s = Math.max(-1, Math.min(1, this._buf[i]));
      sum += s * s;
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage({ pcm: pcm.buffer, rms: Math.sqrt(sum / n) }, [pcm.buffer]);
  }
}

registerProcessor("pcm-worklet", PCMWorklet);
