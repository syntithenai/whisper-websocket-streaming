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
from fastapi import FastAPI,File, WebSocket, WebSocketDisconnect, UploadFile, Query, applications
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse
from multiprocessing import Process
import concurrent.futures
import multiprocessing
# from profile import profile 
from whisper import tokenizer
from typing import Optional
LANGUAGE_CODES = sorted(list(tokenizer.LANGUAGES.keys()))
ASR_ENGINE = os.getenv("ASR_ENGINE", "openai_whisper")
if ASR_ENGINE == "faster_whisper":
    from faster_whisper.core import transcribe, language_detection
# else:
    # from openai_whisper.core import transcribe, language_detection
from urllib.parse import quote

SAMPLE_RATE = 16000
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

print('WHISPE1R KEY',os.environ.get('OPENAI_WHISPER_API_KEY',''))

if os.environ.get('OPENAI_WHISPER_API_KEY',''):
	from openai import OpenAI
	openai_client = OpenAI(api_key=os.environ.get('OPENAI_WHISPER_API_KEY',''))


def add_streaming_routes(app):
	
	
	@app.post("/asr", tags=["Endpoints"])
	async def asr(
			audio_file: UploadFile = File(...),
			encode: bool = Query(default=True, description="Encode audio first through ffmpeg"),
			task: Union[str, None] = Query(default="transcribe", enum=["transcribe", "translate"]),
			language: Union[str, None] = Query(default=None, enum=LANGUAGE_CODES),
			initial_prompt: Union[str, None] = Query(default=None),
			vad_filter: Annotated[bool | None, Query(
					description="Enable the voice activity detection (VAD) to filter out parts of the audio without speech",
					include_in_schema=(True if ASR_ENGINE == "faster_whisper" else False)
				)] = False,
			word_timestamps: bool = Query(default=False, description="Word level timestamps"),
			output: Union[str, None] = Query(default="txt", enum=["txt", "vtt", "srt", "tsv", "json"])
	):
		print("START TRANSCRIBE")
		result = transcribe(load_audio(audio_file.file, encode), task, language, initial_prompt, vad_filter, word_timestamps, output)
		print("DONE TRANSCRIBE",result.getvalue())
		return StreamingResponse(
		result,
		media_type="text/plain",
		headers={
			'Asr-Engine': ASR_ENGINE,
			'Content-Disposition': f'attachment; filename="{quote(audio_file.filename)}.{output}"'
		}
	)
	
	# STT
	@app.websocket("/stt")
	async def websocket_endpoint(websocket: WebSocket, clientId: Optional[int] = None):
		print("AAAddff local transcribe ")
		# try:
		audio_buffer = asyncio.Queue()
		
		# async def vad_callback():
			# now = time.time()
			# # print(f"VAD CALLBACK {now}")
			# try:
				# await websocket_send_json({"vad_timeout" : True, "time": now})
				# await transcribe_buffer(audio_buffer)
			# except Exception as e:
				# print(e)
				# await websocket_send_json({"error": str(e)})

		# vad = VadDetector(vad_callback)

		async def websocket_send_json(jsondata):
			try:
				await websocket.send_text(json.dumps(jsondata)) 
				# reset queue
			except Exception as e:
				print("WS send failed?")
				print(e)
		
		async def transcribe_buffer(audio_buffer):	
			print("TTT local transcribe ")
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
					print("local transcribe ")
					o = transcribe(load_audio(io.FileIO(output_file.name), False), 'transcribe', "en", "", False, True, "json")	
					print("local transcribe ",o)
					t = json.loads(o.read()).get('text')
					n = time.time() - s
					print(f"transcript in %s" % n,t)
					if t:
						await websocket_send_json({"transcription": t})
				del audio_buffer
				audio_buffer = asyncio.Queue()
				# await websocket.close()
				
		await websocket.accept()
			
		# loop until websocket dies
		# while True:
			# # loop until None message or timeout then reset audio buffer and vad
		while True:
			print("MSG start loop")
			try:
				try:
					print("preMSG")
					msg = await asyncio.wait_for(websocket.receive(), timeout=10)
					print("MSG")
					await asyncio.sleep(0)  # Yield to event loop for timeout handling
					# null message from client triggers transcript
					
					if msg is None:
						print("MSG NONE")
						await transcribe_buffer(audio_buffer)
						# break
					else:
						data_bytes = msg.get('bytes')
						if data_bytes is None:
							print("MSG bytes NONE", )
							await transcribe_buffer(audio_buffer)
							# break
						else:
							print(data_bytes[0:10])
							sf = soundfile.SoundFile(io.BytesIO(data_bytes)) #, channels=1,endian="LITTLE",samplerate=SAMPLING_RATE, subtype="FLOAT",format="RAW")
							audio, _ = librosa.load(sf,sr=SAMPLING_RATE,dtype=np.float32)
							print("MSG NONE sf",sf)
							await audio_buffer.put(audio)
							print("MSG put audio")
							# await vad.feed(data_bytes)
							print("MSG fed audio")
							# del sf
							# del audio
							# del data_bytes
				except asyncio.TimeoutError as e:
					print("TIMEOUT ERR",e)
					# break
			except WebSocketDisconnect:
				print("DISCONNECT")	
				break
				# del audio_buffer
				# del vad
				# print('CLOSE WS CONNECT CLIENT')
				# pass
			except RuntimeError as e:
				print("RUNN ERR",e)
				break;
		print("ALL DONE inner" )
		# reset buffers when loop breaks after None message
		del audio_buffer
		audio_buffer = asyncio.Queue()
		# del vad
		# vad = VadDetector(vad_callback)
		# print("ALL DONE outer")	
		
	
		
	

