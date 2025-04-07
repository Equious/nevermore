import json
import os
import asyncio
from vertexai import init, generative_models
from vertexai.generative_models import GenerativeModel, Part
from google.api_core.exceptions import PermissionDenied
from google.cloud import storage


# Ensure the environment variable is set
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "../gen-lang-client-0225468963-f266d584a284.json"

# Initialize Vertex AI
project_id = "gen-lang-client-0225468963"
location = "us-central1"
init(project=project_id, location=location)
lesson_name = ""

# Define the model - 1.5 flash needed for video context
model = GenerativeModel('gemini-1.5-flash',
                              # Set the `response_mime_type` to output JSON
                              generation_config={"response_mime_type": "application/json"}, 
                              system_instruction="You are a technical writing system meant to generate questions for end of lesson quizzes. Using the provided context generate 5 multiple choice questions based strictly on the covered content. Questions must be self-contained and not require additional context to be understood. DO NOT directly reference the video, or the code snippets showed in the video.  DO NOT directly mention the lecturer. Questions should be general but based off the video content. Always respond in a list format in the specified JSON schema.")

prompt = f"""
    Generate 5 multiple choice questions for the contained video context. DO NOT reference the video or code from the video directly. Use the video as a source of topics more than specific content""" + """
    Respond using this JSON schema, just return the list itself:
        [{"question": str, "correct_answer": str, "wrong_answer_1": str, "wrong_answer_2": str, "wrong_answer_3": str, "answer_timestamp": str, "explanation": str}]
    """

technical_model = GenerativeModel('gemini-1.5-flash',
                              # Set the `response_mime_type` to output JSON
                              generation_config={"response_mime_type": "application/json"}, 
                              system_instruction="You are a technical writing system meant to generate questions for end of lesson quizzes. Using the provided context generate 3 multiple choice questions based strictly on the covered content. The questions should be technical in nature, requiring reasoning and directly involving code. Questions should contain code or pertain to code snippets in answers. DO NOT directly reference the video.  DO NOT directly mention the lecturer. Questions should be general but based off the video content. Always respond in a list format in the specified JSON schema.")

technical_prompt = f"""
    Generate 3 technical multiple choice coding questions for the contained video context. DO NOT reference the video or code from the video directly. Use the video as a source of topics more than specific content""" + """
    Respond using this JSON schema, just return the list itself:
        [{"question": str, "correct_answer": str, "wrong_answer_1": str, "wrong_answer_2": str, "wrong_answer_3": str, "answer_timestamp": str, "explanation": str}]
    """

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


