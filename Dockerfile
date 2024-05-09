FROM onerahmet/openai-whisper-asr-webservice
RUN /app/.venv/bin/pip3 install librosa webrtcvad-wheels
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends \
    certbot \
    && rm -rf /var/lib/apt/lists/*
COPY ./app /app/app
EXPOSE 9000
CMD /app/.venv/bin/python -m gunicorn --bind 0.0.0.0:9000 --workers 1 --timeout 0 app.webservice:app -k uvicorn.workers.UvicornWorker
