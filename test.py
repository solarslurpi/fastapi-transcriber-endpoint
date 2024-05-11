import re

import yt_dlp

def download_file(filename,video_id) -> None:
    ydl_opts = {
    'outtmpl' : f'{filename}',
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    }
            # Create a YoutubeDL object with the options
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Construct the URL
        url = f'https://www.youtube.com/watch?v={video_id}'

        # Extract video information
        info_dict = ydl.extract_info(url, download=True)

        # Get the filename
        filename = ydl.prepare_filename(info_dict)


def sanitize_filename(filename: str) -> str:
    # Remove the file extension
    name_part = filename.rsplit('.', 1)[0]
   # Print ASCII/Unicode values of the characters before sanitization
    print("Before sanitization:")
    for char in name_part:
        print(f"'{char}': {ord(char)}")
    # Replace full-width colons and standard colons with a hyphen or other safe character
    name_part = name_part.replace('：', '_').replace(':', '_')
    # Replace unwanted characters with nothing or specific symbols
    # This regex replaces any non-alphanumeric, non-space, and non-dot characters with nothing
    cleaned_name = re.sub(r"[^a-zA-Z0-9 \.-]", "", name_part)
    # Replace spaces with hyphens
    safe_filename = cleaned_name.replace(" ", "_")

    # Print ASCII/Unicode values of the characters after sanitization
    print("After sanitization:")
    for char in safe_filename:
        print(f"'{char}': {ord(char)}")

    return safe_filename

def get_filename(video_id):
    # Configure yt-dlp options
    ydl_opts = {
        'quiet': True,  # Suppress verbose output
        'simulate': True,  # Do not download the video
        'getfilename': True,  # Just print the filename
    }

    # Create a YoutubeDL object with the options
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Construct the URL
        url = f'https://www.youtube.com/watch?v={video_id}'

        # Extract video information
        info_dict = ydl.extract_info(url, download=False)

        # Get the filename
        filename = ydl.prepare_filename(info_dict)
        print("Filename that would be used:", filename)
        return filename

# Usage example
filename = get_filename('w9Ql1sXFqTQ')
sanitized_filename = sanitize_filename(filename)
download_file(sanitized_filename, 'w9Ql1sXFqTQ')

filepath = sanitized_filename + '.mp3'
print(filepath) # Read the contents of the files
