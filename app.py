import logging
import json


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
async def process_audio(audio_input: AudioProcessRequest = Depends(as_form)):
    global_state.reset()
    global_state.update(audio_quality=audio_input.audio_quality)
    logger.debug("-> Starting init_audio")

    if isYouTubeUrl(audio_input):
        global_state.update(youtube_url=audio_input.youtube_url)
    else:  # Directly handle uploaded file
        global_state.update(mp3_filepath=audio_input.file.filename)
    # All our code shifts to being done within the event_stream
    # This way, the client can get status update and the final transcript.
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Add this to your FastAPI app (app.py)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}

async def event_stream():
    if global_state.youtube_url:
        async for event in download_youtube_to_mp3(global_state.youtube_url, '.', logger):
            logger.debug(f"event: {event}")
            yield f"data: {json.dumps(event)}\n\n"

    async for event in transcribe_mp3(global_state.mp3_filepath, logger):
        logger.debug(f"event: {event}")
        yield f"data: {json.dumps(event)}\n\n"
    logger.debug(f"event: {event}")
    yield f"data: {json.dumps({'status': 'Transcription completed.', 'transcript': global_state.transcript_text})}\n\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app:app', host="127.0.0.1", port=8000, reload=True)
