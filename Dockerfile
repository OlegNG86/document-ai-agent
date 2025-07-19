# Dockerfile for AI Agent
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_CACHE_DIR=/opt/poetry/.cache

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry install --only=main --no-root

# Copy application code
COPY ai_agent/ ./ai_agent/

# Create data directories
RUN mkdir -p data/documents data/chroma_db

# Set environment variables
ENV PYTHONPATH=/app
ENV DATA_PATH=/app/data
ENV DOCUMENTS_PATH=/app/data/documents
ENV CHROMA_PATH=/app/data/chroma_db
ENV OLLAMA_HOST=http://localhost:11434

# Expose port (if needed for future web interface)
EXPOSE 8000

# Default command (can be overridden by docker-compose)
CMD ["poetry", "run", "python", "-m", "ai_agent.main", "--help"]