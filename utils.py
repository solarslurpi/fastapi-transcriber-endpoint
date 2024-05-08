import asyncio
import json
from pathlib import Path

import yt_dlp
from fastapi import HTTPException
from transformers import pipeline
import torch

from pydantic_models import update_state, global_state, mp3_file_ready_event, transcript_ready_event, AudioProcessRequest, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP

def isYouTubeUrl(request: AudioProcessRequest) -> bool:
    if request.youtube_url and request.file:
        raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
    elif request.youtube_url:
        return True
    elif request.file:
        return False
    else:
        raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")

async def download_youtube_to_mp3(yt_url: str, output_dir:str, logger):
    logger.debug(f"Starting download process for: {yt_url} into directory: {output_dir}")
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        'outtmpl': str(output_dir_path / '%(title)s'),
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'postprocessor_args': [
            '-ar', '16000',  # sample rate of ASR models like whisper
            '-ac', '1',  # 1 channel is best for transcription.
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url=yt_url, download=True)
            filename = info['title'] + '.mp3'
            file_path = output_dir_path / filename
            update_state(youtube_url=yt_url, mp3_filepath=str(file_path), tags=info['tags'], description=info['description'])

            logger.debug(global_state.model_dump_json(indent=4))
            mp3_file_ready_event.set()
    except Exception as e:
        logger.error(f"An error occurred during the download or conversion process: {e}")

async def transcribe_mp3(logger):
    await mp3_file_ready_event.wait()
    logger.debug(f"Transcribing file path: {global_state.mp3_filepath}")
    hf_model_name = AUDIO_QUALITY_MAP.get(global_state.audio_quality, "distil-whisper/distil-large-v3")
    compute_type_pytorch = COMPUTE_TYPE_MAP.get(global_state.compute_type, torch.float16)

    logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")

    transcription_text = ""
    audio_file_path = global_state.mp3_filepath
    # Get the transcript
    transcription_text = await _transcribe_pipeline(audio_file_path, hf_model_name, compute_type_pytorch, logger)
  # Extract the filename from the mp3_filepath
    filename = Path(global_state.mp3_filepath).name if global_state.mp3_filepath else ""

    # Prepare the metadata string
    # Start YAML front matter
    metadata = '---\n'

    # Add YouTube URL
    if global_state.youtube_url:
        metadata += f"YouTube URL: {global_state.youtube_url}\n"
    else:
        metadata += "YouTube URL: \n"

    # Add filename
    if global_state.mp3_filepath:
        filename = Path(global_state.mp3_filepath).stem
        metadata += f"Filename: {filename}\n"
    else:
        metadata += "Filename: \n"

    # Add tags
    if global_state.tags:
        formatted_tags = ' '.join(f'#{tag}' for tag in global_state.tags)
        metadata += f"Tags: {formatted_tags}\n"
    else:
        metadata += "Tags: \n"

    # Add description
    if global_state.description:
        metadata += f"Description: {global_state.description}\n"
    else:
        metadata += "Description: \n"

    # Add audio quality and compute type
    audio_quality = AUDIO_QUALITY_MAP.get(global_state.audio_quality, 'default')
    compute_type = COMPUTE_TYPE_MAP.get(global_state.compute_type, 'default')
    metadata += f"Audio Quality: {audio_quality}\n"
    metadata += f"Compute Type: {compute_type}\n"

    # End YAML front matter
    metadata += '---\n\n'

    # Combine metadata with transcription text
    total_transcript = metadata + transcription_text
    update_state(transcript_text = total_transcript)
    transcript_ready_event.set()




async def _transcribe_pipeline(audio_filename: str, model_name: str, compute_float_type: torch.dtype, logger) -> str:
    logger.debug(f"Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL {model_name} using compute type {compute_float_type}")
    def load_and_run_pipeline():
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1,
            torch_dtype=compute_float_type
        )
        return pipe(audio_filename, chunk_length_s=30, batch_size=8, return_timestamps=False)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, load_and_run_pipeline)
    return result['text']
