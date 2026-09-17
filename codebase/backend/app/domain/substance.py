"""Sàn tối thiểu để một lượt chấm có nghĩa — cho cả hai đầu của phép chấm.

Toàn bộ guard hiện có (`verbatim.py`, `leak.py`) đều chống chấm OAN: đừng vu
học viên chép sách, đừng nói hộ đáp án. Không có guard nào chống chiều ngược
lại — CHO QUA một lời giảng chưa tới — mà đó mới là lỗi đắt nhất: học viên
đóng phiên với niềm tin mình đã hiểu.

Hai chỗ hổng đo được trên dữ liệu thật:

1. **Nguồn rỗng ruột.** Phiên 2e6d52f3 (`var/sessions.jsonl`): học viên mở
   TRANG BÌA slide, vùng nguồn chỉ có dòng tiêu đề + câu tagline. "Ý cốt lõi"
   mà bộ chấm rút ra chính là câu tiêu đề, nên câu nào nhắc tới AI/LLM cũng
   "chạm" được nó — 9 chữ là đóng phiên TAUGHT.

2. **Lời giảng quá ngắn.** Đo lại 4 lượt chạy golden set gần nhất
   (`eval/results/`): mọi lượt SUFFICIENT ĐÚNG đều từ 27 từ trở lên, còn mọi
   lượt SUFFICIENT SAI vì nói quá ngắn đều ở 16 từ trở xuống (A03 4 từ, A01 13
   từ, N08 16 từ). Hai nhóm tách hẳn nhau.

Làm bằng luật tất định thay vì siết prompt: không tốn token, không dao động
giữa các lượt chạy, và chặn được cả khi model đang "dễ tính".
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from app.domain.span import Span

_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def word_count(text: str) -> int:
    return len(_WORD.findall(text or ""))


MIN_STUDENT_WORDS = 20
"""Dưới ngần này từ (cộng dồn cả buổi) thì chưa thể coi là đã giảng lại.

Nằm giữa hai nhóm đo được: 16 (lượt cho qua oan cao nhất) và 27 (lượt đạt thật
thấp nhất). Cố ý đặt lệch về phía thấp — chặn hụt vài lượt còn hơn bắt oan một
người đã giảng đúng.

Đây là SÀN, không phải chuẩn: nói đủ 20 từ không làm ai đạt cả, chỉ là dưới
mức đó thì không đủ dữ kiện để kết luận là đạt.
"""


def is_thin_teachback(said: Sequence[str]) -> bool:
    """Cả buổi học viên mới nói được bằng này thì chưa đủ để chấm là đã giảng.

    Tính CỘNG DỒN cả buổi chứ không theo từng lượt: người giảng một nửa ở lượt
    đầu rồi nửa còn lại khi được hỏi ngược vẫn là đã giảng đủ.

    Lượt trùng y nguyên chỉ tính một lần. Nói lại đúng câu cũ không phải là nói
    thêm, mà cộng dồn thẳng thì lặp ba lần một câu tám chữ là vượt sàn — đúng
    kiểu hỏng mà sàn này sinh ra để chặn. Máy nhận dạng phát lại một bản final
    cũng rơi vào đây.
    """
    distinct = dict.fromkeys(" ".join(text.split()).lower() for text in said)
    return sum(word_count(text) for text in distinct) < MIN_STUDENT_WORDS


MIN_SOURCE_WORDS = 24
"""Vùng nguồn ít chữ hơn ngần này (đã trừ tiêu đề trang) thì không có gì để giảng.

Đo trên cả 58 trang của hai bộ slide, đếm chữ từng trang sau khi bỏ ô tiêu đề:
hai trang bìa ra 16 và 18 từ, trang nội dung mỏng nhất kế tiếp ra 29 từ. Khoảng
trống 18 → 29 là chỗ đặt ngưỡng; 24 nằm giữa.

Trừ tiêu đề trang là phần quan trọng nhất của phép đo: tiêu đề là TÊN của phần
cần giảng, không phải nội dung để giảng. Đếm cả tiêu đề thì trang bìa vượt
ngưỡng nhờ đúng dòng chữ mà học viên không có gì để nói về nó.
"""


def teachable_words(spans: Iterable[Span], title: str) -> int:
    """Số chữ THỰC SỰ giảng được trong một vùng: bỏ ô trùng tiêu đề trang.

    `title` KHÔNG có giá trị mặc định, cố ý. Quên nó là phép đo đổi nghĩa trong
    im lặng: đúng trang bìa của bộ slide ra 18 từ khi trừ tiêu đề và 23 từ khi
    không trừ — tức là vượt ngưỡng nhờ đúng dòng chữ mà học viên không có gì để
    nói về nó. Trang không có tiêu đề thì truyền "".
    """
    head = " ".join((title or "").split())
    return sum(
        word_count(s.text) for s in spans if " ".join(s.text.split()) != head
    )
