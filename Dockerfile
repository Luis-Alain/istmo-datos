# syntax=docker/dockerfile:1
FROM python:3.12-slim

# uv, fijado a una versión para builds reproducibles
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    ISTMO_RAIZ=/app \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) Dependencias primero: esta capa solo se reconstruye si cambian pyproject.toml o uv.lock
COPY pyproject.toml uv.lock .python-version README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# 2) Código y datos de entrada
COPY src ./src
COPY app ./app
COPY db/schema.sql ./db/schema.sql
COPY data/raw ./data/raw
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# 3) Construir la base de datos al armar la imagen (el contenedor queda autocontenido)
RUN etl

# 4) Usuario sin privilegios
RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
