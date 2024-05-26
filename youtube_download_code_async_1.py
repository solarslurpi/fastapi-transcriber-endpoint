import re
from typing import  AsyncGenerator
import asyncio
from fastapi import HTTPException
from pydantic_models import AudioProcessRequest
import yt_dlp

class YouTubeDownloader:
    def __init__(self, yt_url: str, logger: object, loop: asyncio.AbstractEventLoop):
        self.yt_url = yt_url
        self.logger = logger
        self.yt_progress_updates = asyncio.Queue()  # Initialize the asyncio queue
        self.isComplete = False
        self.output_dir = "temp"
        self.filepath = f"{self.output_dir}/downloaded_file.mp3"
        self.yaml_metadata = None
        self.chapters = None
        self.loop = loop  # Store the event loop

    def progress_hook(self, d):
        status = d.get('status')
        if status == 'finished':
            asyncio.run_coroutine_threadsafe(self.yt_progress_updates.put("Download finished successfully."), self.loop)
            self.isComplete = True
        elif status == 'downloading':
            downloaded = d.get('downloaded_bytes')
            total = d.get('total_bytes')
            if total:
                percentage = downloaded / total * 100
                asyncio.run_coroutine_threadsafe(self.yt_progress_updates.put(f"Downloading: {percentage:.1f}%"), self.loop)
        elif status == 'error':
            asyncio.run_coroutine_threadsafe(self.yt_progress_updates.put(f"An error occurred: {d.get('error', 'Unknown error')}"), self.loop)
            self.isComplete = True

    async def yield_progress_updates(self) -> AsyncGenerator[dict, None]:
        while not self.isComplete or not self.yt_progress_updates.empty():
            while not self.yt_progress_updates.empty():
                progress_update = await self.yt_progress_updates.get()
                yield {"status": progress_update}
            await asyncio.sleep(1)

    def download_yt_to_mp3(self):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': self.filepath,
            'progress_hooks': [self.progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.yt_url])

    async def download_youtube_to_mp3(self) -> AsyncGenerator[dict, None]:
        download_task = asyncio.get_running_loop().run_in_executor(None, self.download_yt_to_mp3)
        progress_task = self.yield_progress_updates()

        try:
            async for update in progress_task:  # Correctly iterate over the async generator
                yield update
        except StopAsyncIteration:
            pass

        await download_task  # Wait for the download task to complete

        yield {"status": "YouTube Download complete."}

    @staticmethod
    def is_youtube_url(request: AudioProcessRequest) -> bool:
        if request.youtube_url and request.file:
            raise HTTPException(status_code=400, detail="Please provide either a YouTube URL or an MP3 file, not both.")
        elif request.youtube_url:
            return True
        elif request.file:
            return False
        else:
            raise HTTPException(status_code=400, detail="No YouTube URL or file provided.")