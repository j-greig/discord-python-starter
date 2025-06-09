# https://pythonspeed.com/articles/base-image-python-docker-images/
# https://testdriven.io/blog/docker-best-practices/
FROM python:3.11-slim-bullseye

COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv

# Set Working directory
WORKDIR /app

# Install git (needed for honcho-ai dependency from GitHub)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /app
USER app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy only requirements to cache them in docker layer
COPY uv.lock pyproject.toml /app/

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=app:app src/ /app/src/

# Copy configuration files (optional - uncomment if files exist)
#COPY --chown=app:app prompt_scramble.md /app/
COPY --chown=app:app prompt_scramble_simple.md /app/
# COPY --chown=app:app base_context.json /app/
# COPY --chown=app:app system_prompt.txt /app/

# Create logs directory for enthusiasm scoring
RUN mkdir -p /app/logs/enthusiasm && chown -R app:app /app/logs


CMD ["python", "-u", "src/bot.py"]
