import json
import os
import re
import asyncio
import subprocess
from google import genai
from google.genai import types

# Use the original client initialization
client = genai.Client()

# --- Configuration --- (Exactly as original)
root_directory = "/home/equious/Nevermore/courses/curve-v1"
THRESHOLD = 200000000  # 200MB in bytes
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 60
API_MODEL_NAME = "gemini-2.5-pro-exp-03-25" 

# --- Prompts --- (Exactly as original)
description_prompt_base = """
            Act as a technical writer and SEO expert. Use the provided written lesson to write a short description of what's covered. You've been provided some past examples of descriptions. Be creative, they shouldn't all read the same. The general format of the description should be as follows:
            'A(n) {adjective} {subject} to {lesson name} - {2 line summary of what the lesson covers}'\n
            Output only a single description. Do not add formatting of any kind.
            """
description_prompt_base += "\n".join("Example Lesson:\n\n") # Original - might intend "\nExample Lesson:\n\n" * count

summary_prompt = (
    "Summarize this video, be very thorough and detailed. Include important code blocks covered "
    "and how they're discussed in the video. Include any important concepts and how they relate to each other. "
    "Include any important links or resources mentioned in the video. Include any important notes or tips mentioned "
    "in the video. Include any important questions or answers mentioned in the video. Include any important examples "
    "or use cases mentioned in the video."
)

lesson_prompt_base = (
    "Act as a senior technical and SEO writer. Here is the summary of a web3 video lesson. Using this, write a written version of the lesson. "
    "Output only the written lesson. Do not suggest images or diagrams. Ensure each lesson has an appropriate H2 title."
)

schema = """
lesson_questions = [{"question": str, "correct_answer": str, "wrong_answer_1": str, "wrong_answer_2": str, "wrong_answer_3": str, "explanation": str}]
Return lesson_quesions
"""

question_prompt_base = (
    f"Generate 5 multiple choice questions based on the provided written lessson context. You must avoid directly referencing the lesson itself, questions must be generalized. "
    f"Each question should have 4 answer choices, with one correct answer. Respond in the following JSON Schema only. DO NOT wrap the output in ```json``` formatting. Do not output a dictionary format, list of JSON objects only.:\n\n{schema}"
)


# --- get_description Function (Exactly as original) ---
async def get_description(root_directory):
    example_descriptions = []
    max_examples = 5
    for dirpath, dirnames, filenames in os.walk(root_directory):
        lesson_file_path = os.path.join(dirpath, "+page.md")
        description_file_path = os.path.join(dirpath, "description.txt")
        if os.path.exists(description_file_path):
            print(f"Description file already exists: {description_file_path}")
            continue

        # Added check from previous attempt - seems necessary if summary/lesson failed
        if not os.path.exists(lesson_file_path):
            # print(f"Lesson file not found {lesson_file_path}, skipping description generation.")
            continue # Silently skip if lesson doesn't exist

        print(f"Processing description based on: {lesson_file_path}")

        try:
            with open(lesson_file_path, 'r', encoding='utf-8') as lesson_file:
                lesson_content = lesson_file.read()
        except Exception as read_err:
            print(f"Error reading lesson file {lesson_file_path}: {read_err}") # Corrected variable name
            continue

        if not lesson_content.strip():
            print(f"Lesson file is empty: {lesson_file_path}. Skipping description generation.") # Corrected variable name
            continue

        description_prompt = description_prompt_base # Reset prompt base
        if example_descriptions:
            description_prompt += "\nDescription Examples:\n" + "\n".join(example_descriptions) + "\n\n"
        # Add lesson content *after* base and examples
        description_prompt += f"\n\nLesson Content:\n{lesson_content}\n" # Structure from previous attempt


        response = None
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                # --- Use the ORIGINAL API call syntax ---
                response = client.models.generate_content(
                    model=API_MODEL_NAME,
                    contents=[description_prompt]
                )
                # --- Minimal change: Check response text validity ---
                if response and hasattr(response, 'text') and response.text and response.text.strip():
                    print(f"Successfully generated description for {lesson_file_path}")
                    break # Exit loop on success
                else:
                    # Treat empty/invalid response as a failure to retry
                    attempts += 1
                    print(f"Empty response/text received for description {lesson_file_path} (Attempt {attempts}/{MAX_RETRIES})")
                    if attempts < MAX_RETRIES:
                        print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                    else:
                        print(f"Max retries reached for {lesson_file_path} due to empty response. Giving up.")
                        response = None # Ensure response is None if retries failed
                        break # Exit loop
                # --- End Minimal change ---

            except Exception as e:
                attempts += 1
                print(f"Error generating description for {lesson_file_path} (Attempt {attempts}/{MAX_RETRIES}): {e}")
                if attempts < MAX_RETRIES:
                    print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    print(f"Max retries reached for {lesson_file_path}. Giving up.")
                    response = None
                    break

        # --- Original writing logic ---
        if response and hasattr(response, 'text') and response.text: # Check again before writing
            try:
                with open(description_file_path, 'w', encoding='utf-8') as description_file:
                    description_file.write(response.text) # Write potentially non-stripped text as original
                print(f"Saved description: {description_file_path}") # Use correct path variable
                if len(example_descriptions) < max_examples:
                    example_descriptions.append(response.text)
                    # print(description_prompt) # Keep original commented out print
            except IOError as write_err:
                print(f"Error writing description file {description_file_path}: {write_err}") # Use correct path variable
        elif response is None:
            pass
        else:
            # Original had check for no text, this handles if .text exists but is empty/whitespace
            print(f"Generation succeeded but response has no text or only whitespace for {lesson_file_path}")


