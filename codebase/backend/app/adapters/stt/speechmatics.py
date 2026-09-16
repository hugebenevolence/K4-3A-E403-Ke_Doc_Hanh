"""Adapter STT dùng Speechmatics realtime (WebSocket).

Đo thật trên tiếng Việt: đọc lại đúng nguyên văn cả dấu.

VÌ SAO REALTIME CHỨ KHÔNG PHẢI BATCH: bản batch đầu tiên nhận webm từ
MediaRecorder và bị từ chối thẳng — `{"code":400,"error":"Job rejected due to
invalid audio"}`. Chuỗi chunk webm ghép lại không thành file hợp lệ. Realtime
nhận PCM thô, không có container nên không có gì để hỏng; đổi lại còn được
partial để hiện chữ lên màn hình ngay khi học viên đang nói.

Định dạng chốt với frontend: PCM 16-bit little-endian, một kênh. Frontend lấy
bằng AudioWorklet (xem js/pcm-worklet.js), không dùng MediaRecorder.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import websockets

from app.config import settings
from app.ports.stt import SpeechToText, Transcript

log = logging.getLogger(__name__)

ENDPOINT = "wss://eu2.rt.speechmatics.com/v2"
IDLE_TIMEOUT_S = 30.0


def _start_message(sample_rate: int) -> str:
    return json.dumps(
        {
            "message": "StartRecognition",
            "audio_format": {
                "type": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": sample_rate,
            },
            "transcription_config": {
                "language": "vi",
                # Sai dấu là sai nghĩa, và bộ chấm ở sau sẽ phạt oan học viên
                # vì lỗi của máy nghe — nên trả thêm tiền cho "enhanced".
                "operating_point": "enhanced",
                "enable_partials": True,
                "max_delay": 2.0,
            },
        }
    )


class SpeechmaticsRealtimeSTT(SpeechToText):
    def __init__(self, api_key: str | None = None, sample_rate: int = 16000):
        self._key = api_key or settings.speechmatics_api_key
        self._sample_rate = sample_rate

    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        """Nuôi audio vào và nhả transcript ra — partial trước, final sau."""
        out: asyncio.Queue[Transcript | None] = asyncio.Queue()

        async with websockets.connect(
            ENDPOINT, additional_headers={"Authorization": f"Bearer {self._key}"}
        ) as sock:
            await sock.send(_start_message(self._sample_rate))
            feeder = asyncio.create_task(self._feed(sock, audio))
            reader = asyncio.create_task(self._read(sock, out))
            try:
                while (item := await asyncio.wait_for(out.get(), IDLE_TIMEOUT_S)) is not None:
                    yield item
            finally:
                for task in (feeder, reader):
                    task.cancel()
                await asyncio.gather(feeder, reader, return_exceptions=True)

    async def _feed(self, sock, audio: AsyncIterator[bytes]) -> None:
        sent = 0
        async for chunk in audio:
            await sock.send(chunk)
            sent += 1
        await sock.send(json.dumps({"message": "EndOfStream", "last_seq_no": sent}))

    async def _read(self, sock, out: asyncio.Queue[Transcript | None]) -> None:
        final = ""
        async for raw in sock:
            if isinstance(raw, bytes):
                continue
            msg = json.loads(raw)
            kind = msg.get("message")

            if kind == "AddPartialTranscript":
                if text := msg["metadata"]["transcript"].strip():
                    await out.put(Transcript(text=(final + " " + text).strip(), is_final=False))
            elif kind == "AddTranscript":
                # Speechmatics chốt từng mảnh một, phải cộng dồn mới ra cả lượt.
                # KHÔNG phát mảnh vừa chốt ra màn hình: nó ngắn hơn partial gần
                # nhất (đã gồm cả phần đuôi chưa chốt), nên chữ sẽ thụt lại rồi
                # dài ra liên tục — nhìn như đang giật. Cứ để partial kế tiếp
                # phát, nó đã cộng cả phần chốt mới vào rồi.
                final = (final + " " + msg["metadata"]["transcript"].strip()).strip()
            elif kind in ("EndOfTranscript", "Error"):
                if kind == "Error":
                    log.error("Speechmatics báo lỗi: %s", msg)
                await out.put(Transcript(text=final, is_final=True))
                await out.put(None)
                return
