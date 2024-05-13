
import json
from pathlib import Path


from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse


from logger_code import LoggerBase
from pydantic_models import AudioProcessRequest, as_form, global_state, mp3_file_ready_event, transcript_ready_event
from utils import isYouTubeUrl,download_youtube_to_mp3, transcribe_mp3

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
async def process_audio(background_tasks: BackgroundTasks, audio_input: AudioProcessRequest = Depends(as_form)):
    global_state.reset()
    global_state.update(audio_quality=audio_input.audio_quality)
    logger.debug("-> Starting process_audio")
    if isYouTubeUrl(audio_input):
        global_state.update(youtube_url=audio_input.youtube_url)
        # Enqueue the download task, and then the transcription task
        background_tasks.add_task(download_youtube_to_mp3, yt_url=audio_input.youtube_url, output_dir='.', logger=logger)
        # The mp3_filepath is set in the download_youtube... task.  Thus, using global_state.
        background_tasks.add_task(transcribe_mp3, mp3_filepath=global_state.mp3_filepath, logger=logger)
    else:  # Directly handle uploaded file
        global_state.update(mp3_filepath = audio_input.file.filename)
        mp3_file_ready_event.set()
        background_tasks.add_task(transcribe_mp3, logger=logger)

    return f"data: {json.dumps({'transcription':'START'})}"



@app.get("/api/v1/sse")
async def sse_events():
    '''Set up the sse channel.'''
    logger.debug("-> In sse_events.")
    # All our code shifts to being done within the event_stream
    # This way, the client can get status update and the final transcript.
    return StreamingResponse(event_stream(), media_type="text/event-stream")

async def event_stream():
    logger.debug("-> in event_stream.")
    await transcript_ready_event.wait()
    mp3_path = global_state.mp3_filepath
    filename_stem = Path(mp3_path).stem if mp3_path else "Transcript"
    yield f"data: {json.dumps({'transcript_text': global_state.transcript_text, 'filename': filename_stem})}\n\n"



if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app:app', host="127.0.0.1", port=8000, reload=True)
