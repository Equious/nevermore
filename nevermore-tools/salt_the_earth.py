import os

def delete_files(root_dir, target_filename):
    """
    Traverse a directory and delete any file named target_filename.
    
    Args:
        root_dir (str): The root directory to start traversal.
        target_filename (str): The name of the file to delete.
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file == target_filename or file.endswith(".mp4"):
                file_path = os.path.join(dirpath, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

if __name__ == "__main__":
    root_directory = [r'/home/equious/Nevermore/courses/formal-verification']

    for root_directory in root_directory:

        delete_files(root_directory, "blank.mp4")
