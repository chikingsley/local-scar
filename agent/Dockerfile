# Voice Agent Dockerfile
# Uses NVIDIA CUDA base for GPU-accelerated Parakeet STT
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    curl \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY voice_agent/ voice_agent/
COPY prompts/ prompts/

# Install dependencies with GPU support
RUN uv pip install --system -e .

# Pre-download Parakeet model (optional - can be done at runtime)
# RUN python -c "import onnx_asr; onnx_asr.load_model('nemo-parakeet-tdt-0.6b-v3')"

# Expose ports
EXPOSE 8765 8889

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s \
    CMD curl -f http://localhost:8765/health || exit 1

# Run the bot
CMD ["python", "-m", "voice_agent.bot"]
