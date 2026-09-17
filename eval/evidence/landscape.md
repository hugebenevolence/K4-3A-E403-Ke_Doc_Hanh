# Định vị — "Giảng lại" đứng ở đâu so với các công cụ học bằng AI

Mục đích: tìm điểm mạnh **thật** của sản phẩm, tức những chỗ đối thủ không làm hoặc làm theo cách yếu hơn, và mỗi điểm phải có căn cứ nghiên cứu hoặc số đo. Kèm các điểm yếu đã biết. Nguồn ở cuối file; những gì chưa kiểm chứng được ghi rõ.

## 1. Sáu trục so sánh

Sáu trục này được chọn vì đổi giá trị trên trục nào cũng đổi cách học viên học:

1. **Ai là người giải thích**: AI giải thích hay học viên giải thích?
2. **Đối chiếu với cái gì**: kiến thức chung của mô hình, hay đúng đoạn tài liệu khoá học?
3. **Nguồn có bị che khi học viên trả lời không**: che thì học viên phải nhớ lại (thực hành gợi nhớ), không che thì học viên đọc lại.
4. **"Không làm hộ" giữ bằng gì**: bằng lời dặn trong prompt và tắt được, hay bằng kiểm tra trong code và không có đường vòng?
5. **Nằm ở đâu**: một app riêng, hay ngay trong trình đọc bài đang học?
6. **Kênh**: gõ chữ hay nói.

| Sản phẩm | ① Ai giải thích | ② Đối chiếu | ③ Che nguồn | ④ Giữ "không làm hộ" | ⑤ Ở đâu | ⑥ Kênh |
|---|---|---|---|---|---|---|
| Tutor VLearn hiện tại (chatlog) | AI (giảng lại 89,9% lượt) | Tài liệu khoá, 28% lượt không trích dẫn | Không | Không có | Trong trình đọc slide | Gõ |
| ChatGPT — Study mode (29/7/2025) | AI hỏi gợi mở, rồi vẫn giải thích | Kiến thức chung | Không | Chế độ bật tắt; chuyển về chế độ thường là có đáp án, không khoá được | App riêng | Gõ / nói |
| Gemini — Guided Learning (6/8/2025) | AI chia nhỏ bài, hỏi mở, kèm hình và quiz | Kiến thức chung (LearnLM) | Không | Chế độ bật tắt | App riêng | Gõ |
| Claude — Learning mode (2/4/2025) | AI hỏi kiểu Socrates thay vì đưa lời giải | Kiến thức chung | Không | Chế độ bật tắt | App riêng | Gõ |
| Khanmigo (Khan Academy) | AI dẫn dắt từng bước | Bài tập của Khan Academy | Không | Chính sách sản phẩm | Trong nền tảng Khan | Gõ |
| NotebookLM | AI tóm tắt, trả lời, làm Audio Overview | **Đúng tài liệu tải lên, có trích dẫn** | Không (trích nguyên văn cạnh câu trả lời) | Không nhắm tới | App riêng | Gõ / nghe |
| Duolingo Max — Video Call | Học viên nói, AI đóng vai người đối thoại | Bài học ngôn ngữ | Không áp dụng | Không áp dụng | Trong app Duolingo | **Nói** |
| Betty's Brain (Vanderbilt) | **Học viên dạy** agent bằng bản đồ khái niệm | Mô hình chuẩn của giáo viên | Có (agent làm quiz) | Luật cố định | Phần mềm riêng | Kéo thả |
| TeachYou / AlgoBo (CHI 2024) | **Học viên dạy** agent LLM | Đề thuật toán | Không | Pipeline giới hạn kiến thức của agent | Nghiên cứu | Gõ |
| **Giảng lại (của nhóm)** | **Học viên giảng**, AI là học trò chỉ hỏi ngược | **Đúng vùng slide học viên chọn** | **Có, từng ô, bật tắt được** | **Guard trong code**: đọc nguyên văn, lộ đáp án, xác nhận ý sai; không có chế độ nào đưa đáp án | **Ngay trong trình đọc slide** | **Nói** (gõ dự phòng) |

