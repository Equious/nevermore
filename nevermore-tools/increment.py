import os
import sys
import re

# increments the numeric prefix of folders in a directory starting from a given number

def rename_files(start_number, target_directory):
    # Check if the target directory exists
    if not os.path.isdir(target_directory):
        print(f"Error: The directory '{target_directory}' does not exist.")
        sys.exit(1)

    # List all folders (directories) in the target directory
    items = [f for f in os.listdir(target_directory) if os.path.isdir(os.path.join(target_directory, f))]

    # Compile the pattern to match folders starting with a number and a hyphen
    pattern = re.compile(r'^(\d+)-(.*)')

    # Extract items matching the pattern "#-TITLE"
    items_to_rename = []
    for item in items:
        match = pattern.match(item)
        if match:
            number = int(match.group(1))
            title = match.group(2)
            items_to_rename.append((number, title, item))

    # Sort items by their numeric prefix to process them in order
    items_to_rename.sort()

    # Rename items with a numeric prefix >= start_number
    for number, title, original in items_to_rename:
        if number >= start_number:
            new_number = number + 1
            new_name = f"{new_number}-{title}"
            old_path = os.path.join(target_directory, original)
            new_path = os.path.join(target_directory, new_name)
            print(f"Renaming '{old_path}' to '{new_path}'")
            os.rename(old_path, new_path)

if __name__ == "__main__":
    # Check if enough arguments are provided
    if len(sys.argv) < 2:
        print("Usage: python script.py <starting number>")
        sys.exit(1)

    try:
        starting_number = int(sys.argv[1])
    except ValueError:
        print("Error: Starting number must be an integer.")
        sys.exit(1)

    target_directory = r"/home/equious/Nevermore/courses/advanced-foundry/4-cross-chain-rebase-token"

    rename_files(starting_number, target_directory)
