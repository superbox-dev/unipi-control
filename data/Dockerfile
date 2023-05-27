FROM python:3.10-slim

# Update packages
RUN apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
      git \
      gcc \
      ccache \
      sudo \
      libc6-dev \
      patchelf \
    && rm -rf /var/lib/apt/lists/*

# Install dev packages
RUN pip install --no-cache-dir nuitka

WORKDIR /build
