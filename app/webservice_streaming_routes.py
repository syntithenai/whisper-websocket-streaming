import importlib.metadata
import os
import random
import io
import time
import sys
import json
from os import path
import asyncio
import tempfile
import librosa
import soundfile
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from multiprocessing import Process
import concurrent.futures
import multiprocessing

from whisper import tokenizer
from typing import Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import SAMPLING_RATE,LANG
from audio_utils import *
from faster_whisper_core import transcribe
# import torch
# torch.set_num_threads(1)
from vad import VadDetector
# from gpt4all import GPT4All

from typing import Annotated, Union

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Query,
    WebSocket,
    WebSocketException,
    status,
)
from fastapi.responses import HTMLResponse

print('WHISPER KEY',os.environ.get('OPENAI_WHISPER_API_KEY',''))

if os.environ.get('OPENAI_WHISPER_API_KEY',''):
	from openai import OpenAI
	openai_client = OpenAI(api_key=os.environ.get('OPENAI_WHISPER_API_KEY',''))


def add_streaming_routes(app):
	
	# STT
	@app.websocket("/stt")
	async def websocket_endpoint(websocket: WebSocket, clientId: Optional[int] = None):
		
		try:
			audio_buffer = asyncio.Queue()
			
			async def vad_callback():
				now = time.time()
				# print(f"VAD CALLBACK {now}")
				try:
					await websocket_send_json({"vad_timeout" : True, "time": now})
					await transcribe_buffer(audio_buffer)
				except Exception as e:
					print(e)
					await websocket_send_json({"error": str(e)})

			vad = VadDetector(vad_callback)

			async def websocket_send_json(jsondata):
				try:
					await websocket.send_text(json.dumps(jsondata)) 
					# reset queue
				except Exception as e:
					print("WS send failed?")
					print(e)
			
			async def transcribe_buffer(audio_buffer):	
				s = time.time()
				with tempfile.NamedTemporaryFile(suffix=".wav") as output_file:
					print(output_file)
					print(output_file.name)
					await write_queue_to_audio_file(output_file.name,audio_buffer, True)
					if os.environ.get('OPENAI_WHISPER_API_KEY',''):
						print("USE WHISPER ASR")
						transcription = openai_client.audio.transcriptions.create(model="whisper-1", file=io.FileIO(output_file.name), response_format="text")
						if transcription:
							await websocket_send_json({"transcription": transcription})
							print("api transcript",transcription)
					else:
						o = transcribe(load_audio(io.FileIO(output_file.name), False), 'transcribe', "en", "", False, True, "json")	
						t = json.loads(o.read()).get('text')
						n = time.time() - s
						#print(f"transcript in %s" % n,t)
						if t:
							await websocket_send_json({"transcription": t})
					audio_buffer = asyncio.Queue()
					
			await websocket.accept()
				
			# loop until websocket dies
			while True:
				# loop until None message or timeout then reset audio buffer and vad
				while True:
					try:
						msg = await asyncio.wait_for(websocket.receive(), timeout=3)
						await asyncio.sleep(0)  # Yield to event loop for timeout handling
						# null message from client triggers transcript
						if msg is None:
							print("MSG NONE")
							await transcribe_buffer(audio_buffer)
							break
						data_bytes = msg.get('bytes')
						if data_bytes is None:
							print("MSG bytes NONE")
							await transcribe_buffer(audio_buffer)
							break
						print(data_bytes[0:10])
						sf = soundfile.SoundFile(io.BytesIO(data_bytes), channels=1,endian="LITTLE",samplerate=SAMPLING_RATE, subtype="PCM_16",format="RAW")
						audio, _ = librosa.load(sf,sr=SAMPLING_RATE,dtype=np.float32)
						await audio_buffer.put(audio)
						await vad.feed(data_bytes)
					except asyncio.TimeoutError:
						break
					except RuntimeError:
						break;
				# reset buffers when loop breaks after None message
				audio_buffer = asyncio.Queue()
				vad = VadDetector(vad_callback)
				
			
		except WebSocketDisconnect:
			print('CLOSE WS CONNECT CLIENT')
			pass
			
		

