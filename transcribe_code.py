
import os
import time

from mutagen.mp3 import MP3
from typing import Union
from pydub import AudioSegment
import torch
import yaml
from transformers import pipeline


from logger_code import LoggerBase
from pydantic_models import  global_state, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP
from utils import build_yaml_metadata

async def transcribe_mp3(mp3_filepath: str, logger: LoggerBase):
    whisper_model = AUDIO_QUALITY_MAP.get(global_state.audio_quality, "distil-whisper/distil-large-v3")
    torch_compute_type = COMPUTE_TYPE_MAP.get(global_state.compute_type)
    logger.debug(f"Transcribing file path: {mp3_filepath}")
    # If there are no chapters, it means the audio either didn't originate from YouTube or the YouTube metadata did not break the video into chapters.
    if not global_state.chapters:
        chapter = {}
        chapter['start_time'] = 0.0
        chapter['end_time'] = 0.0
        chapter['title'] = ''
        chapters = [chapter]
        global_state.update(chapters=chapters)
    else:
        chapters = global_state.chapters
        transcription_time = 0

    # Let the user know that the transcription will be transcribing by chapters.
    yield {'status': f'Transcribing {len(chapters)} chapter(s).'}
    yield {'num_chapters': len(chapters)}
    logger.debug(f"Number of chapters: {len(chapters)}")

    transcription_text = ''
    start_time = time.time()
    # Transcribed chapters are sent to Obsidian as they become available.
    async for event in transcribe_chapters(chapters, logger, mp3_filepath, whisper_model, torch_compute_type):
        yield event
        if 'transcript_part' in event:
            transcription_text += event['transcript_part']
    end_time = time.time()
    transcription_time = end_time - start_time

    if not global_state.yaml_metadata: # In the case of Uploading an mp3 file.
        filename = os.path.basename(mp3_filepath) if global_state.mp3_filepath else ''
        audio = MP3(mp3_filepath)
        duration = audio.info.length
        mp3_metadata = {
            "webpage_url": '',
            "filename": f'{filename}',
            "tags": [],
            "description": '',
            "duration": duration,
            "channel": '',
            "upload_date": '',
            "uploader_id": '',
        }
        global_state.update(yaml_metadata=build_yaml_metadata(mp3_filepath, mp3_metadata) )

    data = yaml.safe_load(global_state.yaml_metadata)
    data['transcription time'] = round(transcription_time, 1)
    data_str = yaml.dump(data)
    startstop = "---\n"
    frontmatter = startstop + data_str + startstop
    yield {'frontmatter': frontmatter}
    global_state.update(frontmatter=frontmatter)


# Define a function to slice audio
def slice_audio(mp3_filepath, start_ms, end_ms):
    audio = AudioSegment.from_file(mp3_filepath)
    return audio[start_ms:end_ms]


def transcribe_chapter(audio_in: Union[str, AudioSegment], hf_model_name: str = "distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype = torch.float16) -> str:
    # Load model
    transcriber = pipeline("automatic-speech-recognition",
                           model=hf_model_name,
                           device=0 if torch.cuda.is_available() else -1,
                           torch_dtype=compute_type_pytorch)

    # Prepare the audio file path
    if isinstance(audio_in, AudioSegment):
        # Export the AudioSegment to a temporary WAV file
        audio_in.export("temp.wav", format="wav")
        audio_path = "temp.wav"
    else:
        audio_path = audio_in

    # Transcribe
    result = transcriber(audio_path, chunk_length_s=30, batch_size=8)

    return result['text']

async def transcribe_chapters(chapters: list, logger: LoggerBase, mp3_filepath: str, hf_model_name: str = "distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype = torch.float16):
    chapters_text = ''
    for chapter in chapters:
        logger.debug(f'processing chapter {chapter}')
        # The end_time = 0 if the chapter did not come from YouTube metadata.
        if int(chapter['end_time']) > 0.0:
            # Convert start and end times from seconds to milliseconds
            start_ms = int(chapter['start_time'] * 1000)
            end_ms = int(chapter['end_time'] * 1000)
            # Slice the audio
            audio_segment = slice_audio(mp3_filepath, start_ms, end_ms)
        else:
            audio_segment = mp3_filepath
        # Transcribe the audio segment
        transcription = transcribe_chapter(audio_segment, hf_model_name=hf_model_name, compute_type_pytorch=compute_type_pytorch)
        # Write to Markdown file

        transcription_chapter= f"## {chapter['title']}\n"
        if chapter['end_time'] > 0.0:
            start_time_str = time.strftime('%H:%M:%S', time.gmtime(chapter['start_time']))
            end_time_str = time.strftime('%H:%M:%S', time.gmtime(chapter['end_time']))
            transcription_chapter += f"{start_time_str} - {end_time_str}\n"
        transcription_chapter += f"{transcription}\n"
        chapters_text += transcription_chapter

        # Yield progress event for each chapter
        yield {'chapter': transcription_chapter}

# async def transcribe(mp3_filename: str, logger:LoggerBase, hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16) -> str:
#     logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")
#     # Get the transcript
#     transcription_text = await _transcribe_pipeline(mp3_filename, logger, hf_model_name, compute_type_pytorch )

#     return transcription_text

# async def _transcribe_pipeline(mp3_filename: str, logger:LoggerBase, model_name: str, compute_float_type: torch.dtype ) -> str:
#     logger.debug(f"Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL {model_name} using compute type {compute_float_type}")
#     def load_and_run_pipeline():
#         pipe = pipeline(
#             "automatic-speech-recognition",
#             model=model_name,
#             device=0 if torch.cuda.is_available() else -1,
#             torch_dtype=compute_float_type
#         )
#         return pipe(mp3_filename, chunk_length_s=30, batch_size=8, return_timestamps=False)
#     loop = asyncio.get_running_loop()
#     result = await loop.run_in_executor(None, load_and_run_pipeline)
#     return result['text']

# if __name__ == "__main__":
#     logger = LoggerBase.setup_logger('HF_whisper')
#     text = asyncio.run(transcribe(mp3_filename='Bluelab_Pulse_Meter_Review.mp3', logger=logger))
#     logger.debug(f"Transcription text: {text}")
