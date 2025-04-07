import os
from moviepy.editor import VideoFileClip

def get_mov_durations(directory):
    total_duration = 0.0
    mov_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.mov'):
                file_path = os.path.join(root, file)
                mov_files.append(file_path)

    for mov_file in mov_files:
        try:
            with VideoFileClip(mov_file) as video:
                duration = video.duration
                total_duration += duration
                print(f"File: {mov_file}, Duration: {duration:.2f} seconds")
        except Exception as e:
            print(f"Error processing file {mov_file}: {e}")

    print(f"\nTotal duration of all .mov files: {total_duration:.2f} seconds")

if __name__ == "__main__":
    directory = r"D:\Downloads\moccasin-101"
    get_mov_durations(directory)
