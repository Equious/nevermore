# Nevermore

## Overview

A python CLI for the generation of written lesson content based on video and textual context. Leverages Gemini 1.5 Pro and multiple inference layers to provide a selection of lessons to choose from.

## Installation

```bash
git clone https://github.com/Equious/nevermore.git
cd nevermore
```

> [!IMPORTANT]
> You'll need to enter the path to your own `GOOGLE_APPLICATION_CREDENTIALS` json in `line 14` of `Nevermore.py`

Install Nevermore:

```
pip install --editable .
```

## Running Nevermore

> [!IMPORTANT]
> `Line 82` is configured currently to support `.mov` video types. This will be configurable via CLI in future, but will need to be adjusted to your particular case.

Once installed you can run:

```bash
$ nevermore --root-directory "PATH/TO/YOUR/COURSE/DIRECTORY"
```

Your course directory must be in the following structure:

```
├── Course
│   ├── Section 1
│   │   ├── Lesson 1
│   │   │   └── lesson.mov
│   │   └── Lesson 2
│   │       └── lesson.mov
│   └── repo-context
│       ├── additional_context.md
│       └── additional_context.sol
```

Additional context to the video lesson can be added to the `repo-context` folder (in future this should pull from a provided GitHub repo).

> [!NOTE]
> This Repo contains a random selection of testing context files, remove as needed.
