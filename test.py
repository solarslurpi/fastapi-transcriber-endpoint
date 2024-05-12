import torch

from pydub import AudioSegment
from transformers import pipeline

# Define a function to slice audio
def slice_audio(audio_path, start_ms, end_ms):
    audio = AudioSegment.from_file(audio_path)
    return audio[start_ms:end_ms]

# Define a function to transcribe audio
def transcribe_audio(audio_segment, model_name="openai/whisper-tiny.en"):
    # Load model
    transcriber = pipeline("automatic-speech-recognition",
                           model=model_name,
                           device=0 if torch.cuda.is_available() else -1,torch_dtype=torch.float16)
    # Export the audio segment to a format compatible with the Whisper model
    audio_segment.export("temp.wav", format="wav")
    # # Transcribe
    result = transcriber("temp.wav")
    return result['text']

# Main function to process chapters and write to a Markdown file
def process_chapters(chapters, audio_path, output_file):
    with open(output_file, "w") as md_file:
        for chapter in chapters:
            # Convert start and end times from seconds to milliseconds
            start_ms = int(chapter['start_time'] * 1000)
            end_ms = int(chapter['end_time'] * 1000)
            # Slice the audio
            audio_segment = slice_audio(audio_path, start_ms, end_ms)
            # Transcribe the audio segment
            transcription = transcribe_audio(audio_segment)
            # Write to Markdown file
            md_file.write(f"## {chapter['title']}\n\n{transcription}\n\n")

# Example usage
chapters = [
    {'start_time': 0.0, 'title': 'Intro', 'end_time': 15.0},
    {'start_time': 15.0, 'title': 'Features', 'end_time': 66.0},
    {'start_time': 66.0, 'title': 'Soil EC', 'end_time': 148.0},
    {'start_time': 148.0, 'title': 'Pulse App', 'end_time': 301.0},
    {'start_time': 301.0, 'title': 'Conclusion', 'end_time': 318.0}
]
audio_path = "Bluelab_Pulse_Meter_Review.mp3"
output_file = "output.md"
process_chapters(chapters, audio_path, output_file)