async def generate(root_directory):
    bucket_name = 'equious-nevermore-bucket'
    global lesson_name
    
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for file in filenames:
            if file.endswith('.mov') or file.endswith('.mp4'):
                # Determine the lesson name and section directory
                lesson_name = os.path.basename(dirpath)
                section_dir = os.path.basename(os.path.dirname(dirpath))

                # Build the path to the expected JSON file
                json_output_path = os.path.join(f'{section_dir}', f'{lesson_name}.json')

                # Check if JSON already exists
                if os.path.exists(json_output_path):
                    print(f"Skipping generation for {file}, JSON already exists at {json_output_path}")
                    continue

                # Upload the file to Google Cloud Storage
                file_path = os.path.join(dirpath, file)
                relative_path = os.path.relpath(file_path, root_directory).replace("\\", "/")
                file_uri = upload_to_gcs(bucket_name, file_path, relative_path)

                retry_count = 0
                MAX_RETRIES = 5
                while retry_count < MAX_RETRIES:
                    try:
                        # Use the Google Cloud Storage URI
                        video_file = Part.from_uri(file_uri, mime_type="video/mp4")

                        contents = [video_file]
                        contents.append(prompt)
                        print("Generating content...")

                        # Generate content using the model
                        response = model.generate_content(contents, safety_settings=safety_config)

                        await asyncio.sleep(5)

                        contents.pop()
                        contents.append(technical_prompt)
                        technical_response = technical_model.generate_content(contents, safety_settings=safety_config)

                        # Wait 20 seconds
                        await asyncio.sleep(15)

                        # Create the section directory if it doesn't exist
                        os.makedirs(f'{section_dir}', exist_ok=True)


                        break

                    except PermissionDenied as e:
                        print("Permission denied error:", e)
                        break  # Exit the retry loop on specific exceptions

                    except Exception as e:
                        retry_count += 1
                        print(f"An error occurred (retry {retry_count}/{MAX_RETRIES}):", e)
                        if retry_count >= MAX_RETRIES:
                            print("Max retries reached. Skipping this file.")
                            break  # Exit the retry loop after max retries
                # Save to JSON
                if response.text is not None:
                    # Initialize variables for retry mechanism
                    parse_successful = False
                    retry_count_tech = 0
                    MAX_RETRIES_TECH = 5

                    while not parse_successful and retry_count_tech < MAX_RETRIES_TECH:
                        try:
                            questions = json.loads(response.text)
                            technical_questions = json.loads(technical_response.text)
                            parse_successful = True  # Parsing was successful
                        except json.JSONDecodeError as e:
                            retry_count_tech += 1
                            print(f"JSONDecodeError when parsing technical_response.text: {e}")
                            if retry_count_tech >= MAX_RETRIES_TECH:
                                print("Max retries reached for technical_response.text parsing. Skipping technical questions.")
                                technical_questions = []  # Assign an empty list to technical_questions
                                questions = []  # Assign an empty list to questions
                                break
                            else:
                                print(f"Retrying original question generation (retry {retry_count_tech}/{MAX_RETRIES_TECH})")
                                # Re-generate response
                                response = model.generate_content(contents, safety_settings=safety_config)
                                print(f"Retrying technical_model.generate_content() (retry {retry_count_tech}/{MAX_RETRIES_TECH})")
                                # Re-generate technical_response
                                technical_response = technical_model.generate_content(contents, safety_settings=safety_config)
                                await asyncio.sleep(2)  # Optional delay between retries
                    
                    with open(json_output_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                
                if os.path.exists(json_output_path):
                    print("Adding technical questions.")
                    # Load existing data
                    with open(json_output_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                else:
                    existing_data = []

                if isinstance(technical_questions, list):
                        # Append new data to existing_data
                        existing_data.extend(technical_questions)
                with open(json_output_path, 'w', encoding='utf-8') as f:
                        json.dump(existing_data, f, indent=4)

                print(f"Generation complete for {file}. JSON saved at {json_output_path}.")
                print("-------------------")

                assessment = await supervisorCheck(json_output_path, contents)
    

async def supervisorCheck(json_path, contents):

    print("Running supervisor check...")

    sup_model = GenerativeModel('gemini-1.5-flash',
                              # Set the `response_mime_type` to output JSON
                              generation_config={"response_mime_type": "application/json"}, 
                              system_instruction="You are a technical system meant to assess the accuracy of question and answer pairs. Always respond in a list format in the specified JSON schema.")



    contents.pop()

    # Load the JSON file
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        question = item['question']
        answer = item['correct_answer']

        supervisorPrompt = """
                            Is this answer correct for the given question? If not, provide the correct answer.

                            Question: """ + question + """
                            Answer: """ + answer + """

                            Respond using this JSON schema, just return the list itself:
                                [{"question": str, "original_answer", "is_correct": bool, "correct_answer": str}]
                           """

        contents.append(supervisorPrompt)
    # Generate content using the model
    response = sup_model.generate_content(contents, safety_settings=safety_config)

    # Wait 20 seconds
    await asyncio.sleep(20)
    # Save the response in a Markdown file
    assessment_file_path = os.path.join(os.path.dirname(json_path), f'{lesson_name}_assessment.json')
    with open(assessment_file_path, 'w', encoding='utf-8') as assessment:
        assessment.write(response.text)
    print(f"Supervisor file saved: {assessment_file_path}")
    print("-------------------")

    with open(assessment_file_path, 'r', encoding='utf-8') as f:
        assessment_data = json.load(f)
    
    for item in assessment_data:
        if item['is_correct'] == False:
            # Update the correct answer
            correct_answer = item['correct_answer']
            for question_item in data:
                if question_item['question'] == item['question']:
                    question_item['correct_answer'] = correct_answer

                    # Write the updated data back to the JSON file
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)

                    print(f"Correct answer updated for question: {item['question']} with answer: {correct_answer}")

    return assessment_file_path


# Set the root directory to your Course directory

courses = [r"rocket-pool-reth-integration"]
# Run the async function
for course in courses:
    questions = asyncio.run(generate("../courses/" + course))



