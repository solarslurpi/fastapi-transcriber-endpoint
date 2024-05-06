from fastapi import HTTPException
from pydantic_models import AudioProcessRequest


def isYouTubeUrl(request:AudioProcessRequest) -> bool:
    if request.youtube_url and request.file:
        raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
    elif request.youtube_url:
        return True
    elif request.file:
        return False
    else:
        raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")