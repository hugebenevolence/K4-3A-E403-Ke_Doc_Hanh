"""Adapter STT dùng Speechmatics (REST batch).

Đo thật trên tiếng Việt: đọc lại đúng nguyên văn cả dấu, mất ~2s cho một câu.

DÙNG BATCH CHỨ CHƯA DÙNG REALTIME, có chủ ý: tầng trên hiện gom hết audio của
một lượt rồi mới gọi STT (xem `_transcribe` trong main.py), nên partial chưa có
chỗ dùng. Port đã có sẵn dạng streaming, khi nào chuyển sang nuôi audio liên
tục thì thay phần thân hàm này bằng WebSocket realtime, call site không đổi.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.ports.stt import SpeechToText, Transcript

log = logging.getLogger(__name__)

API = "https://asr.api.speechmatics.com/v2/jobs"
POLL_EVERY_S = 0.75
POLL_TIMEOUT_S = 45.0

_CONFIG = json.dumps(
    {
        "type": "transcription",
        # operating_point "enhanced" đắt hơn nhưng tiếng Việt có dấu thì độ
        # chính xác quan trọng hơn: sai dấu là sai nghĩa, và bộ chấm ở sau sẽ
        # phạt oan học viên vì lỗi của máy nghe.
        "transcription_config": {"language": "vi", "operating_point": "enhanced"},
    }
)


class SpeechmaticsSTT(SpeechToText):
    def __init__(self, api_key: str | None = None):
        self._key = api_key or settings.speechmatics_api_key

    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        blob = b"".join([chunk async for chunk in audio])
        if len(blob) < 1024:
            # Vài chục byte thì không phải tiếng nói, gửi lên chỉ tốn một job.
            yield Transcript(text="", is_final=True)
            return

        headers = {"Authorization": f"Bearer {self._key}"}
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as http:
            created = await http.post(
                API,
                data={"config": _CONFIG},
                files={"data_file": ("turn.webm", blob, "audio/webm")},
            )
            created.raise_for_status()
            job_id = created.json()["id"]

            text = await self._await_transcript(http, job_id)

        yield Transcript(text=text, is_final=True)

    async def _await_transcript(self, http: httpx.AsyncClient, job_id: str) -> str:
        url = f"{API}/{job_id}/transcript?format=txt"
        deadline = asyncio.get_running_loop().time() + POLL_TIMEOUT_S
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(POLL_EVERY_S)
            got = await http.get(url)
            if got.status_code == 200:
                return got.text.strip()
            if got.status_code not in (404, 202):
                got.raise_for_status()

        log.warning("Speechmatics job %s quá %.0fs chưa xong, bỏ lượt", job_id, POLL_TIMEOUT_S)
        return ""
