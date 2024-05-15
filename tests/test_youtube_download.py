import pytest

from logger_code import LoggerBase

from utils import get_yt_metadata, download_youtube_to_mp3

@pytest.fixture
def logger():
    logger = LoggerBase.setup_logger('test_transcribing')
    return logger

@pytest.fixture
def youtube_url():
    youtube_url = 'https://www.youtube.com/watch?v=KbZDsrs5roI'
    return youtube_url


def test_get_youtube_metadata(youtube_url):
    info_dict = get_yt_metadata(youtube_url)

@pytest.mark.asyncio
async def test_download_youtube_to_mp3(youtube_url,logger):
    await download_youtube_to_mp3(youtube_url,logger=logger)