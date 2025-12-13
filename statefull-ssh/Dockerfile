FROM python:3.14-alpine3.23

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:/root/.local/bin:${PATH}" \
    PYTHONPATH=/app/src

RUN apk add --no-cache \
    bash \
    curl \
    build-base \
    libffi-dev \
    openssl-dev \
    cargo

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["tail", "-f", "/dev/null"]
