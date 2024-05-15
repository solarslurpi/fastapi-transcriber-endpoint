import asyncio
import time

from pydub import AudioSegment
import torch
import yaml
from transformers import pipeline


from logger_code import LoggerBase
from pydantic_models import mp3_file_ready_event, transcript_ready_event, global_state, AUDIO_QUALITY_MAP, COMPUTE_TYPE_MAP

async def transcribe_mp3(mp3_filepath: str, logger: LoggerBase):

    await mp3_file_ready_event.wait()
    # Why not just pass these in? Because of the way this background task uses an event to start the code actually going.
    mp3_filepath = global_state.mp3_filepath
    whisper_model = AUDIO_QUALITY_MAP.get(global_state.audio_quality, "distil-whisper/distil-large-v3") # Get hf model name from simple name.
    torch_compute_type = COMPUTE_TYPE_MAP.get(global_state.compute_type) # get torch.dtype from simple name.
    logger.debug(f"Transcribing file path: {mp3_filepath}")
    chapters = global_state.chapters
    transcription_time = 0
    if chapters is not None:
        logger.debug(f"Number of chapters: {len(chapters)}")
    # We have one last thing to add to the transcript. How long it took.  We'll add this to the frontmatter.
    if chapters is not None and len(chapters) > 0:
        start_time = time.time()
        transcription_text = process_chapters(chapters, logger, mp3_filepath, whisper_model, torch_compute_type)
        end_time = time.time()
        transcription_time = end_time - start_time
    else:
        start_time = time.time()
        transcription_text = await transcribe(mp3_filepath, logger, whisper_model, torch_compute_type, )
        end_time = time.time()
        transcription_time = end_time - start_time

    # Combine the frontmatter list back into a single string
    data = yaml.safe_load(global_state.yaml_metadata)
    data['transcription time'] = round(transcription_time, 1)
    # convert the yaml to a string representation.
    data_str = yaml.dump(data)
    startstop = "---\n"
    obsidian_yaml = startstop + data_str + startstop
    # Combine metadata with transcription text

    total_transcript = obsidian_yaml + transcription_text
    global_state.update(transcript_text = total_transcript)
    transcript_ready_event.set()

def insert_before_last_line(text, text_line_to_insert):
    last_delimiter_index = -1
    lines = text.split('\n')
    # find the end of yaml.
    for i, line in enumerate(lines):
        if line.strip() == '---':
            last_delimiter_index = i

    lines.insert(last_delimiter_index - 1, text_line_to_insert)
    modified_text = '\n'.join(lines)
    return modified_text

# Define a function to slice audio
def slice_audio(mp3_filepath, start_ms, end_ms):
    audio = AudioSegment.from_file(mp3_filepath)
    return audio[start_ms:end_ms]


def transcribe_chapter(audio_segment: AudioSegment, hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16) -> str:
    # Load model
    transcriber = pipeline("automatic-speech-recognition",
                           model=hf_model_name,
                           device=0 if torch.cuda.is_available() else -1,torch_dtype=compute_type_pytorch)
    # Export the audio segment to a format compatible with the Whisper model
    audio_segment.export("temp.wav", format="wav")
    # # Transcribe
    result = transcriber("temp.wav", chunk_length_s=30, batch_size=8)
    return result['text']

def process_chapters(chapters:list,logger:LoggerBase, mp3_filepath:str , hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16):
    chapters_text = ''
    for chapter in chapters:
        logger.debug(f'processing chapter {chapter}')
        # Convert start and end times from seconds to milliseconds
        start_ms = int(chapter['start_time'] * 1000)
        end_ms = int(chapter['end_time'] * 1000)
        # Slice the audio
        audio_segment = slice_audio(mp3_filepath, start_ms, end_ms)
        # Transcribe the audio segment
        transcription = transcribe_chapter(audio_segment, hf_model_name=hf_model_name, compute_type_pytorch=compute_type_pytorch)
        # Write to Markdown file
        start_time_str = time.strftime('%H:%M:%S', time.gmtime(chapter['start_time']))
        chapters_text += f"## {chapter['title']}\n"
        chapters_text += f"{start_time_str}\n"
        chapters_text += f"{transcription}\n"


    return chapters_text



async def transcribe(mp3_filename: str, logger:LoggerBase, hf_model_name: str="distil-whisper/distil-large-v3", compute_type_pytorch: torch.dtype=torch.float16) -> str:
    logger.debug(f"Starting transcription with model: {hf_model_name} and compute type: {compute_type_pytorch}")
    # Get the transcript
    transcription_text = await _transcribe_pipeline(mp3_filename, logger, hf_model_name, compute_type_pytorch )

    return transcription_text

async def _transcribe_pipeline(mp3_filename: str, logger:LoggerBase, model_name: str, compute_float_type: torch.dtype ) -> str:
    logger.debug(f"Transcribe using HF's Transformer pipeline (_transcribe_pipeline)...LOADING MODEL {model_name} using compute type {compute_float_type}")
    def load_and_run_pipeline():
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1,
            torch_dtype=compute_float_type
        )
        return pipe(mp3_filename, chunk_length_s=30, batch_size=8, return_timestamps=False)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, load_and_run_pipeline)
    return result['text']

# if __name__ == "__main__":
#     logger = LoggerBase.setup_logger('HF_whisper')
#     text = asyncio.run(transcribe(mp3_filename='Bluelab_Pulse_Meter_Review.mp3', logger=logger))
#     logger.debug(f"Transcription text: {text}")
