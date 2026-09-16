"""FastAPI entrypoint.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.agents.peer import PeerAgentSession, TurnState
from app.voice.stt import MockSTT
from app.voice.tts import MockTTS

app = FastAPI(title="Ke Doc Hanh — Track D1 voice classroom")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/session")
async def voice_session(ws: WebSocket):
    """Một phiên = một lượt ôn khái niệm. Audio vào/ra qua binary frame,
    text điều khiển (state, transcript tạm) qua JSON frame — tự định nghĩa
    schema cụ thể khi bắt tay build, đây chỉ là bộ khung state machine.
    """
    await ws.accept()

    stt = MockSTT()
    tts = MockTTS()
    session = PeerAgentSession(
        source_span="[Txx-NNN]",  # điền mã đoạn transcript thật khi build case
        misconception="",  # điền câu hiểu-sai của persona cho case đang chạy
    )

    try:
        while True:
            message = await ws.receive()
            # TODO: route theo session.state — audio binary vs control JSON.
            # Ngưỡng ngắt lời (VAD/endpointing) phải đổi theo session.state:
            # ngắn khi AI_SPEAKING, dài khi vừa hỏi ngược (CONFIRMING).
            if session.state == TurnState.AI_SPEAKING:
                pass
    except WebSocketDisconnect:
        pass
