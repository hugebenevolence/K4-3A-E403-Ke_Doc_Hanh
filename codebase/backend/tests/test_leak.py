"""Chặn câu hỏi ngược làm lộ đáp án — tiêu chí 15 điểm của rubric D3.

Case gốc là thứ quan sát được khi chạy thật: học viên nói "trên đó lạnh hơn",
agent hỏi lại "cái lạnh đó liên quan thế nào đến áp suất khí quyển" — đưa luôn
từ khoá học viên đang thiếu, học viên chỉ cần gật đầu là xong.
"""

from __future__ import annotations

from app.domain.leak import leaked_terms, leaks_answer, suggests_fix

UNCOVERED = "Nước sôi ở 100 độ C là do áp suất khí quyển ở mực nước biển đè lên mặt nước."
STUDENT = "Lên núi nước sôi thấp hơn là tại trên đó lạnh hơn nhiều."


def test_bat_duoc_cau_hoi_doc_ho_dap_an():
    q = "Mình hiểu là trên núi lạnh hơn, nhưng cái lạnh đó liên quan thế nào đến áp suất khí quyển?"
    assert leaks_answer(q, UNCOVERED, STUDENT)
    # "áp" bị lọc vì dưới MIN_TERM_LEN, nhưng "suất"/"quyển" là từ đặc trưng đủ để bắt.
    assert {"suất", "quyển"} <= leaked_terms(q, UNCOVERED, STUDENT)


def test_cau_hoi_mo_khong_bi_coi_la_lo():
    for q in [
        "Ừm, mình chưa hình dung được — vì sao lên cao lại thành ra như thế bạn?",
        "Bạn giải thích thêm giúp mình chỗ đó được không?",
        "Cái đó bắt đầu từ đâu ra vậy bạn?",
    ]:
        assert not leaks_answer(q, UNCOVERED, STUDENT), q


def test_nhac_lai_loi_hoc_vien_khong_phai_la_lo():
    # Học viên đã tự nói "lạnh" rồi, nhắc lại chính lời họ thì không lộ gì.
    q = "Bạn bảo trên núi lạnh hơn — cái lạnh đó dẫn tới chuyện gì tiếp theo?"
    assert not leaks_answer(q, UNCOVERED, STUDENT)


def test_mot_tu_trung_tinh_co_thi_chua_tinh_la_lo():
    # "nước" xuất hiện trong nguồn nhưng là từ không thể tránh khi nói về chủ đề.
    q = "Vậy nước ở trên đó thì khác gì dưới này bạn nhỉ?"
    assert not leaks_answer(q, UNCOVERED, STUDENT)


def test_khong_co_phan_thieu_thi_khong_co_gi_de_lo():
    assert not leaks_answer("Câu hỏi bất kỳ về áp suất khí quyển?", "", STUDENT)


# --- Bài code: lộ đáp án = mách cách sửa ------------------------------------
#
# Câu mách nước không trùng từ nào với nguồn (nguồn là code, lời mách là tiếng
# Việt), nên bộ lọc từ khoá ở trên không thấy. Phải bắt theo lối nói.


def test_bat_cau_mach_cach_sua():
    # Đúng câu agent đã tự viết ra khi prompt cấm suông: đưa sẵn tối ưu mà học
    # viên phải tự tìm ra.
    for q in [
        "Tại sao vòng trong lại duyệt từ đầu thay vì chỉ từ i+1?",
        "Lẽ ra chỗ này chỉ cần một vòng thôi phải không bạn?",
        "Dùng dict ở đây thì có tốt hơn không?",
    ]:
        assert suggests_fix(q), q


def test_cau_hoi_ve_code_dang_co_thi_khong_bi_chan():
    for q in [
        "Vòng lặp bên trong chạy bao nhiêu lần với mảng 5 phần tử?",
        "Dòng 7 đang so sánh hai giá trị nào vậy bạn?",
        "Bạn đọc dòng 4 giúp mình, nó đang làm gì?",
    ]:
        assert not suggests_fix(q), q
