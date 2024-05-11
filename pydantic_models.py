import asyncio
from typing import Optional

import torch
from fastapi import UploadFile, Form, File
from pydantic import BaseModel, Field
AUDIO_QUALITY_MAP = {
    "default":  "openai/whisper-tiny.en",
    "tiny": "openai/whisper-tiny.en",
    "small": "openai/whisper-small.en",
    "medium": "openai/whisper-medium.en",
    "large": "openai/whisper-large-v3"
}

COMPUTE_TYPE_MAP = {
    "default": torch.float16,
    "float16": torch.float16,
    "float32": torch.float32,
}
# Define the blueprint for the input data.  Note that the input
# is either a YouTube URL or an UploadFile.  Both are optional
# to allow for one or the other.
class AudioProcessRequest(BaseModel):
    youtube_url: Optional[str] = None
    file: Optional[UploadFile] = None

# This dependency function - i.e.: depends(as_form) - Tell FastAPI that
# the data is being passed in as a form. Look for one or both or neither
# of these fields.
def as_form(
    youtube_url: str = Form(None),  # Use Form to specify form data
    file: UploadFile = File(None)  # Use File to specify file upload
) -> AudioProcessRequest:
    return AudioProcessRequest(youtube_url=youtube_url, file=file)

class GlobalState(BaseModel):
    youtube_url: str = Field(default=None, description="URL of the downloaded YouTube video")
    mp3_filepath: str = Field(default=None, description="Location of the MP3 file")
    tags: list = Field(default_factory=list, description="Descriptive tags from the content")
    description: str = Field(default=None, description="Description provided by the content creator")
    audio_quality: str = Field(default="default")
    compute_type: str = Field(default="default")
    transcript_text: str = Field(default=None, description="Transcript of the MP3 file")

# Instance of the global state
global_state = GlobalState()

# Events to manage the state transitions
mp3_file_ready_event = asyncio.Event()
transcript_ready_event = asyncio.Event()

def update_state(**kwargs):
    for key, value in kwargs.items():
        if hasattr(global_state, key):
            setattr(global_state, key, value)


# e.g.:
# Assume these are the new tags you want to set
# new_tags = ['tutorial', 'education', 'python']
# Updating the 'tags' field in the global state
# update_state(tags=new_tags)