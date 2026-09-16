"""Phiên nhận dạng cho MỘT lượt nói.

Tách khỏi main.py vì nó có vòng đời riêng: mở khi học viên bắt đầu nói, sống
suốt lượt đó, đóng khi họ bấm chốt. Trong lúc sống nó đẩy partial ra màn hình
để học viên thấy máy đang nghe tới đâu — không có cái đó thì học viên nói vào
khoảng không, không biết mic có ăn hay không.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

from app.ports.stt import SpeechToText

SENTINEL = None


class LiveTurn:
    def __init__(self, stt: SpeechToText, on_partial: Callable[[str], Awaitable[None]]):
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._task = asyncio.create_task(self._run(stt, on_partial))

    def feed(self, chunk: bytes) -> None:
        self._queue.put_nowait(chunk)

    async def finish(self) -> str:
        """Đóng nguồn audio và chờ transcript cuối cùng."""
        self._queue.put_nowait(SENTINEL)
        return await self._task

    async def abort(self) -> None:
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)

    async def _audio(self) -> AsyncIterator[bytes]:
        while (chunk := await self._queue.get()) is not SENTINEL:
            yield chunk

    async def _run(
        self, stt: SpeechToText, on_partial: Callable[[str], Awaitable[None]]
    ) -> str:
        final = ""
        async for piece in stt.stream(self._audio()):
            if piece.is_final:
                final = piece.text
            else:
                await on_partial(piece.text)
        return final