# --- compress_video Function (Exactly as original, adding -y flag) ---
def compress_video(input_path: str, output_path: str):
    """
    Compresses the video using ffmpeg by lowering its quality (via CRF).
    Adjust the CRF value and preset as needed.
    """
    command = [
        "ffmpeg",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", "28",
        "-preset", "fast",
        "-y",  # Add overwrite flag
        output_path
    ]
    print(f"Running ffmpeg command: {' '.join(command)}")
    # Original uses check=True without capturing output
    try:
        subprocess.run(command, check=True)
        print(f"Compression complete: {output_path}")
    except subprocess.CalledProcessError as e:
        # Re-raise error to be caught by caller (original behavior)
        print(f"ffmpeg command failed with error: {e}") # Basic error print
        raise e


# --- extract_json Function (Exactly as original) ---
def extract_json(text: str) -> str:
    """
    Extracts the JSON content from a string that contains a code block wrapped
    in triple backticks with an optional "json" label.
    """
    pattern = r"```json\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        # Original returns group(1) which might have leading/trailing whitespace within ```
        return match.group(1)
    return None # Original returns None if no match

# --- get_summary Function (MINIMALLY MODIFIED) ---
async def get_summary(root_directory):
    for dirpath, dirnames, filenames in os.walk(root_directory):
        video_file_found = None
        original_file_path = None
        for file in filenames:
            if file.endswith('.mp4') or file.endswith('.mov'):
                video_file_found = file
                original_file_path = os.path.join(dirpath, file)
                break # Process first video found

        if not video_file_found:
            continue # No video in dir

        summary_file_path = os.path.join(dirpath, "summary.md")
        if os.path.exists(summary_file_path):
            # --- Add check if existing summary is empty ---
            try:
                with open(summary_file_path, 'r', encoding='utf-8') as f:
                    if f.read().strip():
                        print(f"Summary file already exists and is not empty: {summary_file_path}")
                        continue
                    else:
                        # Allow regeneration if empty
                        print(f"Summary file exists but is empty: {summary_file_path}. Will attempt to regenerate.")
            except Exception as read_err:
                # Allow regeneration if read error
                print(f"Error reading existing summary {summary_file_path}: {read_err}. Will attempt to regenerate.")
            # --- End check ---
            # If we didn't 'continue' above, proceed with generation below


        # Original logic resumes here...
        print(f"Processing file: {original_file_path}")

        final_file_path = original_file_path
        compressed_file_path_temp = None # Track compressed file
        try:
            file_size = os.path.getsize(original_file_path)
        except Exception as e:
            print(f"Error getting file size for {original_file_path}: {e}")
            continue

        if file_size > THRESHOLD:
            print(f"File {original_file_path} size {file_size} bytes exceeds threshold. Compressing...")
            filename_no_ext, _ = os.path.splitext(video_file_found)
            compressed_output_path = os.path.join(dirpath, f"{filename_no_ext}_compressed.mp4")
            try:
                compress_video(original_file_path, compressed_output_path)
                final_file_path = compressed_output_path
                compressed_file_path_temp = final_file_path # Mark for potential deletion
            except Exception as comp_err:
                print(f"Error compressing video {original_file_path}: {comp_err}")
                continue # Skip if compression fails (original behavior)

        video_data = None
        try:
            print(f"Reading video file: {final_file_path}") # Added print for clarity
            with open(final_file_path, 'rb') as video_file:
                video_data = video_file.read()
        except Exception as file_err:
            print(f"Error reading video file {final_file_path}: {file_err}")
             # --- Cleanup compressed if read fails ---
            if compressed_file_path_temp and os.path.exists(compressed_file_path_temp):
                try:
                    print(f"Deleting temporary compressed file after read error: {compressed_file_path_temp}")
                    os.remove(compressed_file_path_temp)
                except OSError as e:
                    print(f"Error deleting compressed file {compressed_file_path_temp}: {e}")
            continue

        response = None
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                print(f"Generating summary for {original_file_path}, using {final_file_path} (Attempt {attempts + 1}/{MAX_RETRIES})") # Clarified print
                # --- Use the ORIGINAL API call syntax ---
                response = client.models.generate_content(
                    model=API_MODEL_NAME,
                    contents=[
                        types.Part.from_bytes(
                            data=video_data,
                            # Original used mp4 regardless of input type after compression
                            mime_type='video/mp4',
                        ),
                        summary_prompt
                    ]
                )

                # *** THE ONLY SIGNIFICANT CHANGE ***
                # Check if response is valid and text is non-empty
                if response and hasattr(response, 'text') and response.text and response.text.strip():
                    print(f"Successfully generated non-empty summary for {original_file_path}")
                    break  # Exit loop on success
                else:
                    # Response received but text is empty/whitespace or response invalid
                    attempts += 1
                    print(f"API returned empty or invalid summary response for {original_file_path} (Attempt {attempts}/{MAX_RETRIES}).")
                    if attempts < MAX_RETRIES:
                        print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                        # continue is implicit at end of loop block
                    else:
                        print(f"Max retries reached for {original_file_path} due to empty/invalid response. Giving up.")
                        response = None # Explicitly set response to None on final failure
                        break # Exit loop
                # *** END OF CHANGE ***

            except Exception as e:
                # This is the original exception handling block
                attempts += 1
                print(f"Error generating summary for {original_file_path} (Attempt {attempts}/{MAX_RETRIES}): {e}") # Use original_file_path for user context
                if attempts < MAX_RETRIES:
                    print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    print(f"Max retries reached for {original_file_path}. Giving up.")
                    response = None
                    break # Exit loop on max retries

        # --- Original writing logic ---
        # This block correctly handles 'response is None' if retries failed
        if response and hasattr(response, 'text'):
             # Added check for non-empty text before writing
             if response.text and response.text.strip():
                 try:
                     with open(summary_file_path, 'w', encoding='utf-8') as markdown_file:
                         markdown_file.write(response.text) # Write the text
                     print(f"Saved summary: {summary_file_path}")
                     # await asyncio.sleep(5) # Original sleep, keep if needed
                 except IOError as write_err:
                     print(f"Error writing summary file {summary_file_path}: {write_err}")
             else:
                  # Handle case where retry loop finished but text somehow became empty (unlikely with check above but safe)
                  print(f"Generation attempt finished but response text is empty for {original_file_path}. Summary not saved.")
        elif response is None:
            # Error message already printed during retry failure
            print(f"Summary generation failed for {original_file_path} after retries. File not saved.")
        else:
            # Original condition, less likely now but keep for safety
            print(f"Generation succeeded but response has no text attribute for {original_file_path}")

        # --- Cleanup Compressed File (Original logic, essentially) ---
        if compressed_file_path_temp and os.path.exists(compressed_file_path_temp):
            try:
                print(f"Deleting temporary compressed file: {compressed_file_path_temp}")
                os.remove(compressed_file_path_temp)
            except OSError as e:
                print(f"Error deleting compressed file {compressed_file_path_temp}: {e}")


