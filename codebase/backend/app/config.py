"""Cấu hình. Đổi model là đổi env, không sửa code.

Mặc định để mock bật: clone repo về là chạy được ngay, không cần key, không
tốn credit. Bật provider thật bằng USE_MOCKS=false.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    use_mocks: bool = True

    openai_api_key: str = ""
    speechmatics_api_key: str = ""
    fpt_ai_api_key: str = ""

    # Phân tầng theo chi phí — xem bảng ngân sách trong codebase/README.md.
    model_fast: str = "gpt-5-nano"
    model_standard: str = "gpt-5-mini"
    model_judge: str = "gpt-5"
    model_tts: str = "gpt-4o-mini-tts"  # tts-1 đo được 44s/câu, không dùng được

    # Đo thật trên node chấm: default 5249ms -> priority 1689ms, nhanh gấp 3.1
    # lần chỉ bằng một tham số. Đắt hơn mỗi token nhưng mỗi lượt vẫn ~$0.002,
    # và độ trễ là điểm yếu lớn nhất của sản phẩm. Đặt "default" để tiết kiệm.
    openai_service_tier: str = "priority"

    # Giọng đọc nhanh hơn mặc định: cùng thời gian sinh nhưng rút ~20% thời
    # gian nghe, và học viên đang chờ để tới lượt mình nói.
    tts_speed: float = 1.5

    # Câu đệm lúc chờ chấm. Tắt vì đo được nó chậm hơn chính khoảng nó định
    # lấp — xem ghi chú dài trong api/session.py.
    enable_talker: bool = False

    # Bài thật nằm ngoài repo (data pack không commit được). Khi USE_MOCKS=true
    # thì dùng bài demo tự bịa trong fixtures/ để repo chạy được ngay.
    lesson_file: Path = REPO_ROOT / "knowledge" / "lesson.json"
    # Mô tả hình trên slide, sinh bằng scripts/describe_figures.py.
    figures_file: Path = REPO_ROOT / "knowledge" / "figures.json"
    demo_lesson_file: Path = BACKEND_DIR / "fixtures" / "demo_lesson.json"
    demo_code_lesson_file: Path = BACKEND_DIR / "fixtures" / "demo_code_lesson.json"

    # "slide" hoặc "code" — đổi chế độ bài học mà không sửa dòng code nào.
    lesson_mode: str = "slide"

    # Dạy-lại-CODE tạm ẩn. Đường nói mới là chỗ sản phẩm đứng hay ngã, nên dồn
    # sức vào đó trước; phần code vẫn còn nguyên (fixtures/demo_code_lesson.json,
    # prompts/grader_code/, frontend CodeView.jsx) và bật lại bằng đúng cờ này.
    enable_code_mode: bool = False

    # File slide để frontend render. Nằm ngoài repo vì thuộc data pack.
    slides_pdf: Path | None = None
    # Thư mục chứa nhiều bộ slide (*.pdf) — mỗi file là một bài học chọn được ở
    # trang thư viện. Cả hai cách cấu hình đều nhận; trùng file thì tính một.
    slides_dir: Path | None = None
    # Tên hiển thị cho từng bộ slide: {"<slug>": {"title": ..., "subtitle": ...}}.
    # Thiếu thì lấy tiêu đề trang đầu của bộ slide.
    decks_file: Path = REPO_ROOT / "knowledge" / "decks.json"

    # Đăng nhập cho bản thử nghiệm nội bộ — xem app/api/auth.py.
    # MEMBERS="an:matkhau1,binh:matkhau2". Để trống = tắt đăng nhập (máy cá nhân, test).
    members: str = ""
    # Khoá ký token. Để trống thì sinh ngẫu nhiên mỗi lần khởi động (token cũ mất hiệu lực).
    auth_secret: str = ""

    # Bản build của frontend. Có thư mục này thì backend phục vụ luôn giao diện,
    # deploy chỉ cần MỘT service — không phải lo CORS hay hai tên miền.
    frontend_dist: Path = REPO_ROOT / "codebase" / "frontend-react" / "dist"
    session_log_file: Path = BACKEND_DIR / "var" / "sessions.jsonl"
    pronunciation_file: Path = BACKEND_DIR / "var" / "sounds_like.json"

    # Sinh cách đọc kiểu Việt cho thuật ngữ bằng LLM. TẮT vì đo được nó làm TỆ
    # đi: 8 đoạn giọng đọc tiếng Anh kiểu Việt, từ điển theo vùng + cụm từ ra
    # đúng 19/20 thuật ngữ, thêm cách đọc sinh tự động còn 15/20 ("reward model"
    # quay về "report model" ở cả hai giọng). Đo bằng giọng tổng hợp nên chưa
    # phải lời cuối — bật lại để thử khi có bản ghi giọng người thật.
    enable_generated_pronunciations: bool = False
    profile_file: Path = BACKEND_DIR / "var" / "profiles.json"
    checkpoint_db: Path = BACKEND_DIR / "var" / "checkpoints.sqlite"


settings = Settings()
