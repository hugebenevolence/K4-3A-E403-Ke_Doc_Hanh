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

    knowledge_file: Path = REPO_ROOT / "knowledge" / "spans.json"
    session_log_file: Path = BACKEND_DIR / "var" / "sessions.jsonl"
    profile_file: Path = BACKEND_DIR / "var" / "profiles.json"
    checkpoint_db: Path = BACKEND_DIR / "var" / "checkpoints.sqlite"


settings = Settings()