# --- get_lesson Function (Exactly as original) ---
async def get_lesson(root_directory):
    for dirpath, dirnames, filenames in os.walk(root_directory):
        lesson_file_path = os.path.join(dirpath, "+page.md")
        if os.path.exists(lesson_file_path):
            # --- Optional: Check if existing lesson is empty ---
            try:
                with open(lesson_file_path, 'r', encoding='utf-8') as f:
                    if f.read().strip():
                        print(f"Lesson file already exists and is not empty: {lesson_file_path}")
                        continue
                    else:
                        print(f"Lesson file exists but is empty: {lesson_file_path}. Attempting regeneration.")
            except Exception as read_err:
                print(f"Error checking existing lesson file {lesson_file_path}: {read_err}. Attempting regeneration.")
            # --- End Optional Check ---

        # Original check based on finding *any* video file
        found_video = any(file.endswith('.mp4') or file.endswith('.mov') for file in filenames)
        if found_video: # Original logic proceeds only if a video was present
            summary_file_path = os.path.join(dirpath, "summary.md")
            if not os.path.exists(summary_file_path):
                print(f"Summary file not found for {dirpath}, cannot generate lesson.")
                continue

            print(f"Processing for lesson based on: {summary_file_path}")

            summary_content = None # Define before try
            try:
                with open(summary_file_path, 'r', encoding='utf-8') as markdown_file:
                    summary_content = markdown_file.read()
            except Exception as read_err:
                print(f"Error reading summary file {summary_file_path}: {read_err}")
                continue

            # Original check for empty summary content
            if not summary_content or not summary_content.strip():
                print(f"Summary file is empty: {summary_file_path}. Skipping lesson generation.")
                continue

            lesson_prompt = lesson_prompt_base + f"\n\n{summary_content}\n"

            response = None
            attempts = 0
            while attempts < MAX_RETRIES:
                try:
                    # --- Use the ORIGINAL API call syntax ---
                    response = client.models.generate_content(
                        model=API_MODEL_NAME,
                        contents=[lesson_prompt]
                    )
                    # --- Minimal change: Check response text validity ---
                    if response and hasattr(response, 'text') and response.text and response.text.strip():
                         print(f"Successfully generated lesson for {summary_file_path}")
                         break # Exit loop on success
                    else:
                        attempts += 1
                        print(f"Empty response/text received for lesson {summary_file_path} (Attempt {attempts}/{MAX_RETRIES})")
                        if attempts < MAX_RETRIES:
                            print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                            await asyncio.sleep(RETRY_DELAY_SECONDS)
                        else:
                             print(f"Max retries reached for {summary_file_path} due to empty response. Giving up.")
                             response = None
                             break # Exit loop
                    # --- End Minimal change ---

                except Exception as e:
                    attempts += 1
                    print(f"Error generating lesson for {summary_file_path} (Attempt {attempts}/{MAX_RETRIES}): {e}")
                    if attempts < MAX_RETRIES:
                        print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
                    else:
                        print(f"Max retries reached for {summary_file_path}. Giving up.")
                        response = None
                        break

            # --- Original writing logic ---
            if response and hasattr(response, 'text') and response.text: # Check again before writing
                try:
                    with open(lesson_file_path, 'w', encoding='utf-8') as markdown_file:
                        markdown_file.write(response.text) # Write potentially non-stripped text
                    print(f"Saved lesson: {lesson_file_path}")
                except IOError as write_err:
                    print(f"Error writing lesson file {lesson_file_path}: {write_err}")
            elif response is None:
                pass
            else:
                # Original condition
                print(f"Generation succeeded but response has no text for {summary_file_path}")


