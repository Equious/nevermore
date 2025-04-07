import os
import json

def count_json_objects_in_file(file_path):
    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
            # Check if the data is a list, then count the objects
            if isinstance(data, list):
                return len(data)
            else:
                # If not a list, count it as 1 object
                return 1
        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {file_path}")
            return 0

def count_json_objects_in_directory(directory):
    total_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if "assessment" in file:
                continue
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                count = count_json_objects_in_file(file_path)
                print(f"{file}: {count} objects")
                total_count += count
    return total_count

if __name__ == "__main__":
    directory = r"../Generated_Questions/Vyper Basics"
    total_json_objects = count_json_objects_in_directory(directory)
    print(f"Total JSON objects in directory: {total_json_objects}")
