# USTHB FORMS - AI Assistant Backend

This repository contains the AI-powered backend service for **USTHB FORMS**, a platform designed to help users create university-related forms through a conversational interface.

This service uses the Google Gemini API to understand user requests in natural language, ask clarifying questions, and generate structured JSON forms that can be rendered by a front-end application.

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [API Endpoints](#api-endpoints)
  - [Chat](#post-chat)
  - [Generate Form](#post-generate)
- [Contributing](#contributing)
- [License](#license)

## How It Works

The backend is a Flask application that serves as a bridge between a user-facing application (the "front-end") and the Google Gemini generative model.

1.  **Conversation**: A user starts by describing the form they want to create. The `/chat` endpoint sends this prompt to the AI, which is instructed to ask a relevant follow-up question to gather more specific details.
2.  **Context Management**: The server maintains the history of the conversation using a unique `conversation_id`. This ensures that the AI has the full context of the user's needs in subsequent interactions.
3.  **Iterative Refinement**: Users can provide additional details or modify their requests. The assistant can also take an `current_form` JSON object to add to or modify an existing form structure.
4.  **Form Generation**: Once the user is ready, the front-end calls the `/generate` endpoint. The server sends the entire conversation context to the AI, which then generates a complete, structured JSON representation of the university form.

## Features

-   **Conversational Form Building**: Engages users in a dialogue to precisely understand their requirements.
-   **Dynamic Form Generation**: Translates unstructured conversational text into a well-defined JSON format.
-   **Conversation Context & History**: Remembers previous parts of the conversation to build a coherent understanding.
-   **Iterative Form Refinement**: Allows for adding to or modifying an already partially-built form.
-   **University-Specific Context**: Includes a validation layer to gently guide users toward creating forms relevant to a university setting (e.g., registrations, applications, surveys).

## Project Structure

```
/
├── app.py              # The main Flask application file
├── requirements.txt    # Project dependencies
├── .env                # Local environment variables (DO NOT COMMIT)
├── .env.example        # Example environment variables
└── README.md           # This file
```

## Getting Started

Follow these instructions to get the AI assistant running on your local machine for development and testing.

### Prerequisites

-   Python 3.8+
-   `pip` (Python package installer)
-   A Google AI API Key. You can get one from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Installation

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/your-username/usthb-forms-ai-backend.git](https://github.com/your-username/usthb-forms-ai-backend.git)
    cd usthb-forms-ai-backend
    ```

2.  **Create and activate a virtual environment:**
    - On macOS/Linux:
      ```sh
      python3 -m venv venv
      source venv/bin/activate
      ```
    - On Windows:
      ```sh
      python -m venv venv
      .\venv\Scripts\activate
      ```

3.  **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```
    *You will need to create a `requirements.txt` file. Here are its contents:*
    ```txt
    Flask
    google-generativeai
    ```

4.  **Set up your environment variables:**
    * Create a file named `.env` by copying the example file:
        ```sh
        cp .env.example .env
        ```
    * Open the `.env` file and add your Google Gemini API key.
        ```
        GEMINI_API_KEY="AIzaSy...your...key...here"
        ```
    * **Important**: I've updated the code below to use this environment variable. Hardcoding API keys is insecure. Replace the `genai.configure` line in `app.py` with this:

        ```python
        # Near the top of app.py
        import os
        from dotenv import load_dotenv

        load_dotenv() # Loads environment variables from .env file

        # In your chat_with_ai and generate_form functions
        # Replace the hardcoded key with this:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
        genai.configure(api_key=api_key)
        ```


5.  **Run the Flask application:**
    ```sh
    flask run
    ```
    The application will be running at `http://127.0.0.1:5000`.

## API Endpoints

The server exposes two main endpoints for interacting with the AI.

### POST /chat

This endpoint drives the conversation. It takes the user's latest prompt and returns the AI's next question.

-   **URL**: `/chat`
-   **Method**: `POST`
-   **Request Body** (`application/json`):
    ```json
    {
      "prompt": "I need to make a form for new student registration.",
      "conversation_id": "conv_12345_67890",
      "current_form": {
        "form_name": "...",
        "categories": [
          /* ... existing form structure ... */
        ]
      }
    }
    ```
    - `prompt` (string, required): The user's message.
    - `conversation_id` (string, optional): The ID of the ongoing conversation. If not provided, a new one is created.
    - `current_form` (object, optional): The current JSON structure of the form if it's being edited.

-   **Success Response** (`application/json`):
    ```json
    {
      "question": "Great! What specific sections should the student registration form include, such as Personal Information or Academic History?",
      "conversation_id": "conv_12345_67890"
    }
    ```

### POST /generate

This endpoint generates the final JSON form based on the conversation context.

-   **URL**: `/generate`
-   **Method**: `POST`
-   **Request Body** (`application/json`):
    ```json
    {
      "context": "The user wants a new student registration form with personal details, contact info, and previous education sections.",
      "conversation_id": "conv_12345_67890",
      "current_form": {
        "form_name": "...",
        "categories": [
          /* ... existing form structure to be preserved/added to ... */
        ]
      }
    }
    ```
    - `context` (string, required): A summary of the user's needs. This can be the last prompt or a curated summary.
    - `conversation_id` (string, optional): The ID to retrieve the full conversation history.
    - `current_form` (object, optional): The current JSON form to be modified.

-   **Success Response** (`application/json`):
    *A full JSON object representing the generated form.*
    ```json
    {
      "form_name": "New Student Registration Form",
      "form_description": "A form to collect information from newly registering students.",
      "categories": [
        {
          "category_name": "Personal Information",
          "questions": [
            {
              "question_text": "Full Name",
              "question_type": "text",
              "answer_type": "question courte",
              "required": true
            }
            // ... other questions
          ]
        }
        // ... other categories
      ]
    }
    ```



## License

This project is licensed under the MIT License.
