#!/bin/sh
/app/.venv/bin/python /app/whisper-websocket-streamer/generate_ssl_certificates.py

exec "$@"
