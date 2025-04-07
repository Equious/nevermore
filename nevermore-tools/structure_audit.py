import os
import sys
from collections import defaultdict

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    print("Please install moviepy: pip install moviepy")
    sys.exit(1)

def is_video_file(filename):
    return filename.lower().endswith(('.mp4', '.mov'))

def check_directory_structure(course_dir):
    errors = []
    section_numbers = set()
    section_slugs = set()
    for section_name in sorted(os.listdir(course_dir)):
        section_path = os.path.join(course_dir, section_name)
        if not os.path.isdir(section_path):
            continue  # Skip files
        # Check section directory name format {section-number}-{section-slug}
        if '-' not in section_name:
            errors.append(f"Invalid section directory name: {section_name}")
            continue
        section_number, section_slug = section_name.split('-', 1)
        if section_number in section_numbers:
            errors.append(f"Duplicate section number: {section_number} in section {section_name}")
        else:
            section_numbers.add(section_number)
        if section_slug in section_slugs:
            errors.append(f"Duplicate section slug: {section_slug} in section {section_name}")
        else:
            section_slugs.add(section_slug)
        # Now check lessons
        lesson_numbers = set()
        lesson_slugs = set()
        for lesson_name in sorted(os.listdir(section_path)):
            lesson_path = os.path.join(section_path, lesson_name)
            if not os.path.isdir(lesson_path):
                continue  # Skip files
            # Check lesson directory name format {lesson-number}-{lesson-slug}
            if '-' not in lesson_name:
                errors.append(f"Invalid lesson directory name: {lesson_name} in section {section_name}")
                continue
            lesson_number, lesson_slug = lesson_name.split('-', 1)
            if lesson_number in lesson_numbers:
                errors.append(f"Duplicate lesson number: {lesson_number} in section {section_name}")
            else:
                lesson_numbers.add(lesson_number)
            if lesson_slug in lesson_slugs:
                errors.append(f"Duplicate lesson slug: {lesson_slug} in section {section_name}")
            else:
                lesson_slugs.add(lesson_slug)
            # Check for video file
            video_found = False
            for filename in os.listdir(lesson_path):
                file_path = os.path.join(lesson_path, filename)
                if os.path.isfile(file_path) and is_video_file(filename):
                    video_found = True
                    video_path = file_path
                    # Check if video file is valid and duration is normal
                    try:
                        clip = VideoFileClip(video_path)
                        duration = clip.duration
                        if duration < 1:
                            errors.append(f"Video {filename} in {lesson_path} has duration less than 1 second")
                        elif duration > 1800:
                            errors.append(f"Video {filename} in {lesson_path} has duration more than 1 hour")
                        clip.close()
                    except Exception as e:
                        errors.append(f"Error processing video {filename} in {lesson_path}: {e}")
            if not video_found:
                # Check if the lesson directory is empty
                if not os.listdir(lesson_path):
                    errors.append(f"Lesson directory {lesson_path} is empty")
                else:
                    errors.append(f"No valid video file found in lesson {lesson_path}")
    return errors

if __name__ == '__main__':
    if len(sys.argv) > 1:
        course_dir = sys.argv[1]
    else:
        course_dir = '.'
    errors = check_directory_structure(course_dir)
    if errors:
        print("Errors found:")
        for error in errors:
            print(error)
    else:
        print("No errors found. Directory structure is valid.")
