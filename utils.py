
import os
import re

import yaml
import yt_dlp
from fastapi import HTTPException

from logger_code import LoggerBase
from pydantic_models import  global_state, mp3_file_ready_event, transcript_ready_event, AudioProcessRequest, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP
from transcribe_code import transcribe, process_chapters

def isYouTubeUrl(request: AudioProcessRequest) -> bool:
    if request.youtube_url and request.file:
        raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
    elif request.youtube_url:
        return True
    elif request.file:
        return False
    else:
        raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")

async def download_youtube_to_mp3(yt_url: str, output_dir:str, logger:LoggerBase):
    logger.debug(f"Starting download process for: {yt_url} into directory: {output_dir}")
    # The YouTube title is used as the filename. Sometimes, there are characters - like asian 'double colon' that won't work when opening and closing files (on Windows at least).  So we look at the title first then download.
    filename, global_state.tags, global_state.description, global_state.duration, global_state.chapters = get_yt_filename(yt_url=yt_url, logger=logger)
    # Clean out any characters that don't work great in filenames.
    sanitized_filename = sanitize_filename(filename=filename,logger=logger)
    filepath = output_dir + '/' + sanitized_filename
    download_yt_to_mp3(filepath, yt_url, logger)
    global_state.update(mp3_filepath = filepath + '.mp3')
    mp3_file_ready_event.set()

async def transcribe_mp3(mp3_filepath: str, logger: LoggerBase):

    await mp3_file_ready_event.wait()
    # Why not just pass these in? Because of the way this background task uses an event to start the code actually going.
    mp3_filepath = global_state.mp3_filepath
    whisper_model = AUDIO_QUALITY_MAP.get(global_state.audio_quality, "distil-whisper/distil-large-v3") # Get hf model name from simple name.
    torch_compute_type = COMPUTE_TYPE_MAP.get(global_state.compute_type) # get torch.dtype from simple name.
    logger.debug(f"Transcribing file path: {mp3_filepath}")
    chapters = global_state.chapters

    if chapters is not None and len(chapters) > 0:
        transcription_text = process_chapters(chapters, logger, mp3_filepath, whisper_model, torch_compute_type)
    else:
        transcription_text = await transcribe(mp3_filepath, logger, whisper_model, torch_compute_type, )
    metadata_text = build_frontmatter()

    # Combine metadata with transcription text
    total_transcript = metadata_text + transcription_text
    global_state.update(transcript_text = total_transcript)
    transcript_ready_event.set()


def build_frontmatter():
    youtube_url = f'{global_state.youtube_url}' if global_state.youtube_url else ''
    filename = os.path.basename(global_state.mp3_filepath) if global_state.mp3_filepath else ''
    # Ensure each tag is prefixed with '#' and concatenated correctly
    tags = ' '.join(f'#{tag.replace(" ", "-")}' for tag in global_state.tags) if global_state.tags else ''
    # YAML didn't like <CR LF>..these were replaced with a space.
    description = global_state.description.replace('\r\n', ' ').replace('\n', ' ') if global_state.description else ''
    duration = global_state.duration
    data = {
        "youTube URL": f'{youtube_url}',
        "filename": f'{filename}',
        "tags": f'{tags}',
        "description": f'{description}',
        "duration": f'{format_time(duration)}',
        "audio quality": f'{AUDIO_QUALITY_MAP[global_state.audio_quality]}',
        "compute type": f'{str(COMPUTE_TYPE_MAP[global_state.compute_type])}'
    }

    # Serialize data to a YAML string
    yaml_string = yaml.dump(data)
    yaml_start_stop = "---\n"
    frontmatter = yaml_start_stop + yaml_string + yaml_start_stop
    return frontmatter

def format_time(seconds):
    hours = seconds // 3600  # Calculate the number of hours
    minutes = (seconds % 3600) // 60  # Calculate the remaining minutes
    seconds = seconds % 60  # Calculate the remaining seconds
    return f"{hours}h {minutes}m {seconds}s"  # Format the string

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
        duration = info_dict['duration']
        chapters = info_dict['chapters']

        # Get the filename
        filename = ydl.prepare_filename(info_dict)
        logger.debug(f"Filename that would be used: {filename}", )
        return filename, tags, description, duration, chapters

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

def clean_youtube_description(description_text):
    # Replace newline characters with a space to prevent breaking YAML format
    cleaned_text = description_text.replace('\r\n', ' ').replace('\n', ' ')

    # Handle special characters for YAML
    # Escape double quotes in the text
    cleaned_text = cleaned_text.replace('"', '\\"')

    # Replace '@' with '"@"' within quotes if it is part of a username or handle
    # This helps preserve the original meaning without YAML parsing errors
    cleaned_text = cleaned_text.replace('@', '"@"')
    # Strip all characters to the left of the first ASCII letter or number
    cleaned_text = re.sub(r'^[^a-zA-Z0-9]+', '', cleaned_text)


    return cleaned_text