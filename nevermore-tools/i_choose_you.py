import os

# Walk a directory and rename all .md files to +page.md

def rename_md_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md") and file != "+page.md" and file == "lesson.md":
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, "+page.md")
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {old_path} -> {new_path}")
                except FileExistsError:
                    print(f"File already exists: {new_path}, skipping.")
                except Exception as e:
                    print(f"Error renaming {old_path}: {e}")

# Example usage
directory_to_walk = [r'/home/equious/Nevermore/courses/rocket-pool-reth-integration']  # Replace with the path to your directory

for directory in directory_to_walk:
    rename_md_files(directory)
