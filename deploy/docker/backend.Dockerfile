FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y \
        --no-install-recommends \
        python3 \
        python3-venv \
        python3-libvirt \
        qemu-utils \
        iproute2 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY backend/requirements.txt /tmp/requirements.txt

RUN python3 -m venv \
        --system-site-packages \
        /opt/venv \
    && /opt/venv/bin/pip install \
        --no-cache-dir \
        -r /tmp/requirements.txt

COPY backend/ /workspace/backend/

WORKDIR /workspace/backend

ENV PYTHONPATH=/workspace/backend
ENV HOME=/tmp

CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
