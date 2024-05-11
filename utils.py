import asyncio
import re
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
    # The YouTube title is used as the filename. Sometimes, there are characters - like asian 'double colon' that won't work when opening and closing files (on Windows at least).  So we look at the title first then download.
    filename, global_state.tags, global_state.description = get_yt_filename(yt_url=yt_url, logger=logger)
    # Clean out any characters that don't work great in filenames.
    sanitized_filename = sanitize_filename(filename=filename,logger=logger)
    filepath = output_dir + '/' + sanitized_filename
    download_yt_to_mp3(filepath, yt_url, logger)
    update_state(mp3_filepath = filepath + '.mp3')
    mp3_file_ready_event.set()

async def transcribe_mp3(logger):

    await mp3_file_ready_event.wait()
    # Why not just pass these in? Because of the way this background task uses an event to start the code actually going.
    mp3_filepath = global_state.mp3_filepath
    whisper_model = AUDIO_QUALITY_MAP.get(global_state.audio_quality, "distil-whisper/distil-large-v3")
    torch_compute_type = COMPUTE_TYPE_MAP.get(global_state.compute_type)
    logger.debug(f"Transcribing file path: {mp3_filepath}")
    transcription_text = await transcribe(mp3_filepath, whisper_model, torch_compute_type, logger)
    metadata_text = build_metadata()

    # Combine metadata with transcription text
    total_transcript = metadata_text + transcription_text
    update_state(transcript_text = total_transcript)
    transcript_ready_event.set()


async def transcribe(mp3_filename: str, hf_model_name: str, compute_type_pytorch: torch.dtype, logger) -> str:

    logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")
    # Get the transcript
    transcription_text = await _transcribe_pipeline(mp3_filename, hf_model_name, compute_type_pytorch, logger)
    return transcription_text

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

def build_metadata():
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


    metadata += f"Audio Quality: {AUDIO_QUALITY_MAP[global_state.audio_quality]}\n"
    metadata += f"Compute Type: {str(COMPUTE_TYPE_MAP[global_state.compute_type])}\n"

    # End YAML front matter
    metadata += '---\n\n'
    return metadata

def sanitize_filename(filename: str, logger) -> str:
    # Remove the file extension
    name_part = filename.rsplit('.', 1)[0]

    # Replace full-width colons and standard colons with a hyphen or other safe character
    name_part = name_part.replace('：', '_').replace(':', '_')
    # Replace unwanted characters with nothing or specific symbols
    # This regex replaces any non-alphanumeric, non-space, and non-dot characters with nothing
    cleaned_name = re.sub(r"[^a-zA-Z0-9 \.-]", "", name_part)
    # Replace spaces with hyphens
    safe_filename = cleaned_name.replace(" ", "_")

    return safe_filename

def get_yt_filename(yt_url: str, logger) -> str:
    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': '%(title)s',
        # 'quiet': True,  # Suppress verbose output
        'simulate': True,  # Do not download the video
        'getfilename': True,  # Just print the filename
        'logger': logger,
    }

    # Create a YoutubeDL object with the options
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        # Extract video information
        info_dict = ydl.extract_info(yt_url, download=False)
        tags = info_dict['tags']
        description = info_dict['description']

        # Get the filename
        filename = ydl.prepare_filename(info_dict)
        logger.debug(f"Filename that would be used: {filename}", )
        return filename, tags, description

def download_yt_to_mp3(output_file:str,yt_url:str, logger) -> None:

    ydl_opts = {
        'outtmpl': f"{output_file}",
        'logger': logger,
        'format': 'bestaudio/best',
        'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '0'
        }],
        'postprocessor_args': [
            '-ar', '16000',
            '-ac', '1'
        ]
    }

    # Create a YoutubeDL object with the options
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract video information
        info_dict = ydl.extract_info(yt_url, download=True)
