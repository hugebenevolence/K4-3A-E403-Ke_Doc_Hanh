"""Port lưu trữ: log phiên (replay được), hồ sơ học viên, và đồ thị tri thức.

Ba thứ nhớ khác nhau: log để dựng lại một buổi, hồ sơ để biết học viên hay vấp
đâu, đồ thị để biết họ đã DẠY ĐƯỢC những gì (spec §4c).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.graph import KnowledgeGraph
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


class GraphStore(ABC):
    """Đồ thị tri thức của từng học viên, sống qua mọi buổi và mọi tài liệu."""

    @abstractmethod
    async def load(self, student_id: str) -> KnowledgeGraph: ...

    @abstractmethod
    async def save(self, graph: KnowledgeGraph) -> None: ...
