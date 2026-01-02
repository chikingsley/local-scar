# Voice Agent Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY voice_agent/ voice_agent/
COPY prompts/ prompts/

# Install dependencies
RUN uv pip install --system -e .

# Expose ports
EXPOSE 8765 8889

# Run the bot
CMD ["python", "-m", "voice_agent.bot"]
