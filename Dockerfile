FROM python:3.10-alpine

# Update packages
RUN apk update && apk upgrade
RUN apk add --no-cache gcc ccache musl-dev patchelf linux-headers shadow sudo

# Install dev packages
RUN pip install --no-cache-dir nuitka

WORKDIR /build
