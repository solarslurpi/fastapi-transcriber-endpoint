# metadata_service.py
import re

from mutagen.mp3 import MP3
from typing import Dict
import yt_dlp

import os
from datetime import datetime

from pydantic_models import global_state, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP

class MetadataService:
    def extract_youtube_metadata(self, youtube_url: str) -> Dict[str, str]:
        ydl_opts = {
            'outtmpl': '%(title)s',
            'quiet': True,
            'simulate': True,
            'getfilename': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            tags = info_dict.get('tags', [])
            formatted_tags = ', '.join(tag.replace(' ', '_') for tag in tags)
            metadata = {
                "youTube URL": info_dict.get('webpage_url', ''),
                "filename": ydl.prepare_filename(info_dict),
                "tags": formatted_tags,
                "description": info_dict.get('description', ''),
                "duration": self.format_time(info_dict.get('duration', 0)),
                "audio quality": AUDIO_QUALITY_MAP.get(global_state.audio_quality, ''),
                "compute type": str(COMPUTE_TYPE_MAP.get(global_state.compute_type, '')),
                "channel name": info_dict.get('uploader', ''),
                "upload date": info_dict.get('upload_date', ''),
                "uploader id": info_dict.get('uploader_id', '')
            }

            # Chapters are extracted and returned separately because they are used for knowing the
            # transcript part stop and starts, but is not part of the frontmatter.
            chapters = info_dict.get('chapters', [])
            return metadata, chapters

    def extract_mp3_metadata(self, mp3_filepath: str) -> Dict[str, str]:
        audio = MP3(mp3_filepath)
        duration = round(audio.info.length)
        upload_date = datetime.fromtimestamp(os.path.getmtime(mp3_filepath)).strftime('%Y-%m-%d')
        return {
            "duration": self.format_time(duration),
            "upload_date": upload_date,
            "filename": os.path.basename(mp3_filepath),
            "audio quality": AUDIO_QUALITY_MAP.get(global_state.audio_quality, ''),
            "compute type": str(COMPUTE_TYPE_MAP.get(global_state.compute_type, '')),
        }

    def format_time(self, seconds: int) -> str:
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        return f"{hours:d}:{mins:02d}:{secs:02d}"
