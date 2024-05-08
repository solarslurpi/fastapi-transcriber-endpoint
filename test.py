import os

def check_files_for_quotes():
    # Get the current directory's contents
    files = os.listdir('.')

    # Initialize a flag to track if files with quotes are found
    found_files_with_quotes = False
    for char in 'Episode 131： IPM and Beneficial Nematodes with Julie Graesch.mp3':
        print(f"'{char}': {ord(char)}")
    # Check each file in the directory
    for file in files:
        if "Episode" in file:
            print(file)

            print(os.path.exists(file))
            print(os.path.exists('Episode 131： IPM and Beneficial Nematodes with Julie Graesch.mp3'))
        if "'" in file:
            print(f"File with single quotes found: {file}")
            found_files_with_quotes = True

    # If no files with quotes were found, print a message
    if not found_files_with_quotes:
        print("No files with single quotes in their names were found in the current directory.")

# Run the function
check_files_for_quotes()
