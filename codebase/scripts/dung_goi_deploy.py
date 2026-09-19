"""Dựng thư mục để đẩy lên Railway (hoặc host Docker bất kỳ).

    python codebase/scripts/dung_goi_deploy.py            # dựng vào deploy/
    python codebase/scripts/dung_goi_deploy.py --ra D:/x  # dựng vào chỗ khác

Vì sao cần: slide của khoá và mô tả hình nằm ngoài git (luật data pack), nên
host build từ repo sẽ không có dữ liệu. Railway build từ THƯ MỤC ĐƯỢC ĐẨY LÊN,
nên gói này gom đúng những gì cần chạy — và chỉ những thứ đó.

CHỈ chép slide (brief/data/course-slides/*.pdf). Không chép chatlog, không chép
discord-pack, studio-pack hay vlearn-pack: máy chủ không cần chúng để chạy, mà
data pack thì dùng ở mức tối thiểu cần thiết.

Gói dựng ra KHÔNG chứa .env: khoá API đặt bằng biến môi trường trên nền tảng,
không nằm trong image.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent.parent
SLIDE = GOC / "brief" / "data" / "course-slides"

# Thư mục con không bao giờ cần trên máy chủ: môi trường ảo, gói npm, bản build
# cũ, dữ liệu phiên của máy đang chạy, cache.
BO_QUA = {
    ".venv", "node_modules", "dist", "var", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".vite", "htmlcov",
}

# Không bao giờ vào image. `.env` nằm ngay trong codebase/backend và chứa khoá
# API thật — chép vào là khoá đi theo image lên nền tảng, và ai kéo được image
# là có khoá. Khoá đặt bằng biến môi trường trên nền tảng, không nằm trong file.
KHONG_CHEP = {".env", ".env.local", ".env.production"}


def chep_cay(nguon: Path, dich: Path) -> int:
    """Chép một cây thư mục, bỏ những thứ trong BO_QUA. Trả về số file đã chép."""
    dem = 0
    for duong in nguon.rglob("*"):
        if any(phan in BO_QUA for phan in duong.relative_to(nguon).parts):
            continue
        if duong.is_dir() or duong.name in KHONG_CHEP:
            continue
        ra = dich / duong.relative_to(nguon)
        ra.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(duong, ra)
        dem += 1
    return dem


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ra", type=Path, default=GOC / "deploy")
    args = ap.parse_args()

    if not SLIDE.is_dir():
        print(f"Không thấy slide ở {SLIDE} — cần data pack của khoá.")
        return 1

    ra = args.ra
    if ra.exists():
        shutil.rmtree(ra)
    (ra / "slides").mkdir(parents=True)

    n_code = chep_cay(GOC / "codebase", ra / "codebase")
    n_kho = chep_cay(GOC / "knowledge", ra / "knowledge")
    n_slide = 0
    for pdf in sorted(SLIDE.glob("*.pdf")):
        shutil.copy2(pdf, ra / "slides" / pdf.name)
        n_slide += 1

    shutil.copy2(Path(__file__).with_name("Dockerfile.deploy"), ra / "Dockerfile")
    (ra / ".dockerignore").write_text(
        "**/.venv\n**/node_modules\n**/__pycache__\n**/var\n", encoding="utf-8"
    )

    mb = sum(f.stat().st_size for f in ra.rglob("*") if f.is_file()) / 1e6
    print(f"Gói ở {ra}")
    print(f"  code {n_code} file · knowledge {n_kho} file · slide {n_slide} bộ · tổng {mb:.0f} MB")
    print("\nTiếp theo:")
    print("  cd", ra)
    print("  npx @railway/cli login")
    print("  npx @railway/cli init      # đặt tên project")
    print("  npx @railway/cli up        # đẩy lên, Railway tự build Dockerfile")
    print("\nRồi đặt biến môi trường trên Railway (xem codebase/README.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
