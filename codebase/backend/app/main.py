"""FastAPI entrypoint.

Chạy: uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.agents.student import StudentAgentSession, TurnState
from app.voice.stt import MockSTT
from app.voice.tts import MockTTS

app = FastAPI(title="Ke Doc Hanh — Track D3 teach-back")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/session")
async def voice_session(ws: WebSocket):
    """Một phiên = một lượt dạy lại một khái niệm. Audio vào/ra qua binary
    frame, text điều khiển (state, transcript tạm) qua JSON frame — tự định
    nghĩa schema cụ thể khi bắt tay build, đây chỉ là bộ khung state machine.
    """
    await ws.accept()

    stt = MockSTT()
    tts = MockTTS()
    session = StudentAgentSession(
        source_span="[Txx-NNN]",  # điền mã đoạn transcript thật khi build case
        concept="",  # điền tên khái niệm học viên sẽ dạy lại cho case đang chạy
    )

    try:
        while True:
            message = await ws.receive()
            # TODO: route theo session.state — audio binary vs control JSON.
            # Ngưỡng im lặng (VAD/endpointing) phải đổi theo session.state:
            # học viên là người nói chính, nên chỉ tăng ngưỡng chờ lên vài
            # giây khi vừa hỏi ngược (STUDENT_RESPONDING) — im lặng lúc đó
            # là đang suy nghĩ, không phải hết lượt.
            if session.state == TurnState.STUDENT_RESPONDING:
                pass
    except WebSocketDisconnect:
        pass
