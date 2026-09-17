"""Log phiên ra JSONL + hồ sơ học viên ra JSON.

Chọn file phẳng thay vì DB: đủ cho quy mô hackathon, và quan trọng hơn là
`eval/` đọc thẳng được để dựng golden set từ phiên thật.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.domain.log import StudentProfile, TurnLog
from app.ports.store import ProfileStore, SessionLog

log = logging.getLogger(__name__)


class JsonlSessionLog(SessionLog):
    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    async def append(self, turn: TurnLog) -> None:
        record = asdict(turn)
        if turn.grade is not None:
            record["grade"]["verdict"] = turn.grade.verdict.value
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def replay(self, session_id: str) -> tuple[TurnLog, ...]:
        if not self._path.is_file():
            return ()
        rows = [
            json.loads(line)
            for line in self._path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return tuple(
            TurnLog(
                session_id=r["session_id"],
                turn_index=r["turn_index"],
                student_text=r["student_text"],
                source_span_id=r["source_span_id"],
                prompt_versions=r["prompt_versions"],
                grade=None,  # dựng lại GradeResult khi runner eval cần, không phải ở đây
                agent_said=r["agent_said"],
                latency_ms=r.get("latency_ms", {}),
                at=r["at"],
            )
            for r in rows
            if r["session_id"] == session_id
        )


class JsonProfileStore(ProfileStore):
    def __init__(self, path: Path):
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def _all(self) -> dict:
        if not self._path.is_file():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except ValueError:
            # File hỏng thì KHÔNG được ném lỗi lên: hồ sơ được nạp ngay khi mở
            # kết nối, nên một file méo là mọi phiên của mọi người đều không vào
            # được. Dẹp nó sang một bên rồi bắt đầu lại — mất trí nhớ cũ còn hơn
            # mất cả sản phẩm, và file cũ vẫn còn đó để xem sau.
            # Tên có mốc thời gian, KHÔNG dùng một tên cố định: hỏng lần hai sẽ
            # đè mất bản cứu được của lần một, tức là xoá mất đúng thứ vừa hứa
            # là "vẫn còn đó để xem sau".
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            broken = self._path.with_name(f"{self._path.stem}.hong-{stamp}.json")
            self._path.replace(broken)
            log.error("Hồ sơ học viên hỏng, đã chuyển sang %s và bắt đầu lại", broken)
            return {}

    async def load(self, student_id: str) -> StudentProfile:
        raw = self._all().get(student_id)
        if raw is None:
            return StudentProfile(student_id=student_id)
        return StudentProfile(**raw)

    async def save(self, profile: StudentProfile) -> None:
        data = self._all()
        data[profile.student_id] = asdict(profile)
        # Ghi ra file tạm rồi ĐỔI CHỖ, không ghi đè thẳng: `write_text` cắt file
        # về rỗng trước khi viết, nên tắt server đúng lúc đó là còn lại một file
        # JSON cụt — và hồ sơ hỏng thì mọi phiên sau đều không mở được.
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)
