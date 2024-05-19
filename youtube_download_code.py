import re
from typing import AsyncGenerator

from fastapi import HTTPException
import yt_dlp

from logger_code import LoggerBase
from metadata_code import MetadataService
from pydantic_models import global_state, AudioProcessRequest



from typing import AsyncGenerator

async def download_youtube_to_mp3(yt_url: str,  logger: LoggerBase) -> AsyncGenerator[dict, None]:
    '''download_youtube_to_mp3

    - Downloads an mp3 of the youtube video in the format best for transcription.  The YouTube video
      is downloaded to a directory that the transcriber will use to get the mp3 file from.
    - Builds the Obsidian frontmatter by getting the YouTube metadata into YAML format. This
      will serve as the top of the Obsidian note.
    '''
    output_dir = "temp"  # Temporary storage container for mp3 files.
    metadata = MetadataService()
    yield {"status": "Downloading YouTube video..."}
    logger.debug(f"Starting download process for: {yt_url} into directory: {output_dir}")
    try:
        # YouTube provides some great metadata to use as frontmatter at the top of the Obsidian note
        yaml_metadata, chapters = metadata.extract_youtube_metadata(youtube_url=yt_url)

    except Exception as e:
        logger.error(f"Error extracting YouTube metadata: {e}")
        raise Exception(f"Failed to extract YouTube metadata for URL {yt_url}: {e}")

    sanitized_filename = sanitize_filename(filename=yaml_metadata['filename'])

    filepath = output_dir + '/' + sanitized_filename
    download_yt_to_mp3(filepath, yt_url, logger)
    global_state.update(yaml_metadata=yaml_metadata, chapters=chapters,mp3_filepath=filepath + '.mp3')
    yield {"status": "YouTube Download complete."}

def sanitize_filename(filename: str) -> str:
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

def download_yt_to_mp3(output_file:str,yt_url:str, logger:LoggerBase) -> None:

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

    return

def isYouTubeUrl(request: AudioProcessRequest) -> bool:
    if request.youtube_url and request.file:
        raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
    elif request.youtube_url:
        return True
    elif request.file:
        return False
    else:
        raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")
