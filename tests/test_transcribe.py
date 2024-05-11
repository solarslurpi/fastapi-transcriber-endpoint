import pytest

from logger_code import LoggerBase
from pydantic_models import GlobalState, update_state, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP
from utils import transcribe, build_metadata

@pytest.fixture
def logger():
    logger = LoggerBase.setup_logger('test_batch_transcribing')
    return logger

@pytest.fixture
def setup_global_state():
    g_state = GlobalState
    update_state(youtube_url = "https://www.youtube.com/watch?v=example",
                 mp3_filepath = "/path/to/file.mp3",
                 tags = ["tag1", "tag2"],
                 description = "Sample description",
                 audio_quality = "default",
                 compute_type = "default"
                 )
    return g_state

def test_build_metadata(setup_global_state, logger):
    expected_metadata = (
        '---\n'
        'YouTube URL: https://www.youtube.com/watch?v=example\n'
        'Filename: file\n'
        'Tags: #tag1 #tag2\n'
        'Description: Sample description\n'
        f'Audio Quality: {str(AUDIO_QUALITY_MAP["default"])}\n'
        f'Compute Type: {str(COMPUTE_TYPE_MAP["default"])}\n'
        '---\n\n'
    )
    logger.debug(f"Expected metadata: {expected_metadata}")
    # Assign the mock global_state to where it will be accessed in the function
    global global_state
    global_state = setup_global_state
    result = build_metadata()  # Call the function to generate metadata
    logger.debug(f"Result: {result}")
    assert result == expected_metadata

@pytest.mark.asyncio
async def test_transcribe_with_actual_processing(logger):

    # Define a real MP3 file path and expected transcript
    test_audio_file = "./Bluelab_Pulse_Meter_Review.mp3"
    expected_transcription = "expected transcription output"

    # Run the actual transcription function
    transcription_result = await transcribe(test_audio_file, 'default', 'default', logger)
    logger.debug(f"--------------------------\nFirst 100 chars of the transcript:\n{transcription_result[:100]}\n-------------------------------")
    # Assert the transcription is as expected
    assert len(transcription_result) > 50 # Assume a transcription has greater than 50 characters
