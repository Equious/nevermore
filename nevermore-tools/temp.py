import os
import json
import sys

def find_empty_questions_json(root_dir):
    """
    Walks through root_dir and collects paths of every 'questions.json' file
    that is considered empty.
    
    A questions.json file is considered empty if:
    - The file size is 0 bytes, or
    - The JSON content is an empty list or an empty dict.
    
    Args:
        root_dir (str): The root directory to start the search.
        
    Returns:
        list: A list of file paths for questions.json files that are empty.
    """
    empty_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file == 'questions.json':
                file_path = os.path.join(dirpath, file)
                try:
                    # Check file size first.
                    if os.path.getsize(file_path) == 0:
                        empty_files.append(file_path)
                        continue
                    
                    # Attempt to load JSON content.
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    # Consider the file empty if its content is an empty list or dict.
                    if (isinstance(content, list) and len(content) == 0) or \
                       (isinstance(content, dict) and len(content) == 0):
                        empty_files.append(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    return empty_files

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python find_empty_questions_json.py <root_directory>")
        sys.exit(1)
    
    root_directory = sys.argv[1]
    empty_files = find_empty_questions_json(root_directory)
    
    if empty_files:
        print("Empty questions.json files found:")
        for file_path in empty_files:
            print(file_path)
    else:
        print("No empty questions.json files found.")