Đọc bảng: ba chế độ học của OpenAI, Google, Anthropic đều đi cùng một hướng là **AI hỏi nhiều hơn trước khi giải thích**, nhưng AI vẫn giữ vai người dạy. Chúng không bám tài liệu khoá, không che nguồn, và tắt được. NotebookLM bám tài liệu rất chắc nhưng làm học viên thụ động hơn. Các hệ học-bằng-cách-dạy (Betty's Brain, TeachYou) đúng vai nhưng là phần mềm riêng, không nằm ở chỗ học viên đang học, và không dùng giọng nói.

"Giảng lại" là tổ hợp duy nhất trong bảng có cùng lúc: **học viên giảng · đối chiếu đúng đoạn tài liệu · nguồn bị che · chặn làm hộ bằng code · ngay trong trình đọc bài · bằng giọng nói**.

## 2. Điểm mạnh, mỗi điểm một căn cứ

**S1 — Đảo vai: học viên tạo ra lời giải thích, không chỉ đọc lời giải thích.**
- *Self-explanation effect*: học viên được yêu cầu tự giải thích hiểu sâu hơn (Chi và cộng sự, 1994).
- Phân tích lời người dạy: người dạy học được nhiều nhất khi xây kiến thức (giải thích lại, trả lời câu hỏi sâu) chứ không chỉ kể lại (Roscoe & Chi, 2007).
- Teachable agent: học viên cố gắng hơn khi dạy agent so với khi học cho mình (Chase và cộng sự, 2009).
- TeachYou: khi agent chủ động hỏi "vì sao, như thế nào", hội thoại dày ý kiến thức hơn, hiệu ứng 0,71 trên 40 người học (Jin và cộng sự, 2024).
- → Sản phẩm: học trò AI chỉ nhắc lại ý đã nghe và hỏi đúng **một** câu "vì sao/như thế nào" ở chỗ hổng.

**S2 — Che nguồn biến việc đọc lại thành thực hành gợi nhớ.**
- Phải nhớ lại để trả lời giúp nhớ lâu hơn đọc lại (Roediger & Karpicke, 2006).
- Hiệu ứng này lặp lại được, theo tổng hợp nhiều nghiên cứu (Rowland, 2014).
- → Sản phẩm: vùng đang giảng bị che; bấm từng ô để xem, bấm lại để che. Đối thủ trong bảng đều để nguồn mở, hoặc trích nguyên văn ngay cạnh câu trả lời.

**S3 — Lộ ra đúng chỗ "tưởng mình hiểu".**
- Người ta đánh giá quá cao mức mình hiểu một cơ chế, cho tới khi phải giải thích từng bước (Rozenblit & Keil, 2002).
- → Sản phẩm: giảng xong, "Mình hiểu là…" cho thấy ý nào đã tới, câu hỏi ngược cho thấy ý nào chưa tới. Chatlog cho thấy khoảnh khắc này đang bị bỏ lỡ: 107 lượt học viên tự nói ra cách hiểu, tutor giảng lại 93 lượt (`mining.md`).

**S4 — "Không làm hộ" được giữ bằng code, và không có đường vòng.**
- Thực nghiệm gần 1.000 học sinh (Bastani và cộng sự, PNAS 2025):
  - được dùng GPT-4 lúc luyện tập thì điểm bài luyện tăng (+48% với giao diện ChatGPT thường);
  - nhưng khi bỏ AI đi, nhóm này làm bài **kém hơn** nhóm chưa từng dùng (−17%);
  - bản có rào chắn sư phạm ("GPT Tutor") gần như triệt tiêu tác hại đó.
- ChatGPT Study mode chuyển về chế độ thường là có đáp án, và OpenAI nói rõ không có công cụ khoá học sinh ở Study mode (TechCrunch, 29/7/2025).
- → Sản phẩm: guard tất định chặn đọc nguyên văn, lộ đáp án, câu kiểu "có phải là…" xác nhận ý sai. Không tồn tại chế độ "cho đáp án". Kể cả khi học viên xin thẳng hay chèn prompt injection (case O01, O02).

**S5 — Đối chiếu với đúng đoạn tài liệu học viên đang giảng, không với hiểu biết chung.**
- Trợ lý đa năng trả lời theo kiến thức chung, có thể lệch với cách giảng viên dạy. Tutor hiện tại không trích dẫn ở 28% lượt (`mining.md`).
- → Sản phẩm: bài học dựng từ đúng các ô học viên kéo chọn, kể cả sơ đồ (có mô tả hình). Khi hết lượt, thẻ nguồn chỉ **vị trí** cần xem lại, không trích nguyên văn.

**S6 — Nằm đúng chỗ nhu cầu xảy ra.**
- 41,5% lượt trong chatlog là xin được giảng, ngay trong trình đọc slide (`mining.md`).
- → Sản phẩm: thay nút "giải thích đoạn bôi đen" bằng "giảng lại đoạn này", cùng chỗ, cùng thao tác chọn vùng. Học viên không phải mở app khác và dán lại ngữ cảnh.
- Thiết kế sư phạm quyết định kết quả: gia sư AI dựng theo cùng nguyên tắc sư phạm với lớp học chủ động giúp sinh viên học được nhiều hơn trong ít thời gian hơn (Kestin và cộng sự, Scientific Reports 2025, RCT).

**S7 — Giảng bằng lời nói.**
- Dạy lại ngoài đời là nói, không phải gõ. Chưa có nghiên cứu nào nhóm kiểm chứng được so sánh riêng nói và gõ trong học-bằng-cách-dạy, nên đây là **giả thuyết thiết kế**, cần đo ở vòng validation.
- → Sản phẩm: nhận dạng realtime có từ điển thuật ngữ theo vùng đang giảng (nhận đúng 11/20 → 19/20 câu có thuật ngữ).

**S8 — Tạo ra tín hiệu "đã hiểu" mà hệ thống hiện tại không có.**
- `understanding_level` chỉ có ở 0,1% lượt trong chatlog. Mỗi vùng giảng xong có nhãn đủ / thiếu / sai và danh sách ý đã tới, thành tiến độ theo trang slide.

## 3. Điểm yếu và rủi ro đã biết

| Rủi ro | Mức | Đang xử lý |
|---|---|---|
| Bộ chấm LLM dễ cho "đủ" khi học viên nói toàn từ khoá hoặc đọc slide lộn xộn | Cao, đánh thẳng vào S3 | Guard đọc nguyên văn; case A01, A02 trong golden set; siết prompt chấm sau lượt đo 1 |
| Nhận dạng giọng nói tiếng Việt trộn thuật ngữ tiếng Anh | Trung bình | Từ điển theo vùng; chữ nhận dạng hiện ngay để học viên sửa; gõ dự phòng |
| Độ trễ vài giây mỗi lượt | Trung bình | Chỉ báo tiến trình; service tier nhanh |
| Học viên có động lực thấp chỉ muốn đáp án | Trung bình | TechCrunch nhận xét Study mode chỉ có tác dụng với học sinh "thật sự muốn học", và OpenAI xác nhận không có cách khoá học sinh ở chế độ này. Sản phẩm nằm trong luồng học của khoá chứ không phải app phải tự tìm tới, nhưng chưa đo được tỉ lệ dùng |
| Chưa có bằng chứng hiệu quả học của chính sản phẩm | Cao | Vòng validation ≥5 người; chưa đủ thời gian cho đo trước/sau |
| Chỉ đối chiếu slide, chưa dùng transcript bài giảng | Thấp | Ngoài lát cắt hiện tại |

Một cảnh báo liên quan, **chưa bình duyệt**: preprint "Your Brain on ChatGPT" (Kosmyna và cộng sự, 2025; 54 người, EEG) thấy nhóm viết bằng LLM có kết nối não yếu nhất và nhớ kém nội dung chính mình viết. Chỉ dùng làm bối cảnh, không làm căn cứ chính.

## Nguồn

Đã kiểm chứng trực tiếp:
- Bastani H., Bastani O., Sungu A. et al. (2025). *Generative AI without guardrails can harm learning: Evidence from high school mathematics.* PNAS 122(26). https://doi.org/10.1073/pnas.2422633122 (qua PubMed)
- Kestin G., Miller K., Klales A., Milbourne T., Ponti G. (2025). *AI tutoring outperforms in-class active learning: an RCT introducing a novel research-based design in an authentic educational setting.* Scientific Reports 15, 17458. https://doi.org/10.1038/s41598-025-97652-6 (qua PubMed)
- Jin H., Lee S., Shin H., Kim J. (2024). *Teach AI How to Code: Using Large Language Models as Teachable Agents for Programming Education.* CHI 2024. https://arxiv.org/abs/2309.14534
- Kosmyna N. et al. (2025). *Your Brain on ChatGPT: Accumulation of Cognitive Debt when Using an AI Assistant for Essay Writing Task.* Preprint. https://arxiv.org/abs/2506.08872
- Anthropic (2/4/2025). *Introducing Claude for Education* (Learning mode). https://www.anthropic.com/news/introducing-claude-for-education
- Google (6/8/2025). *Guided Learning in Gemini.* https://blog.google/outreach-initiatives/education/guided-learning/
- TechCrunch (29/7/2025). *OpenAI launches Study Mode in ChatGPT.* https://techcrunch.com/2025/07/29/openai-launches-study-mode-in-chatgpt/

Nghiên cứu nền kinh điển (trích theo tài liệu gốc, không mở lại được trong phiên này):
- Chi M.T.H., de Leeuw N., Chiu M.-H., LaVancher C. (1994). Eliciting self-explanations improves understanding. *Cognitive Science*, 18(3).
- Roscoe R.D., Chi M.T.H. (2007). Understanding tutor learning: Knowledge-building and knowledge-telling in peer tutors' explanations and questions. *Review of Educational Research*, 77(4).
- Chase C.C., Chin D.B., Oppezzo M.A., Schwartz D.L. (2009). Teachable agents and the protégé effect. *Journal of Science Education and Technology*, 18(4).
- Biswas G., Leelawong K., Schwartz D., Vye N. (2005). Learning by teaching: A new agent paradigm for educational software. *Applied Artificial Intelligence*, 19(3–4).
- Roediger H.L., Karpicke M.C. (2006). Test-enhanced learning. *Psychological Science*, 17(3).
- Rowland C.A. (2014). The effect of testing versus restudy on retention: A meta-analytic review. *Psychological Bulletin*, 140(6).
- Rozenblit L., Keil F. (2002). The misunderstood limits of folk science: an illusion of explanatory depth. *Cognitive Science*, 26(5).

Đặc điểm sản phẩm Khanmigo, NotebookLM, Duolingo Video Call trong bảng §1 dựa trên mô tả công khai của các sản phẩm này, chưa mở lại trang gốc trong phiên này. Nên có người trong nhóm dùng thử và xác nhận trước khi trình bày.
