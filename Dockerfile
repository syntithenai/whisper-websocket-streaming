FROM onerahmet/openai-whisper-asr-webservice
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends \
    certbot \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install librosa webrtcvad-wheels python-dotenv gunicorn
RUN pip3 install uvicorn fastapi openai-whisper faster-whisper
COPY ./app /app/app
EXPOSE 9000
ENV LD_LIBRARY_PATH /usr/local/lib/python3.10/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib
RUN apt-get -qq update && apt-get -qq install ffmpeg
RUN pip3 install ffmpeg-python 
CMD python3 -m gunicorn --bind 0.0.0.0:9000 --workers 1 --timeout 0 app.webservice:app -k uvicorn.workers.UvicornWorker
