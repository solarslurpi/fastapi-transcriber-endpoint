from typing import Optional

from fastapi import UploadFile, Form, File
from pydantic import BaseModel

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