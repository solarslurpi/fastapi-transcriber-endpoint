import json
import os
import re

import yaml
import yt_dlp
from fastapi import HTTPException


from logger_code import LoggerBase
from pydantic_models import  global_state, AudioProcessRequest, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP


def isYouTubeUrl(request: AudioProcessRequest) -> bool:
    if request.youtube_url and request.file:
        raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
    elif request.youtube_url:
        return True
    elif request.file:
        return False
    else:
        raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")

async def download_youtube_to_mp3(yt_url: str, output_dir: str, logger: LoggerBase):
    yield {"status": "Downloading YouTube video..."}
    logger.debug(f"Starting download process for: {yt_url} into directory: {output_dir}")
    try:
        metadata_dict = get_yt_metadata(yt_url=yt_url, logger=logger)
    except Exception as e:
        raise Exception(e)

    global_state.update(chapters=metadata_dict['chapters'])

    sanitized_filename = sanitize_filename(filename=metadata_dict['title'], logger=logger)
    # Let obsidian know the filename
    yield {"filename": sanitized_filename}
    filepath = output_dir + '/' + sanitized_filename
    download_yt_to_mp3(filepath, yt_url, logger)

    yield {"status": "Download complete."}
    global_state.update(mp3_filepath=filepath + '.mp3')

    yaml_metadata = build_yaml_metadata(filepath, metadata_dict)

    global_state.update(yaml_metadata=yaml_metadata)



def build_yaml_metadata(mp3_filepath:str, yt_metadata:dict) -> str:

    filename = os.path.basename(mp3_filepath) if global_state.mp3_filepath else ''
    tags = ' '.join(f'#{tag.replace(" ", "-")}' for tag in yt_metadata['tags']) if yt_metadata['tags'] else ''
    data = {
        "youTube URL": f"{yt_metadata['webpage_url']}",
        "filename": f'{filename}',
        "tags": tags,
        "description": f"{yt_metadata['description']}",
        "duration": f"{format_time(yt_metadata['duration'])}",
        "audio quality": f'{AUDIO_QUALITY_MAP[global_state.audio_quality]}',
        "compute type": f'{str(COMPUTE_TYPE_MAP[global_state.compute_type])}',
        "channel name": f"{yt_metadata['channel']}",
        "upload date": f"{yt_metadata['upload_date']}",
        "uploader id": f"{yt_metadata['uploader_id']}",
    }


    yaml_metadata = yaml.dump(data)
    return yaml_metadata

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

def get_yt_metadata(yt_url:str, logger):
    # Might not be used in workflow. But evolving how to incorporate metadata in transcript.  There is a wealth of semantic knowledge.
        # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': '%(title)s',
        'quiet': True,  # Suppress verbose output
        'simulate': True,  # Do not download the video
        'getfilename': True,  # Just print the filename
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract video information
            info_dict = ydl.extract_info(yt_url, download=False)
        except Exception as e:
            # Regular expression to remove ANSI escape sequences
            cleaned_message = re.sub(r'\x1b\[([0-9;]*[mGKF])', '', e.msg)
            logger.error(f"Error extracting info from YouTube URL: {yt_url}. Error: {cleaned_message}")
            raise Exception(cleaned_message)
    return info_dict

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
        # Just download. We already have the info.
        ydl.extract_info(yt_url, download=True)

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