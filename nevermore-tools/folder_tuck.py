import os
import shutil

# Organize .mov files into folders with the same name as the file (without extension)

def organize_mov_files(directory):
    # Traverse the directory
    for root, _, files in os.walk(directory):
        for file in files:
            # Check if the file is a .mov file
            if file.endswith(".mov"):
                # Get the full path of the file
                file_path = os.path.join(root, file)
                
                # Get the name of the folder to be created (same as the file name without extension)
                folder_name = os.path.splitext(file)[0]
                folder_path = os.path.join(root, folder_name)

                # Create the folder if it doesn't already exist
                if not os.path.exists(folder_path):
                    os.mkdir(folder_path)
                    print(f"Created folder: {folder_path}")
                
                # Move the .mov file into the folder
                new_file_path = os.path.join(folder_path, file)
                shutil.move(file_path, new_file_path)
                print(f"Moved file: {file_path} -> {new_file_path}")

if __name__ == "__main__":
    # Specify the directory to organize
    directory = r"/home/equious/Nevermore/courses/moccasin-101"
    
    if not os.path.exists(directory):
        print(f"Error: The directory '{directory}' does not exist.")
    else:
        organize_mov_files(directory)
        print("Organization complete.")
