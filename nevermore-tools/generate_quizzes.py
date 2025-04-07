import os
import json
import random
import re
import glob

def natural_key(s):
    """
    Returns a key for natural sorting of a string.
    Extracts the leading number if present; otherwise returns a high value.
    """
    m = re.match(r'(\d+)', s)
    return int(m.group(1)) if m else float('inf')

def generate_quizzes(course_dir, lessons_per_quiz=10, omitted_lesson_names=None):
    """
    Generate full quizzes for each section in a course directory.

    For every group of 'lessons_per_quiz' valid lessons, one quiz is created.
    A lesson is considered valid if its folder name is not in omitted_lesson_names.

    Each quiz includes one randomly chosen question from each lesson in that group.
    If a section has fewer than lessons_per_quiz valid lessons in total, a single quiz is generated
    with however many lessons are available.

    Each generated question is tagged with a "lesson" property indicating its source lesson,
    and a "correct_position" property set to a random int between 1 and 4.
    A summary mapping of quiz files to lesson folders is printed and saved.

    Args:
        course_dir (str): Path to the top-level course directory.
        lessons_per_quiz (int): Number of lessons per quiz. Default is 10.
        omitted_lesson_names (list of str, optional): List of lesson folder names to omit.
    """
    if isinstance(course_dir, tuple):
        course_dir = course_dir[0]
        
    if omitted_lesson_names is None:
        omitted_lesson_names = []

    overall_mappings = {}  # This will store quiz mappings for each section

    # Iterate over each section directory inside the course directory
    for section_name in sorted(os.listdir(course_dir)):
        section_path = os.path.join(course_dir, section_name)
        if not os.path.isdir(section_path):
            continue

        lesson_questions_list = []
        valid_lesson_names = []  # To keep track of lesson folder names

        # Sort lesson folders using natural sort (numeric order)
        for lesson_name in sorted(os.listdir(section_path), key=natural_key):
            lesson_path = os.path.join(section_path, lesson_name)
            if not os.path.isdir(lesson_path):
                continue

            if lesson_name in omitted_lesson_names:
                print(f"Skipping omitted lesson: {lesson_name}")
                continue

            questions_file = os.path.join(lesson_path, 'questions.json')
            print(f"Checking for questions.json in {lesson_path}")
            if os.path.exists(questions_file):
                try:
                    with open(questions_file, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                    if isinstance(questions, list) and questions:
                        lesson_questions_list.append(questions)
                        valid_lesson_names.append(lesson_name)
                    else:
                        print(f"Skipping {questions_file} because content is not a non-empty list.")
                except Exception as e:
                    print(f"Error reading {questions_file}: {e}")
            else:
                print(f"No questions.json found in {lesson_path}")

        total_lessons = len(lesson_questions_list)
        quiz_mappings = []  # For storing mappings for this section

        if total_lessons == 0:
            print(f"Section '{section_name}' has no valid lessons. Skipping section.")
            continue

        if total_lessons < lessons_per_quiz:
            print(f"Section '{section_name}' has only {total_lessons} valid lessons; generating a quiz with all lessons.")
            quiz_questions = []
            for i, questions in enumerate(lesson_questions_list):
                lesson_identifier = valid_lesson_names[i]
                try:
                    question = random.choice(questions)
                    if isinstance(question, dict):
                        question["lesson"] = lesson_identifier
                        question["correct_position"] = random.randint(1, 4)
                    quiz_questions.append(question)
                except Exception as e:
                    print(f"Error selecting question from lesson '{lesson_identifier}' (questions file content: {questions}). Exception: {e}")
                    raise e

            quiz_filename = "quiz-1.json"
            quiz_path = os.path.join(section_path, quiz_filename)
            try:
                with open(quiz_path, 'w', encoding='utf-8') as quiz_file:
                    json.dump(quiz_questions, quiz_file, indent=2, ensure_ascii=False)
                print(f"Created {quiz_filename} in {section_path}")
                quiz_mappings.append({"quiz_file": quiz_filename, "lessons": valid_lesson_names})
            except Exception as e:
                print(f"Failed to create {quiz_filename} in {section_path}: {e}")
        else:
            quiz_count = 0
            for start_idx in range(0, total_lessons, lessons_per_quiz):
                subset = lesson_questions_list[start_idx:start_idx+lessons_per_quiz]
                if len(subset) < lessons_per_quiz:
                    print(f"Skipping incomplete quiz group in section '{section_name}' (only {len(subset)} lessons).")
                    continue

                quiz_count += 1
                quiz_questions = []
                quiz_lessons = valid_lesson_names[start_idx:start_idx+lessons_per_quiz]
                for i, questions in enumerate(subset):
                    lesson_identifier = quiz_lessons[i]
                    try:
                        question = random.choice(questions)
                        if isinstance(question, dict):
                            question["lesson"] = lesson_identifier
                            question["correct_position"] = random.randint(1, 4)
                        quiz_questions.append(question)
                    except Exception as e:
                        print(f"Error selecting question from lesson '{lesson_identifier}' (questions file content: {questions}). Exception: {e}")
                        raise e

                quiz_filename = f"quiz-{quiz_count}.json"
                quiz_path = os.path.join(section_path, quiz_filename)
                try:
                    with open(quiz_path, 'w', encoding='utf-8') as quiz_file:
                        json.dump(quiz_questions, quiz_file, indent=2, ensure_ascii=False)
                    print(f"Created {quiz_filename} in {section_path}")
                    quiz_mappings.append({"quiz_file": quiz_filename, "lessons": quiz_lessons})
                except Exception as e:
                    print(f"Failed to create {quiz_filename} in {section_path}: {e}")

        if quiz_mappings:
            overall_mappings[section_name] = quiz_mappings
            print(f"\nQuiz mappings for section '{section_name}':")
            for mapping in quiz_mappings:
                print(f"  {mapping['quiz_file']}: covers lessons {mapping['lessons']}")
            print("\n" + "="*60 + "\n")

    mappings_file = os.path.join(course_dir, "quiz_mappings.json")
    try:
        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(overall_mappings, f, indent=2, ensure_ascii=False)
        print(f"Saved overall quiz mappings to {mappings_file}")
    except Exception as e:
        print(f"Failed to save overall quiz mappings: {e}")

def generate_summary_quiz(course_dir, omitted_lesson_names=None, summary_cap=35, min_summary=8):
    """
    Generate summary quizzes for each section in the course directory.
    The summary quizzes are generated by selecting one new question per valid lesson,
    excluding any question(s) that were previously selected in the full quizzes.
    
    If the total number of summary questions exceeds summary_cap (default 35),
    multiple summary quiz files will be generated (each containing up to summary_cap questions).
    
    Additionally, if the total number of summary questions is less than min_summary (default 8),
    the function will attempt to draw additional questions (from lessons that have extra candidates)
    until at least min_summary questions are reached (or no more new questions are available).
    
    Process for each section:
      1. For each valid lesson (sorted naturally and not omitted), load its questions.json.
      2. Read all full quiz files (matching "quiz-*.json" except summary_quiz*.json) in the section
         to build a set of question texts that were already used for that lesson.
      3. For each lesson, filter out previously used questions and, if available, randomly select a new question.
         Also, store all candidate new questions per lesson.
      4. If the total number of summary questions is less than min_summary, iterate over lessons with extra candidates
         to add additional questions until the minimum is reached.
      5. Split the collected summary questions into groups of up to summary_cap questions.
      6. Save each group as summary_quiz-<n>.json in the section directory.
    
    Each selected question is tagged with its source lesson and a "correct_position" property set
    to a random int between 1 and 4.
    
    Args:
        course_dir (str): Path to the top-level course directory.
        omitted_lesson_names (list of str, optional): List of lesson folder names to omit.
        summary_cap (int): Maximum number of questions per summary quiz file (default is 35).
        min_summary (int): Minimum total number of summary questions to generate per section (default is 8).
    """
    if isinstance(course_dir, tuple):
        course_dir = course_dir[0]
        
    if omitted_lesson_names is None:
        omitted_lesson_names = []

    for section_name in sorted(os.listdir(course_dir)):
        section_path = os.path.join(course_dir, section_name)
        if not os.path.isdir(section_path):
            continue

        valid_lessons = []  # List of (lesson_name, lesson_path)
        for lesson_name in sorted(os.listdir(section_path), key=natural_key):
            lesson_path = os.path.join(section_path, lesson_name)
            if not os.path.isdir(lesson_path):
                continue
            if lesson_name in omitted_lesson_names:
                print(f"Skipping omitted lesson: {lesson_name}")
                continue
            valid_lessons.append((lesson_name, lesson_path))

        if not valid_lessons:
            print(f"Section '{section_name}' has no valid lessons. Skipping summary quiz generation.")
            continue

        # Build a mapping of lesson -> set of question texts already used in full quizzes.
        used_questions = {}
        quiz_files = glob.glob(os.path.join(section_path, "quiz-*.json"))
        quiz_files = [qf for qf in quiz_files if "summary_quiz" not in os.path.basename(qf)]
        for quiz_file in quiz_files:
            try:
                with open(quiz_file, 'r', encoding='utf-8') as f:
                    quiz_data = json.load(f)
                for q in quiz_data:
                    if isinstance(q, dict) and "lesson" in q and "question" in q:
                        lesson = q["lesson"]
                        q_text = q["question"]
                        used_questions.setdefault(lesson, set()).add(q_text)
            except Exception as e:
                print(f"Error reading quiz file {quiz_file}: {e}")

        summary_questions = []
        summary_mapping = {}  # Mapping of lesson -> list of chosen question texts
        candidate_dict = {}   # Mapping of lesson -> list of candidate questions (all that are new)

        # First pass: for each lesson, pick one new question and store all candidates.
        for lesson_name, lesson_path in valid_lessons:
            questions_file = os.path.join(lesson_path, "questions.json")
            if not os.path.exists(questions_file):
                print(f"No questions.json found in {lesson_path}, skipping.")
                continue
            try:
                with open(questions_file, 'r', encoding='utf-8') as f:
                    all_questions = json.load(f)
                if not (isinstance(all_questions, list) and all_questions):
                    print(f"File {questions_file} does not contain a non-empty list. Skipping.")
                    continue

                used = used_questions.get(lesson_name, set())
                new_candidates = []
                for q in all_questions:
                    if isinstance(q, dict) and "question" in q:
                        if q["question"] not in used:
                            new_candidates.append(q)
                    else:
                        if q not in used:
                            new_candidates.append(q)

                if not new_candidates:
                    print(f"No new questions available for lesson '{lesson_name}'.")
                    continue

                candidate_dict[lesson_name] = new_candidates[:]  # store all candidates
                # Select one candidate randomly as the initial selection.
                selected = random.choice(new_candidates)
                if isinstance(selected, dict):
                    selected["lesson"] = lesson_name
                    selected["correct_position"] = random.randint(1, 4)
                summary_questions.append(selected)
                summary_mapping.setdefault(lesson_name, []).append(selected.get("question", "N/A"))
            except Exception as e:
                print(f"Error processing {questions_file}: {e}")

        # If total summary questions are below min_summary, try to add additional questions.
        if len(summary_questions) < min_summary:
            additional_needed = min_summary - len(summary_questions)
            print(f"Total summary questions ({len(summary_questions)}) below minimum ({min_summary}). Attempting to add {additional_needed} additional questions.")
            # Iterate over lessons that have extra candidates.
            for lesson_name, candidates in candidate_dict.items():
                # Remove already selected questions for this lesson.
                already_selected = set(summary_mapping.get(lesson_name, []))
                extra_candidates = [q for q in candidates if (q.get("question") if isinstance(q, dict) else q) not in already_selected]
                while extra_candidates and additional_needed > 0:
                    extra = random.choice(extra_candidates)
                    if isinstance(extra, dict):
                        extra["lesson"] = lesson_name
                        extra["correct_position"] = random.randint(1, 4)
                    summary_questions.append(extra)
                    summary_mapping.setdefault(lesson_name, []).append(extra.get("question", "N/A"))
                    additional_needed -= 1
                    # Remove the chosen candidate from extra_candidates.
                    extra_candidates.remove(extra)
                    if additional_needed <= 0:
                        break
                if additional_needed <= 0:
                    break

        if summary_questions:
            # Split summary_questions into chunks of up to summary_cap
            num_chunks = (len(summary_questions) + summary_cap - 1) // summary_cap
            for i in range(num_chunks):
                chunk = summary_questions[i*summary_cap : (i+1)*summary_cap]
                summary_quiz_filename = f"summary_quiz-{i+1}.json"
                summary_quiz_file = os.path.join(section_path, summary_quiz_filename)
                try:
                    with open(summary_quiz_file, 'w', encoding='utf-8') as f:
                        json.dump(chunk, f, indent=2, ensure_ascii=False)
                    print(f"\nCreated summary quiz for section '{section_name}' in {summary_quiz_file}")
                except Exception as e:
                    print(f"Failed to create summary quiz for section '{section_name}': {e}")
            print("Summary quiz mapping:")
            for lesson, q_texts in summary_mapping.items():
                print(f"  {lesson}: {q_texts}")
            print("\n" + "="*60 + "\n")
        else:
            print(f"No new questions were available to create a summary quiz for section '{section_name}'.")

if __name__ == "__main__":
    
    course_dir="/home/equious/Nevermore/courses/formal-verification"
    lessons_per_quiz=10
    omitted_lesson_names=[
        "1-course-introduction", 
        "46-a-note-on-your-new-powers", 
        "71-section-1-horsestore-recap", 
        "1-introduction",
        "50-recap",
        "01-introduction",
        "21-mid-lesson-recap",
        "27-section-3-recap"
    ]

    generate_quizzes(course_dir=course_dir, lessons_per_quiz=lessons_per_quiz, omitted_lesson_names=omitted_lesson_names)
    generate_summary_quiz(
    course_dir=course_dir,
    omitted_lesson_names=omitted_lesson_names,
    summary_cap=35,
    min_summary=8
    )
