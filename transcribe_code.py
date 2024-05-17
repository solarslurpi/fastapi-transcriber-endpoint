import asyncio
import os
import time

from pydub import AudioSegment
import torch
import yaml
from transformers import pipeline


from logger_code import LoggerBase
from pydantic_models import  global_state, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP

async def transcribe_mp3(mp3_filepath: str, logger: LoggerBase):
    whisper_model = AUDIO_QUALITY_MAP.get(global_state.audio_quality, "distil-whisper/distil-large-v3")
    torch_compute_type = COMPUTE_TYPE_MAP.get(global_state.compute_type)
    logger.debug(f"Transcribing file path: {mp3_filepath}")
    chapters = global_state.chapters
    transcription_time = 0

    if chapters is not None:
        yield {'status': f'Transcribing {len(chapters)} chapter(s).'}
        logger.debug(f"Number of chapters: {len(chapters)}")

    transcription_text = ''
    if chapters is not None and len(chapters) > 0:
        start_time = time.time()
        async for event in transcribe_chapters(chapters, logger, mp3_filepath, whisper_model, torch_compute_type):
            yield event
            if 'transcript_part' in event:
                transcription_text += event['transcript_part']
        end_time = time.time()
        transcription_time = end_time - start_time
    else:
        start_time = time.time()
        transcription_text = await transcribe(mp3_filepath, logger, whisper_model, torch_compute_type)
        end_time = time.time()
        transcription_time = end_time - start_time

    data = yaml.safe_load(global_state.yaml_metadata)
    data['transcription time'] = round(transcription_time, 1)
    data_str = yaml.dump(data)
    startstop = "---\n"
    obsidian_yaml = startstop + data_str + startstop
    total_transcript = obsidian_yaml + transcription_text
    global_state.update(transcript_text=total_transcript)
        # Yield the final transcription text
    yield {'done': 'Transcription complete.'}

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
    result = transcriber("temp.wav", chunk_length_s=30, batch_size=8)
    return result['text']

async def transcribe_chapters(chapters: list, logger: LoggerBase, mp3_filepath: str, hf_model_name: str = "distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype = torch.float16):
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
        start_time_str = time.strftime('%H:%M:%S', time.gmtime(chapter['start_time']))
        transcription_chapter= f"## {chapter['title']}\n"
        transcription_chapter += f"{start_time_str}\n"
        transcription_chapter += f"{transcription}\n"
        chapters_text += transcription_chapter

        # Yield progress event for each chapter
        yield {'chapter': transcription_chapter}






async def transcribe(mp3_filename: str, logger:LoggerBase, hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16) -> str:
    logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")
    # Get the transcript
    transcription_text = await _transcribe_pipeline(mp3_filename, logger, hf_model_name, compute_type_pytorch )

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
