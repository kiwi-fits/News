FROM python:3.11-slim

# Install system dependencies: FFmpeg, Tamil fonts, fontconfig, and ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto-core \
    fonts-noto-extra \
    fontconfig \
    ca-certificates \
    curl \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Set up user according to Hugging Face guidelines (UID 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR $HOME/app

# Copy dependency definition and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=user . $HOME/app

# Ensure generated directory exists with correct permissions
RUN mkdir -p $HOME/app/generated && chown -R user:user $HOME/app

USER user

EXPOSE 7860

CMD ["python", "app.py"]
