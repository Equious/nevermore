import os
import asyncio
import time
from vertexai import init, generative_models
from vertexai.generative_models import GenerativeModel, Part
from google.api_core.exceptions import PermissionDenied
from google.cloud import storage
import click

runtime = time.time()
MAX_RETRIES = 3

# Ensure the environment variable is set
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "gen-lang-client-0225468963-f266d584a284.json"

# Initialize Vertex AI
project_id = "gen-lang-client-0225468963"
location = "us-central1"
init(project=project_id, location=location)

# Define the model 
model = GenerativeModel('gemini-2.5-pro-exp-03-25')

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    print("Uploading file...")
    #Uploads a file to Google Cloud Storage.
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)
    print(f"Context file uploaded gs://{bucket_name}/{destination_blob_name}")
    print("-------------------")
    return f"gs://{bucket_name}/{destination_blob_name}"


# Define the safety settings

safety_config = [
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    generative_models.SafetySetting(
        category=generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]

async def upload_repo_context_files(repo_context_directory, bucket_name, root_directory):
    print("Uploading repo context files...")
    context_list = []
    # Uploads all files in the repo-context directory to Google Cloud Storage.
    for dirpath, dirnames, filenames in os.walk(repo_context_directory):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            relative_path = os.path.relpath(file_path, root_directory).replace("\\", "/")
            file_uri = upload_to_gcs(bucket_name, file_path, relative_path)
            context_list.append(Part.from_uri(file_uri, mime_type="text/plain"))
    return context_list

@click.command()
@click.option('--root_directory', default='', help='The root directory of the course.')
@click.option('--skip_lessons', default=False, help='Skip writing lessons.')
@click.argument('descriptions')
def write_lesson_command(skip_lessons,root_directory, descriptions):
    video_file = asyncio.run(write_lessons(root_directory, descriptions))

async def generate_descriptions(dirpath, video_file):
    print("Generating description...")
    prompt = """
            Act as a technical writer and SEO expert. Use the provided written lesson to write a short description of what's covered. You've been provided some past examples of descriptions. Be creative, they shouldn't all read the same. The general format of the description should be as follows:
            'A(n) {adjective} {subject} to {lesson name} - {2 line summary of what the lesson covers}'
            
            Example:
            'A beginner’s guide to creating a Solidity smart contract using Remix IDE. The lesson covers the basics of setting up a Solidity development environment, including creating a new file, writing the contract, understanding SPDX License Identifier, and compiling the contract.'
            """
    contents = [video_file, prompt]
    response = model.generate_content(contents, safety_settings=safety_config)
    markdown_file_path = os.path.join(dirpath, "description.txt")
    with open(markdown_file_path, 'w') as md_file:
        md_file.write(response.text)
    print(f"Description saved: {markdown_file_path}")

async def write_lessons(root_directory, descriptionsNeeded):
    bucket_name = 'equious-nevermore-bucket'
    lessons_written = 0
    context_list = await upload_repo_context_files(f"{root_directory}/repo-context", bucket_name, root_directory)
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for file in filenames:
            if file.endswith('.mp4') or file.endswith('.mov'):
                
                markdown_file_path = os.path.join(dirpath, "+page.md")
                sup_file_path = os.path.join(dirpath, "+page_supervisor.md")
                
                # Check if +page.md exists
                if os.path.exists(markdown_file_path) or os.path.exists(sup_file_path):
                    print(f"Markdown detected. Skipping {file}.")
                    continue

                # Upload the file to Google Cloud Storage
                file_path = os.path.join(dirpath, file)
                relative_path = os.path.relpath(file_path, root_directory).replace("\\", "/")
                file_uri = upload_to_gcs(bucket_name, file_path, relative_path)

                retry_count = 0
                while retry_count < MAX_RETRIES:
                    try:
                        # Use the Google Cloud Storage URI
                        video_file = Part.from_uri(file_uri, mime_type="video/mp4")
                        if descriptionsNeeded:
                            descriptions = await generate_descriptions(dirpath, video_file)

                        # # Define the prompt
                        prompt = """
                            You are a technical writing system meant to construct written style lessons from video lessons. Using the provided video context, use a step by step approach to write a high quality written lesson which follows the video chronologically. Important guidelines:

                            1. Include ALL significant topics covered
                            2. If something specific such a technique or methodology is mentioned, this is very important to include
                            3. If the video is an introduction to a topic, ensure the written lesson is an introduction as well, DON'T include code from later in the course.
                            4. ALL code should be formatted on new lines as:
                            ```javascript
                            commands
                            ```
                            5. DO NOT include diagrams or images, but absolutely provide code blocks from the lesson.
                            6. ALWAYS format your response in markdown
                            7. DO NOT use H1s
                            8. ONLY output the written lessons
                            9. Use first person plural (we, us) when appropriate
                            10. DO NOT narrate or transcribe the video. The written lesson should illustrate the video content in a written format
                            11. DO NOT deviate from the video content
                            12. ONLY include code being shown or written in the video
                            13. Terminal commands being run must be formatted on new lines as:
                            ```bash
                            commands
                            ```
                            """

                        contents = [video_file]
                        contents.extend(context_list)
                        contents.append(prompt) 
                        # print(contents)                   
                        print("Generating content...")

                        # Generate content using the model
                        response = model.generate_content(contents, safety_settings=safety_config)

                        # Wait 20 seconds
                        await asyncio.sleep(20)
                        # Save the response in a Markdown file
                        markdown_file_path = os.path.join(dirpath, "+page.md")
                        with open(markdown_file_path, 'w',encoding="utf-8") as md_file:
                            md_file.write(response.text)
                        
                        print(f"Markdown file saved: {markdown_file_path}")
                        print("Initial Generation complete.")
                        print("Supervisor check...")
                        sup_path = await supervisorCheck(contents, response.text, markdown_file_path)
                        
                        lessons_written += 1
                        # delete_mp4_files(dirpath)
                        # supported_languages = ["Spanish", "Korean"]
    
                        # for language in supported_languages:
                        #     await translate_lesson(sup_path, language)

                        break  # Exit the retry loop on success
                        
                    
                    except PermissionDenied as e:
                        print("Permission denied error:", e)
                        break  # Exit the retry loop on specific exceptions

                    except Exception as e:
                        retry_count += 1
                        print(f"An error occurred (retry {retry_count}/{MAX_RETRIES}):", e)
                        if retry_count >= MAX_RETRIES:
                            print("Max retries reached. Skipping this file.")
                            break  # Exit the retry loop after max retries
    
        
    print("Lessons written: ", lessons_written)
    print("\n\nTime taken: ", time.time() - runtime)

async def translate_lesson(lesson_path, language):
    # Translate the lesson to a different language
    try:
        with open(lesson_path, 'r') as lesson:
            lesson_text = lesson.read()
            
            contents = []
            contents.append(lesson_text)

            prompt = f"""
                    You are a technical writing system meant to translate written style lessons from English to {language}. Using the provided written lesson, translate the content to the specified language. Ensure the translation is accurate and maintains the original meaning. Do not translate proper nouns, technical terms or variable names.
                    """
            
            contents.append(prompt)
            print(f"Translating content to {language}...")
            response = model.generate_content(contents, safety_settings=safety_config)
            translated_lesson_path = lesson_path.replace("+page_supervisor.md", f"+page_supervisor_{language}.md")
            with open(translated_lesson_path, 'w', encoding="utf-8") as translated_lesson_file:
                translated_lesson_file.write(response.text)
    except Exception as e:
        print(f"Error translating lesson to {language}: {e}")
    

# function to delete the .mp4 in the current directory
def delete_mp4_files(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            if file.endswith('.mp4'):
                file_path = os.path.join(dirpath, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")



async def supervisorCheck(contents, unVettedResponse, markdown_file_path):
    contents.pop()
    contents.append(unVettedResponse)
    contents.append(markdown_file_path)
    supervisorPrompt = """
                        You are a supervisor checking the quality of a written lesson generated by a technical writing system. You are tasked with ensuring the written lesson is high quality and meets certain criteria. Important criteria:

                        1. Include ALL significant topics covered
                        2. If something specific such a technique or methodology is mentioned, this is very important to include
                        3. ALL code should be formatted on new lines as:
                        ```solidity
                        commands
                        ```
                        4. DO NOT include diagrams or images, but absolutely provide code blocks from the lesson.
                        6. ALWAYS format your response in markdown
                        7. DO NOT use H1s
                        8. ONLY output the written lessons
                        9. Use first person plural (we, us) when appropriate
                        10. The written lesson MUST NOT transcribe the video verbatim. The written lesson should illustrate the video content in a written format
                        11. DO NOT deviate from the video content
                        12. Be thorough, don't glaze over details, if a topic is explained in the video, it should be explained in the written lesson.
                        13. Do not introduce code or topics that are not covered in the video
                        14. Terminal commands being run must be formatted on new lines as:
                         ```bash
                         commands
                         ```
                         15. Ensure each written lesson has a title that matches the video content

                        Based on the criteria above, ensure the provided lesson matches what's required. Check the major topics in the written lesson vs the video content. Ensure the lesson is NOT a verbatim transcription of the video, in whole or in part.
                        """

    contents.append(supervisorPrompt)
    # Generate content using the model
    response = model.generate_content(contents, safety_settings=safety_config)

    # Wait 20 seconds
    await asyncio.sleep(20)
    # Save the response in a Markdown file
    markdown_file_path = markdown_file_path.replace("+page.md", "+page_supervisor.md")
    with open(markdown_file_path, 'w', encoding="utf-8") as md_file:
        md_file.write(response.text)
    
    print(f"Supervisor file saved: {markdown_file_path}")
    return markdown_file_path

    

# The following code is for running the script from the command line:

# Set the root directory to your Course directory

course_directory = [r'/home/equious/Nevermore/courses/advanced-foundry/1-How-to-create-an-erc20-crypto-currency']

for directory in course_directory:

    # Run the async function
    lessons_written = asyncio.run(write_lessons(directory, False))

# supported_languages = ["korean"]
# lessons_translated = asyncio.run(translate_lesson(course_directory, supported_languages))
