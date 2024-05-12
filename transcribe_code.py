import asyncio
import time

from pydub import AudioSegment
import torch
from transformers import pipeline

from logger_code import LoggerBase

# Define a function to slice audio
def slice_audio(mp3_filepath, start_ms, end_ms):
    audio = AudioSegment.from_file(mp3_filepath)
    return audio[start_ms:end_ms]


def transcribe_chapter(audio_segment: AudioSegment, hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16) -> str:
    # Load model
    transcriber = pipeline("automatic-speech-recognition",
                           model=hf_model_name,
                           device=0 if torch.cuda.is_available() else -1,torch_dtype=compute_type_pytorch)
    # Export the audio segment to a format compatible with the Whisper model
    audio_segment.export("temp.wav", format="wav")
    # # Transcribe
    result = transcriber("temp.wav")
    return result['text']

def process_chapters(chapters:list,logger:LoggerBase, mp3_filepath:str , hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16):
    chapters_text = ''
    for chapter in chapters:
        logger.debug(f'processing chapter {chapter}')
        # Convert start and end times from seconds to milliseconds
        start_ms = int(chapter['start_time'] * 1000)
        end_ms = int(chapter['end_time'] * 1000)
        # Slice the audio
        audio_segment = slice_audio(mp3_filepath, start_ms, end_ms)
        # Transcribe the audio segment
        transcription = transcribe_chapter(audio_segment, hf_model_name=hf_model_name, compute_type_pytorch=compute_type_pytorch)
        # Write to Markdown file
        chapters_text += f"## {chapter['title']}\n\n{transcription}\n\n"
    return chapters_text

async def transcribe(mp3_filename: str, logger:LoggerBase, hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16) -> str:
    start_time = time.time()
    logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")
    # Get the transcript
    transcription_text = await _transcribe_pipeline(mp3_filename, logger, hf_model_name, compute_type_pytorch )
    end_time = time.time()
    duration = end_time - start_time
    logger.debug(f"Duration: {duration} seconds. ")
    return transcription_text

async def _transcribe_pipeline(mp3_filename: str, logger:LoggerBase, model_name: str, compute_float_type: torch.dtype ) -> str:
    logger.debug(f"Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL {model_name} using compute type {compute_float_type}")
    def load_and_run_pipeline():
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1,
            torch_dtype=compute_float_type
        )
        return pipe(mp3_filename, chunk_length_s=30, batch_size=8, return_timestamps=False)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, load_and_run_pipeline)
    return result['text']

# if __name__ == "__main__":
#     logger = LoggerBase.setup_logger('HF_whisper')
#     text = asyncio.run(transcribe(mp3_filename='Bluelab_Pulse_Meter_Review.mp3', logger=logger))
#     logger.debug(f"Transcription text: {text}")
