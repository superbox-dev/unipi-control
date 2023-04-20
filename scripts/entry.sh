#!/bin/sh

set -e

BUILD=/build
VENV=/opt/.venv
USER="root"

if [ "${BUILDER_UID:-0}" -ne 0 ] && [ "${BUILDER_GID:-0}" -ne 0 ]; then
  getent group "${BUILDER_GID}" > /dev/null || groupadd -g "${BUILDER_GID}" builder
  getent passwd "${BUILDER_UID}" > /dev/null || useradd -m -u "${BUILDER_UID}" -g "${BUILDER_GID}" builder
  echo "builder ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers
  chown "${BUILDER_UID}:${BUILDER_GID}" /build || true
  USER="builder"
fi

python -m venv --system-site-packages "${VENV}"
. "${VENV}/bin/activate"
pip install --no-cache-dir -e .

sudo -H -u ${USER} python -m nuitka \
    --standalone \
    --output-filename="$1" \
    --output-dir="${BUILD}/output" \
    "${VENV}/bin/$1"

