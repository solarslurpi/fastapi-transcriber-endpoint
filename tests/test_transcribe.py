import pytest
import time

from logger_code import LoggerBase
from pydantic_models import global_state, mp3_file_ready_event
from transcribe_code import transcribe_mp3, transcribe
from utils import get_yt_metadata

@pytest.fixture
def mp3_file():
    mp3_file = 'Bluelab_Pulse_Meter_Review.mp3'
    return mp3_file

@pytest.fixture
def logger():
    logger = LoggerBase.setup_logger('test_transcribing')
    return logger

@pytest.fixture
def setup_global_state(mp3_file):
    yt_url = "https://www.youtube.com/watch?v=KbZDsrs5roI"  # Example YouTube URL
    yt_metadata = get_yt_metadata(yt_url)
    global_state.mp3_filepath = mp3_file
    global_state.audio_quality = "tiny"
    global_state.compute_type = "default"
    global_state.chapters = yt_metadata.get('chapters', [])
    global_state.youtube_url = yt_url
    global_state.frontmatter_text = '''---
audio quality: openai/whisper-large-v3
channel name: KIS Organics
compute type: torch.float16
description: 'I am really enjoying using the Bluelab Pulse Meter in my grow room!
  I go over how it works as well as some potential uses for living soil growers.


  We currently have it available on our website for the best price online if anyone
  wants to try it. https://www.kisorganics.com/products/bluelab-pulse-multimedia-ec-mc-meter?_pos=1&_sid=cfeeacdab&_ss=r


  Shop: www.KISorganics.com

  Instagram: @KISorganics

  Twitter: @KISorganics

  Facebook: www.Facebook.com/KISorganics'
duration: 0h 5m 18s
filename: Bluelab_Pulse_Meter_Review
tags: ''
upload date: '20240426'
uploader id: '@kisorganics'
youTube URL: https://www.youtube.com/watch?v=KbZDsrs5roI
---'''


@pytest.mark.asyncio
async def test_transcribe_with_actual_processing(logger):
    # The transcribe() function is at the heart of the transcription process.  It actually does the transcription.

    # Define a real MP3 file path and expected transcript
    test_audio_file = "./Bluelab_Pulse_Meter_Review.mp3"

    # Run the actual transcription function
    transcription_result = await transcribe(test_audio_file, logger)
    logger.debug(f"--------------------------\nFirst 100 chars of the transcript:\n{transcription_result[:100]}\n-------------------------------")
    # Assert the transcription is as expected
    assert len(transcription_result) > 50 # Assume a transcription has greater than 50 characters

@pytest.mark.asyncio
async def test_transcribe_mp3_duration(logger, setup_global_state, mp3_file):
    mp3_file_ready_event.set() # transcribe_mp3 waits on the mp3 file being ready.  This signifies it is.
    await transcribe_mp3(mp3_file, logger)

    print(f"Transcription Time: {global_state.transcription_time} seconds.")


    # Check if transcript text is updated
    assert global_state.transcript_text is not None
    assert len(global_state.transcript_text) > 0

    # Check if chapters were processed correctly
    assert global_state.chapters is not None
    assert len(global_state.chapters) > 0
