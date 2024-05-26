import asyncio
from queue import Queue
from typing import AsyncGenerator

from fastapi import HTTPException
import yt_dlp

from pydantic_models import AudioProcessRequest
from metadata_code import MetadataService

class YouTubeDownloader:
    def __init__(self, yt_url: str, logger: object):
        self.yt_url = yt_url
        self.logger = logger
        self.yt_progress_updates = Queue()
        self.isComplete = False
        self.base_temp_mp3_filepath = "temp/downloaded_file"


    def progress_hook(self, d):
        status = d.get('status')
        if status == 'finished':
            self.yt_progress_updates.put("Download finished successfully.")
            self.isComplete = True
        elif status == 'downloading':
            downloaded = d.get('downloaded_bytes')
            total = d.get('total_bytes')
            if total:
                percentage = downloaded / total * 100
                self.yt_progress_updates.put(f"Downloading: {percentage:.1f}%")
        elif status == 'error':
            self.yt_progress_updates.put(f"An error occurred: {d.get('error', 'Unknown error')}")
            self.isComplete = True

    def download_yt_to_mp3(self):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': self.base_temp_mp3_filepath,
            'progress_hooks': [self.progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.yt_url])

    async def yield_progress_updates(self) -> AsyncGenerator[dict, None]:
        while not self.isComplete or not self.yt_progress_updates.empty():
            while not self.yt_progress_updates.empty():
                progress_update = self.yt_progress_updates.get()
                yield {"status": progress_update}
            await asyncio.sleep(1)

    async def download_youtube_to_mp3(self) -> AsyncGenerator[dict, None]:
        # YouTube provides some great metadata to use as frontmatter at the top of the Obsidian note.
        metadata = MetadataService()
        try:
            metadata.extract_youtube_metadata(youtube_url=self.yt_url,logger=self.logger)
        except Exception as e:
            self.logger.error(f"Error extracting YouTube metadata: {e}")
            raise Exception(f"Failed to extract YouTube metadata for URL {self.yt_url}: {e}")



        loop = asyncio.get_running_loop()
        download_task = loop.run_in_executor(None, self.download_yt_to_mp3)
        progress_updates = self.yield_progress_updates()

        try:
            async for update in progress_updates:
                yield update
        except StopAsyncIteration:
            pass

        await download_task
        yield {"status": "YouTube Download complete."}

    def is_youtube_url(request: AudioProcessRequest) -> bool:
        if request.youtube_url and request.file:
            raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
        elif request.youtube_url:
            return True
        elif request.file:
            return False
        else:
            raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")
