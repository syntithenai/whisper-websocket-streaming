import os
import asyncio
import soundfile as sf
from typing import BinaryIO, Union, Annotated
import numpy as np
from constants import SAMPLING_RATE, CHANNELS, BLOCKSIZE

async def write_queue_to_audio_file(thefile: BinaryIO,queue, overwrite = False):
    # load file for appending
    current_data = np.array([])
    if (not overwrite): 
        with sf.SoundFile(thefile, mode='r') as infile:
            for block in sf.blocks(thefile, blocksize=BLOCKSIZE, overlap=0): 
                current_data = np.concatenate((current_data ,block),0)
            
    with sf.SoundFile(thefile, mode='w', samplerate=SAMPLING_RATE,
                      channels=CHANNELS) as outfile:
        # write file contents
        if (not overwrite):
            outfile.write(np.reshape(np.array(current_data),(len(current_data),1)))
        # now append queue data
        try:
            while True:
                data = queue.get_nowait()
                outfile.write(data)
        except asyncio.queues.QueueEmpty:
            outfile.close()



def load_audio(file: BinaryIO, encode=False, sr: int = SAMPLING_RATE):
    """
    Open an audio file object and read as mono waveform, resampling as necessary.
    Modified from https://github.com/openai/whisper/blob/main/whisper/audio.py to accept a file object
    Parameters
    ----------
    file: BinaryIO
        The audio file like object
    encode: Boolean
        If true, encode audio stream to WAV before sending to whisper
    sr: int
        The sample rate to resample the audio if necessary
    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """
    if encode:
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input("pipe:", threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
                .run(cmd="/usr/bin/ffmpeg", capture_stdout=True, capture_stderr=True, input=file.read())
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    else:
        out = file.read()

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

    
def pad_audio_packet(indata):
    audio_data = np.array(indata).flatten()
    result = audio_data
    if (len(audio_data) < BLOCKSIZE):
        result = np.pad(result,(0,BLOCKSIZE - len(audio_data)))
    data = np.reshape(np.array(result),(BLOCKSIZE,1))
    return data    
