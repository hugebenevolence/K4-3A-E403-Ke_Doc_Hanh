"""Đặt biến môi trường trên Railway từ codebase/backend/.env.

    cd deploy                                  # thư mục đã `railway link`/`init`
    python ../codebase/scripts/dat_bien_railway.py

Giá trị đi qua STDIN (`railway variables set KEY --stdin`), không nằm trên dòng
lệnh: dán khoá vào dòng lệnh là nó vào lịch sử shell, vào log của terminal, và
vào ảnh chụp màn hình khi demo. Script cũng chỉ in TÊN biến, không in giá trị.

Không đặt USE_MOCKS và SLIDES_DIR: hai biến đó đã nằm trong image
(scripts/Dockerfile.deploy), khai lại ở đây chỉ tạo thêm chỗ để lệch nhau.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / "backend" / ".env"

# Thiếu một trong hai khoá đầu là server chạy được nhưng mọi phiên đều hỏng;
# thiếu MEMBERS là ai có link cũng dùng được, mà mỗi phiên tốn credit thật.
BAT_BUOC = ("OPENAI_API_KEY", "SPEECHMATICS_API_KEY", "MEMBERS", "AUTH_SECRET")
TUY_CHON = ("OPENAI_SERVICE_TIER", "TTS_SPEED", "MODEL_FAST", "MODEL_STANDARD")


def doc_env() -> dict[str, str]:
    gia_tri: dict[str, str] = {}
    for dong in ENV.read_text(encoding="utf-8").splitlines():
        if dong.strip() and not dong.lstrip().startswith("#") and "=" in dong:
            khoa, _, gia = dong.partition("=")
            gia_tri[khoa.strip()] = gia.strip().strip('"').strip("'")
    return gia_tri


def main() -> int:
    if not ENV.is_file():
        print(f"Không thấy {ENV}")
        return 1
    env = doc_env()

    thieu = [k for k in BAT_BUOC if not env.get(k)]
    if thieu:
        print("Thiếu trong .env:", ", ".join(thieu))
        return 1

    for khoa in (*BAT_BUOC, *TUY_CHON):
        if not env.get(khoa):
            continue
        ket_qua = subprocess.run(
            ["npx", "--yes", "@railway/cli", "variables", "set", khoa,
             "--stdin", "--skip-deploys"],
            input=env[khoa], text=True, capture_output=True, shell=True, check=False,
        )
        xong = "đặt xong" if ket_qua.returncode == 0 else f"HỎNG: {ket_qua.stderr.strip()[:120]}"
        print(f"  {khoa:24} {xong}")

    print("\nBiến đã đặt với --skip-deploys, lần `railway up` tới sẽ dùng chúng.")
    print("Nhớ gắn volume trước khi có người dùng thật:")
    print("  npx @railway/cli volume add --mount-path /app/codebase/backend/var")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
