import asyncio
import logging
import json
import os
import shutil


from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse


from logger_code import LoggerBase
from pydantic_models import AudioProcessRequest, as_form, global_state
from transcribe_code import transcribe_mp3
from utils import isYouTubeUrl,download_youtube_to_mp3

app = FastAPI()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # The origin(s) to allow requests from
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

logger = LoggerBase.setup_logger("fastapi-transcriber-endpoint",level = logging.DEBUG)

audio_input_global = None

@app.post("/api/v1/process_audio")
async def process_audio( audio_input: AudioProcessRequest = Depends(as_form)):
    global_state.reset()
    global_state.update(audio_quality=audio_input.audio_quality)
    logger.debug("-> Starting init_audio")

    if isYouTubeUrl(audio_input):
        global_state.update(youtube_url=audio_input.youtube_url)
    else:  # Directly handle uploaded file
        prep_file_for_transcription(audio_input.file)


    return {"status": "Transcription started"}

def prep_file_for_transcription(obsidian_file) -> None:
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_location = os.path.join(temp_dir, obsidian_file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(obsidian_file.file, buffer)
    global_state.update(mp3_filepath=file_location)

@app.get("/api/v1/stream")
async def stream():
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# Add this to your FastAPI app (app.py)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}

async def event_stream():
    if global_state.youtube_url:
        # wait for downloading youtube to complete at which point there will be
        # an mp3 filename.
        try:
            async for event in download_youtube_to_mp3(global_state.youtube_url, '.', logger):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e.args[0])})}\n\n"
    # once we hgave the mp3 filename, we can move on to transcription.
    while not global_state.mp3_filepath:
        await asyncio.sleep(0.1)

    # Moving on to transcribing.
    async for event in transcribe_mp3(global_state.mp3_filepath, logger):
        yield f"data: {json.dumps(event)}\n\n"

    yield f"data: {json.dumps({'done': 'Transcription completed.'})}\n\n"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
