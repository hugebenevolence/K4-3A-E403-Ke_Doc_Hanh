# Một image cho cả app: backend FastAPI phục vụ luôn giao diện React đã build.
#
#   docker build -t giang-lai codebase
#
# Image KHÔNG chứa slide hay mô tả hình của khoá (data pack không được phát
# tán) — mount lúc chạy, xem "Deploy cho thành viên thử" trong codebase/README.md.

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend-react/package.json frontend-react/package-lock.json ./
RUN npm ci
COPY frontend-react/ ./
RUN npm run build

FROM python:3.14-slim
# Giữ đúng cây thư mục của repo: config.py tính knowledge/ và bản build giao
# diện theo vị trí tương đối từ backend/.
WORKDIR /app/codebase/backend
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    SLIDES_DIR=/data/slides
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist /app/codebase/frontend-react/dist
EXPOSE 8000
# PORT do nền tảng cấp (Render, Railway…); chạy tay thì mặc định 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
