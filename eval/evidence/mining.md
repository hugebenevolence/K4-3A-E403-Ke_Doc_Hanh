# Nhật ký mining — chatlog tutor VLearn (chuẩn B)

Nguồn: `brief/data/vlearn-pack/chatlog/tutor_turns.csv` — 13.494 lượt hỏi-đáp, 1.617 học viên, 22/07–15/09/2026; trong đó khoá hiện tại K4 là 3.097 lượt, 448 học viên. Data pack không nằm trong repo; mọi trích dẫn dưới đây dẫn theo `turn_id`, mỗi trích dẫn tối đa một câu.

## Phương pháp

1. Đọc tay khoảng 60 lượt ngẫu nhiên (seed 7), rồi đọc riêng các lượt K4 thuộc buổi D01/D02 (1.173 lượt không phải câu mẫu) để biết học viên hỏi về khái niệm theo những kiểu nào.
2. Từ đó định nghĩa nhóm bằng regex, chạy trên toàn bộ file. Quy tắc nằm nguyên văn trong [`mine_chatlog.py`](mine_chatlog.py); chạy `python eval/evidence/mine_chatlog.py` ra đúng các số dưới đây.
   - **Xin được giảng**: câu hỏi chứa "giải thích / là gì / nghĩa là gì / hiểu thế nào / không hiểu / chưa hiểu", tính cả câu mẫu.
   - **Tự nói cách hiểu**: học viên nêu cách hiểu của mình kèm ý muốn được kiểm ("tôi hiểu là…", "có phải…", "…đúng không", "tức là…"); không tính câu mẫu.
   - **Đòi đáp án / làm hộ**: "đáp án", "làm hộ/giúp", "giải hộ/giúp", "cho tôi lời giải"…
   - **Hỏi lại cùng đoạn**: cùng học viên, cùng buổi, cùng 80 ký tự đầu của đoạn đã chọn, hỏi từ 2 lần trở lên.
3. Nước đi sư phạm lấy thẳng từ cột `move_used` do hệ thống ghi, không tự suy.

Giới hạn đã biết: regex tiếng Việt bắt thiếu các cách nói khác (ví dụ "theo mình thì…"), nên nhóm "tự nói cách hiểu" là **cận dưới**. Cột `reply_ms` hai kỳ khác nguồn nên không dùng.

## Kết quả

**Tutor gần như chỉ giảng, gần như không hỏi ngược** (cột `move_used`, n = 13.494):

| Nước đi | Lượt | Tỉ lệ |
|---|---|---|
| review_concept (giảng lại khái niệm) | 12.127 | 89,9% |
| give_direct_answer | 731 | 5,4% |
| give_example | 372 | 2,8% |
| give_hint | 39 | 0,3% |
| **ask_probing_question (hỏi ngược)** | **28** | **0,2%** |
| **validate_understanding (kiểm cách hiểu)** | **22** | **0,2%** |

**Các nhóm lượt:**

| Nhóm | Lượt | Học viên | Trong K4 | Rating up/down |
|---|---|---|---|---|
| Xin được giảng | 5.602 (41,5%) | 1.215 | 1.145 lượt · 318 HV | 45/31 |
| Tự nói cách hiểu, muốn được kiểm | 107 (0,8%) | 73 | 38 lượt · 26 HV | 1/0 |
| Đòi đáp án / làm hộ | 57 (0,4%) | 31 | 28 lượt · 20 HV | 0/0 |
| Xin quiz / ôn tập | 274 (2,0%) | 116 | 120 lượt · 31 HV | 2/2 |
| Tutor trả lời không trích dẫn | 3.781 (28,0%) | 933 | 839 lượt · 191 HV | 34/56 |
| Tutor trả lời dài hơn 1.500 ký tự | 2.604 (19,3%) | 543 | 444 lượt · 146 HV | 10/2 |

- **Khi học viên tự nói ra cách hiểu (107 lượt), tutor giảng lại 93 lần (86,9%)** và chỉ kiểm cách hiểu 2 lần. Đúng khoảnh khắc học viên đang chủ động giải thích, hệ thống giành lại vai người giảng.
- **Hỏi lại cùng một đoạn đã chọn**: 145 đoạn, 365 lượt, 83 học viên. Nghe giảng xong vẫn phải hỏi lại đúng chỗ đó.
- **Không đo được hiểu hay chưa**: `understanding_level` có giá trị ở 20/13.494 lượt (0,1%). Rating chỉ có ở 1,3% số lượt, và 85/177 là down.
- **Câu mẫu bấm sẵn** ("giải thích đoạn bôi đen"…) chiếm 22,7%. Cách dùng mặc định là giao việc giải thích cho máy.
- Câu trả lời dài trung vị 1.012 ký tự, trong khi câu hỏi tự gõ trung vị 81 ký tự.

## Ví dụ nguyên văn

| turn_id | Khoá · buổi | Học viên gõ | Tutor chọn |
|---|---|---|---|
| T02871 | K3 · D02 | "bạn hãy hỏi tôi không hiểu chỗ nào được không" | ask_probing_question |
| T02531 | K3 · D11 | "Tôi hiểu là tranformer có cơ chế attention nên khác với các mô hình học máy khác ?" | review_concept |
| T01019 | K3 · D13 | "vậy prompt engineerig có phải là mô tả lại ngữ cảnh của câu để cho AI hiểu rõ hơn không" | review_concept |
| T10975 | K4 · D01 | "hallucination: không bao giờ giải quyết được hết do dự đoán xác suất" | review_concept |
| T10883 | K4 · D01 | "em vẫn chưa hiểu rõ sự khác biệt của agent và llm" | review_concept |
| T10927 | K4 · D01 | "vẫn chưa hiểu MCP lắm" | review_concept |
| T02864 | K3 · D05 | "tôi vẫn không hiểu gì" | review_concept |
| T11543 | K4 · D03 | "đáp án đúng của câu này là gì" | review_concept |

Đọc cùng nhau: học viên có lúc tự xin được hỏi ngược (T02871), có lúc tự nói ra cách hiểu để được kiểm (T02531, T01019, T10975). Phản hồi mặc định vẫn là một đoạn giảng lại. Người vẫn không hiểu thì nhắn cụt (T02864, T10927), và hệ thống giảng thêm một đoạn nữa.
