"""Port lưu trữ: log phiên (replay được) và hồ sơ học viên (nhớ xuyên phiên)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.log import StudentProfile, TurnLog


class SessionLog(ABC):
    @abstractmethod
    async def append(self, turn: TurnLog) -> None: ...

    @abstractmethod
    async def replay(self, session_id: str) -> tuple[TurnLog, ...]: ...


class ProfileStore(ABC):
    @abstractmethod
    async def load(self, student_id: str) -> StudentProfile: ...

    @abstractmethod
    async def save(self, profile: StudentProfile) -> None: ...
