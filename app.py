
import json
import time


from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse


from logger_code import LoggerBase
from pydantic_models import AudioProcessRequest, as_form
from utils import isYouTubeUrl

app = FastAPI()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # The origin(s) to allow requests from
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

logger = LoggerBase.setup_logger("fastapi-transcriber-endpoint")

audio_input_global = None

@app.post("/api/v1/process_audio")
async def process_audio(audio_input: AudioProcessRequest = Depends(as_form)):
    global audio_input_global
    audio_input_global = audio_input
    logger.debug("-> Starting process_audio")

@app.get("/api/v1/sse")
async def sse_events():
    '''Set up the sse channel.'''
    logger.debug("-> In sse_events.")
    return StreamingResponse(event_stream(), media_type="text/event-stream")

async def event_stream():
    logger.debug("-> in event_streams.")
    if isYouTubeUrl(audio_input_global):
        # TODO: Download YouTube video.
        time.sleep(2) # Simulate youtube download...
    yield f"data: {json.dumps({'transcript':'START'})}\n\n"
    transcript_text = await make_transcript()
    yield f"data: {json.dumps({'transcript_text': transcript_text})}\n\n"

async def make_transcript()-> str:
    logger.debug("-> in make_transcript.")
    time.sleep(2) # mimic the time to make the transcript.
    try:
        with open('transcript.txt', 'r', encoding='utf-8') as file:
            file_contents = file.read()
        logger.debug("File content read successfully.")
        return file_contents
    except FileNotFoundError:
        logger.debug("The file does not exist.")
        return 'This is the transcript text to be put in the obsidian folder'
    except IOError:
        logger.debug("An error occurred while reading the file.")
        return 'This is the transcript text to be put in the obsidian folder'


if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app:app', host="127.0.0.1", port=8000, reload=True)
