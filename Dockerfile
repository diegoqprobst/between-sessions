FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY server ./server
COPY fixtures ./fixtures
ENV PORT=8080 DB_PATH=/tmp/between.sqlite
CMD ["uv", "run", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]
