"""Tiến độ học của một học viên: mức hiểu của TỪNG trang slide, qua mọi buổi.

Mức hiểu suy ra từ KẾT QUẢ CHẤM, không từ thời gian đã bỏ ra: mở một trang ra
đọc mười phút không làm nó thành "đã hiểu". Đây là cùng điều kiện đặt lên bản
đồ hiểu biết (spec §4c) — Open Learner Model chỉ có ích khi mô hình máy có về
người học là ĐÚNG, nên chỉ những gì bộ chấm xác nhận mới được tính.

Và khớp với bản đồ: "đã hiểu" trở lên đúng bằng đỉnh sáng; giảng sai thì bản đồ
tắt đỉnh, còn ở đây trang chuyển sang "cần sửa" — hai nơi không bao giờ nói
ngược nhau về cùng một trang.

Thuần domain: không I/O, test được không cần key.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

LEVELS = ("moi", "dang_hoc", "can_sua", "da_hieu", "vung")
"""Thứ tự hiển thị. `can_sua` đứng dưới `da_hieu` vì nó là trạng thái cần làm gì
đó ngay, không phải một bậc tiến bộ."""

SOLID_SESSIONS = 2
"""Được chấm đủ ở ngần này BUỔI khác nhau thì là vững.

Một lần giảng được có thể là nhớ ngắn hạn — vừa đọc xong là giảng. Giảng lại
được ở một buổi khác mới là dấu hiệu nhớ được qua thời gian (spacing effect).
"""

MAX_SESSIONS = 30
"""Số buổi giữ lại mỗi trang — đủ để đếm, không để file phình vô hạn."""


@dataclass(frozen=True)
class PageProgress:
    sessions: tuple[str, ...] = ()
    taught_sessions: tuple[str, ...] = ()
    last_verdict: str = ""
    first_at: str = ""
    last_at: str = ""

    @property
    def level(self) -> str:
        if not self.sessions:
            return "moi"
        if self.last_verdict == "incorrect":
            return "can_sua"
        if len(self.taught_sessions) >= SOLID_SESSIONS:
            return "vung"
        if self.taught_sessions:
            return "da_hieu"
        return "dang_hoc"


@dataclass
class Progress:
    student_id: str
    pages: dict[str, PageProgress] = field(default_factory=dict)

    def record(self, page_key: str, session_id: str, verdict: str, at: str) -> str:
        """Ghi một lượt vừa chấm. Trả về mức hiểu mới của trang.

        Ghi theo LƯỢT nhưng đếm theo BUỔI: một buổi ba lượt vẫn là một buổi.
        Lượt đủ sau một lượt sai trong cùng buổi thì trang hết "cần sửa" — học
        viên đã tự sửa được ngay trong buổi đó.
        """
        nhan = (verdict or "").lower()
        cu = self.pages.get(page_key, PageProgress(first_at=at))
        taught = cu.taught_sessions
        if nhan == "sufficient" and session_id not in taught:
            taught = (*taught, session_id)
        moi = replace(
            cu,
            sessions=tuple(dict.fromkeys([*cu.sessions, session_id]))[-MAX_SESSIONS:],
            taught_sessions=taught[-MAX_SESSIONS:],
            last_verdict=nhan,
            first_at=cu.first_at or at,
            last_at=at,
        )
        self.pages[page_key] = moi
        return moi.level
