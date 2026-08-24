FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DENO_INSTALL=/root/.deno \
    DENO_PATH=/root/.deno/bin/deno \
    PATH="/root/.deno/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# YouTube now needs a supported JavaScript runtime for full yt-dlp support.
# Deno is the recommended runtime.
RUN curl -fsSL https://deno.land/install.sh | sh \
    && /root/.deno/bin/deno --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "import yt_dlp, yt_dlp_ejs; print('yt-dlp:', yt_dlp.version.__version__); print('yt-dlp-ejs: OK')"

COPY . .

EXPOSE 8080
CMD ["python", "main.py"]
