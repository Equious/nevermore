import os

# Walk a directory and delete all files with a given extension

def delete_md_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".mp4") or file.endswith(".mov"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

if __name__ == "__main__":
    directory_to_clean = r"/home/equious/Nevermore/courses/reth-integration"
    if os.path.isdir(directory_to_clean):
        delete_md_files(directory_to_clean)
    else:
        print("Invalid directory. Please provide a valid directory path.")
