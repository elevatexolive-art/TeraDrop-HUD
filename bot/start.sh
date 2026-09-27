#!/bin/sh
# Locate Python in Nixpacks/Railpack/Docker images and start the bot.
cd "$(dirname "$0")" || exit 1
for bin in python3 python python3.12; do
  if command -v "$bin" >/dev/null 2>&1; then
    exec "$bin" -m app
  fi
done
echo "python is not installed in this container. Railway must build Dockerfile.railway (see railway.json)." >&2
exit 127
