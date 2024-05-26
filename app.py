import asyncio
import logging
import json
import os
import shutil
import yaml

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from logger_code import LoggerBase
from pydantic_models import AudioProcessRequest, as_form, global_state
from transcribe_code import transcribe_mp3
from metadata_code import MetadataService
from youtube_download_code import YouTubeDownloader

app = FastAPI()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # The origin(s) to allow requests from
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

logger = LoggerBase.setup_logger("fastapi-transcriber-endpoint", level=logging.DEBUG)

metadata_service = MetadataService()

@app.post("/api/v1/process_audio")
async def process_audio(audio_input: AudioProcessRequest = Depends(as_form)):
    global_state.reset()
    global_state.update(audio_quality=audio_input.audio_quality)
    logger.debug("app.process_audio: Starting init_audio")
    # Processing moves to the event stream.
    if YouTubeDownloader.is_youtube_url(audio_input):
        global_state.update(youtube_url=audio_input.youtube_url, isYouTube_url=True)
    else:
        file_path = prep_file_for_transcription(audio_input.file)
        global_state.update(mp3_filepath=file_path, isYouTube_url=False)
    # Return a success message
    return JSONResponse(content={"message": "Audio processing started successfully"}, status_code=200)

def prep_file_for_transcription(obsidian_file) -> str:
    '''prepare the file for transcription

    If the file is of type UploadFile, the contents of the mp3 file need to be written to a temporary file.  Then the path to the temporary file is returned. This will be used by the transcription code.
    '''
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_location = os.path.join(temp_dir, obsidian_file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(obsidian_file.file, buffer)
    return file_location

@app.get("/api/v1/stream")
async def stream():
    # Starts the process....
    return StreamingResponse(event_stream(), media_type="text/event-stream")

async def event_stream():
    # The mp3 file can come from a YouTube video or an mp3 file.
    # IF the mp3 file comes from a YouTube video, we must download the mp3 file.
    if global_state.isYouTube_url:
        # Get the mp3 file and metadata. Once we have the mp3 file, it can be transcribed.
        try:
            downloader = YouTubeDownloader(global_state.youtube_url, logger)  # Pass the loop to the downloader.
            async for event in downloader.download_youtube_to_mp3():
                logger.debug(f"app.event_stream: Yielding event: {event}")
                yield f"data: {json.dumps(event)}\n\n"
            # Update global_state.mp3_filepath after download completes
            global_state.update(mp3_filepath=f"{downloader.base_temp_mp3_filepath}.mp3")
        except Exception as e:
            logger.debug(f"app.event_stream: Yielding transcription event: {event}")
            yield f"data: {json.dumps({'error': str(e.args[0])})}\n\n"
    else:
        global_state.yaml_metadata = metadata_service.extract_mp3_metadata(global_state.mp3_filepath)

    # Once the mp3 file is available, we can move on to transcription. The file will be
    # available immediately if the start was a file upload.
    while not global_state.mp3_filepath:
        await asyncio.sleep(0.1)

    # Now we are on to transcription.
    try:
        async for event in transcribe_mp3(global_state.mp3_filepath, logger):
            if 'done' in event:
                # Serialize data to a YAML string
                global_state.update(transcription_time=event['done'])
                yaml_string = yaml.dump(global_state.yaml_metadata)
                # Build the frontmatter and send to the Obsidian client.
                frontmatter = "---\n" + yaml_string + "---\n"
                yield f"data: {json.dumps({'basefilename':global_state.basefilename})}\n\n"
                yield f"data: {json.dumps({'frontmatter': frontmatter})}\n\n"
                yield f"data: {json.dumps({'done':'Finished Transcription.'})}\n\n"
                # Delete the mp3 file.
                if os.path.exists(global_state.mp3_filepath):
                    os.remove(global_state.mp3_filepath)
            else:
                yield f"data: {json.dumps(event)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e.args[0])})}\n\n"


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)