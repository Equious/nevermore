import os
import shutil
import sys

# Hardcoded variables
destination_base = "/home/equious/Nevermore/Generated_Questions"  # Base destination directory
folder_name = "formal-verification"                                          # Name of the subfolder under destination_base
file_name = "+page.md"                                        # File to search for and move
root_directory = "/home/equious/Nevermore/courses/formal-verification"       # Original source directory

# Build the target base directory where files are moved to (or from, in reverse mode)
target_base = os.path.join(destination_base, folder_name)

# Check if the script was run with the "reverse" argument
reverse_mode = len(sys.argv) > 1 and sys.argv[1].lower() == "reverse"

if reverse_mode:
    # Reverse mode: Move files from target_base back to their original locations in root_directory
    print("Running in reverse mode. Moving files back to their original locations.")
    for current_root, dirs, files in os.walk(target_base):
        if file_name in files:
            # Determine the relative folder path with respect to target_base
            relative_folder = os.path.relpath(current_root, target_base)
            # Original folder in the root_directory structure
            original_folder = os.path.join(root_directory, relative_folder)
            if not os.path.exists(original_folder):
                os.makedirs(original_folder)
                print(f"Created original folder: {original_folder}")
            source_file = os.path.join(current_root, file_name)
            destination_file = os.path.join(original_folder, file_name)
            shutil.move(source_file, destination_file)
            print(f"Moved '{source_file}' back to '{destination_file}'")
else:
    # Forward mode: Move files from root_directory to the target_base folder while replicating folder structure
    print("Running in forward mode. Moving files to the generated folder structure.")
    # Create the base target folder if it doesn't exist
    if not os.path.exists(target_base):
        os.makedirs(target_base)
        print(f"Created base folder: {target_base}")
    else:
        print(f"Base folder already exists: {target_base}")

    for current_root, dirs, files in os.walk(root_directory):
        if file_name in files:
            # Determine the relative path from the root_directory
            relative_folder = os.path.relpath(current_root, root_directory)
            # Create the corresponding destination folder inside target_base
            destination_folder = os.path.join(target_base, relative_folder)
            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder)
                print(f"Created folder: {destination_folder}")
            source_file = os.path.join(current_root, file_name)
            destination_file = os.path.join(destination_folder, file_name)
            shutil.move(source_file, destination_file)
            print(f"Moved '{source_file}' to '{destination_file}'")