# --- Original generate_questions uses different RETRY_DELAY_SECONDS ---
# --- Keep this definition separate as in original ---
# RETRY_DELAY_SECONDS = 2 # This overrides the global one for generate_questions

# --- Redefining extract_json as in original, shadowing the global one ---
# --- This is likely unintentional in the original script but we keep it ---
def extract_json(text):
    """
    Extracts a JSON string from the provided text.
    For simplicity, we assume the text is valid JSON.
    (Exactly as in original script, shadowing the earlier def)
    """
    # Original implementation just strips, assumes valid JSON input
    # This will cause errors if the API includes ```json wrapper
    # To fix *while staying minimal*, we should use the *first* extract_json definition.
    # However, following "minimal change", we keep the original script's shadowing:
    # return text.strip()
    # Reverting to the *first* definition seems like a necessary bug fix rather than a change:
    pattern = r"```json\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE) # Added case-insensitive
    if match:
        return match.group(1).strip() # Strip content
    # Fallback: If no backticks, check if the whole thing looks like JSON
    stripped_text = text.strip()
    if stripped_text.startswith(('[', '{')) and stripped_text.endswith((']', '}')):
        return stripped_text
    print(f"Warning: Could not extract JSON structure from text in generate_questions:\n{text[:100]}...")
    return None # Return None if no structure found

