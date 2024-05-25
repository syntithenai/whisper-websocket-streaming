import webrtcvad
import sys
import os
import time
import numpy as np
import asyncio

from constants import SAMPLING_RATE, VAD_SENSITIVITY, VAD_TIMEOUT, VAD_MIN_VOICE_PACKETS
from audio_utils import pad_audio_packet

vad = webrtcvad.Vad(VAD_SENSITIVITY)
   
def is_voice( in_data):
    #print(len(in_data))
    #if (len(in_data) == 640):
    buffer = np.frombuffer(pad_audio_packet(in_data), np.int16)
    is_speech = vad.is_speech(buffer[0:320].tobytes(), SAMPLING_RATE)
    return is_speech
    #else:
    #    return False




class VadDetector():

	last_voice = time.time()
	have_voice = 0
	callback = None
			
	def __init__(self, callback):
		if not callable(callback): raise Exception('Vad detector must be created with an async callback function')
		self.callback = callback

	async def feed(self, data):
		# check VAD
		# print('vad feed')
		# print(len(data))
		# window_size_samples = 320 # number of samples in a single audio chunk
		# iv = False
		# for i in range(0, len(data), window_size_samples):
			# iv_s = is_voice(data[i: i+ window_size_samples])
			# iv = iv or iv_s
		iv = is_voice(data)
		if iv:
			self.last_voice = time.time()
			self.have_voice = self.have_voice + 1
		now = time.time()
		print(f"VAD:{iv} {now} {self.have_voice}/{VAD_MIN_VOICE_PACKETS} {(now - self.last_voice)}  {VAD_TIMEOUT}")
		if (self.have_voice > VAD_MIN_VOICE_PACKETS and (now - self.last_voice > VAD_TIMEOUT)):
			self.last_voice = time.time()
			self.have_voice = 0
			print(f"VAD:TRIGGER")
			asyncio.create_task(self.callback())
			return True
		return False
			
 