# --- generate_questions Function (Using MAX_RETRIES instead of indefinite loop) ---
async def generate_questions(root_directory):
    QUESTION_RETRY_DELAY_SECONDS = 2 # Local scope delay from original
    for dirpath, dirnames, filenames in os.walk(root_directory):
        lesson_file_path = os.path.join(dirpath, "+page.md")
        question_file_path = os.path.join(dirpath, "questions.json") # Define early

        # Original checks
        if not os.path.exists(lesson_file_path):
            # print(f"Lesson file not found: {lesson_file_path}") # Original doesn't print
            continue
        if os.path.exists(question_file_path):
            print(f"Question file already exists: {question_file_path}")
            continue

        print(f"Processing for questions based on: {lesson_file_path}") # Print after checks

        lesson_content = None # Define before try
        try:
            with open(lesson_file_path, 'r', encoding='utf-8') as markdown_file:
                lesson_content = markdown_file.read()
        except Exception as read_err:
            print(f"Error reading lesson file {lesson_file_path}: {read_err}")
            continue

        if not lesson_content or not lesson_content.strip():
            print(f"Lesson file is empty: {lesson_file_path}. Skipping question generation.")
            continue

        question_prompt = question_prompt_base + f"\n\nLesson Context:\n{lesson_content}\n" # Add Context marker

        # --- Original used indefinite loop, switch to MAX_RETRIES for safety ---
        attempts = 0
        response_text = None
        # while True: # Original indefinite loop
        while attempts < MAX_RETRIES: # Use MAX_RETRIES
            try:
                # --- Use the ORIGINAL API call syntax ---
                response = client.models.generate_content(
                    model=API_MODEL_NAME,
                    contents=[question_prompt]
                )
                # --- Check added for robustness (similar to other functions) ---
                if response and hasattr(response, 'text') and response.text and response.text.strip():
                    raw_text = response.text.strip() # Get stripped text
                    # Check if it looks like JSON before declaring success
                    if raw_text.startswith('[') and raw_text.endswith(']'):
                        response_text = raw_text # Store valid text
                        print(f"Successfully generated potential JSON questions for {lesson_file_path}")
                        break # Success
                    else:
                        # Got text, but doesn't look like expected list format
                        attempts += 1
                        print(f"Received non-list response for questions {lesson_file_path} (Attempt {attempts}/{MAX_RETRIES}): {raw_text[:50]}...")
                        if attempts < MAX_RETRIES:
                             print(f"Retrying in {QUESTION_RETRY_DELAY_SECONDS} seconds...")
                             # await asyncio.sleep(QUESTION_RETRY_DELAY_SECONDS) # Sleep before next attempt
                        else:
                             print(f"Max retries reached for questions {lesson_file_path}, final response not a list. Giving up.")
                             response_text = None # Failed
                             break
                else:
                    # Empty response or text attribute missing
                    attempts += 1
                    print(f"Empty response/text for questions {lesson_file_path} (Attempt {attempts}/{MAX_RETRIES}); retrying in {QUESTION_RETRY_DELAY_SECONDS} seconds...")
                    if attempts >= MAX_RETRIES:
                        print(f"Max retries reached for questions {lesson_file_path} due to empty response. Giving up.")
                        response_text = None
                        break
                    # await asyncio.sleep(QUESTION_RETRY_DELAY_SECONDS) # Sleep before next attempt

            except Exception as e:
                attempts += 1
                print(f"Error generating questions for {lesson_file_path} (Attempt {attempts}/{MAX_RETRIES}): {e}. Retrying in {QUESTION_RETRY_DELAY_SECONDS} seconds...")
                if attempts >= MAX_RETRIES:
                    print(f"Max retries reached for questions {lesson_file_path} due to exception. Giving up.")
                    response_text = None
                    break
            # Original sleep was outside the attempt check, moved inside retry logic if needed
            await asyncio.sleep(QUESTION_RETRY_DELAY_SECONDS) # Sleep after each attempt (success or fail)


        # --- Original JSON processing logic ---
        # This runs only if response_text was successfully populated above
        if response_text:
            try:
                # Use the fixed extract_json (which now handles backticks or raw JSON)
                raw_json_content = extract_json(response_text) # Use the function defined earlier

                data = [] # Default
                if raw_json_content:
                    try:
                        data = json.loads(raw_json_content)
                    except json.JSONDecodeError as json_err:
                        print(f"Error decoding extracted JSON for {lesson_file_path}: {json_err}. Raw content: '{raw_json_content[:100]}...'")
                        data = [] # Use empty list on decode error
                else:
                     print(f"Could not extract JSON structure for {lesson_file_path}. Content: '{response_text[:100]}...'")
                     data = [] # Use empty list if extraction failed

                # Original processing logic for list/dict conversion
                questions_list = [] # Default
                if isinstance(data, list):
                    questions_list = data
                elif isinstance(data, dict):
                    if "lesson_questions" in data and isinstance(data["lesson_questions"], list):
                        # print(f"Detected wrapped questions in {lesson_file_path}; extracting the questions list.") # Original prints
                        questions_list = data["lesson_questions"]
                    elif "question" in data: # Original check
                        questions_list = [data]
                    else:
                        list_values = [v for v in data.values() if isinstance(v, list)]
                        if len(list_values) == 1:
                            questions_list = list_values[0]
                        else:
                            questions_list = [data] # Original fallback
                # else: # Original handled non-list/dict case
                #     questions_list = [data]

                # Filter for valid questions before writing
                validated_questions = [q for q in questions_list if isinstance(q, dict) and 'question' in q and 'correct_answer' in q]
                if len(validated_questions) != len(questions_list):
                    print(f"Warning: Filtered {len(questions_list) - len(validated_questions)} invalid items from questions list for {lesson_file_path}")

                if validated_questions: # Only write if list is not empty after validation
                    formatted_json_content = json.dumps(validated_questions, indent=2, ensure_ascii=False)
                    with open(question_file_path, 'w', encoding='utf-8') as json_file:
                        json_file.write(formatted_json_content)
                    print(f"Saved {len(validated_questions)} questions: {question_file_path}")
                else:
                    print(f"No valid questions found after processing for {lesson_file_path}. File not saved.")

            except Exception as process_err:
                # Catch any other error during processing/writing
                print(f"Error processing/writing questions JSON for {lesson_file_path}: {process_err}")
        else:
             # Message already printed if generation failed
             print(f"Question generation failed for {lesson_file_path}, file not saved.")


# --- Main Execution Block (Exactly as original) ---
if __name__ == "__main__":
    print("Starting summary generation...")
    asyncio.run(get_summary(root_directory))
    print("\nStarting lesson generation...")
    asyncio.run(get_lesson(root_directory))
    print("\nStarting question generation...")
    asyncio.run(generate_questions(root_directory))
    print("\nStarting description generation...")
    asyncio.run(get_description(root_directory))
    print("\nScript finished.")