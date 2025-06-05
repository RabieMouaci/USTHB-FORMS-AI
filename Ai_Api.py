from flask import Flask, request, jsonify, render_template
import json
import re
import random
import time
import google.generativeai as genai

app = Flask(__name__)

# -------------------- Helper Functions --------------------
def validate_university_context(user_prompt):
    """
    Validates if the user prompt is related to university forms.
    This is a more lenient validation that allows a wider range of topics.
    Returns True if valid, False otherwise.
    """
    # For the updated version, we'll make it much less strict
    # Only filter out obviously unrelated content

    # List of keywords that are definitely NOT university-related
    non_university_keywords = [
        'bomb', 'weapon', 'illegal', 'hack', 'pornography', 'gambling',
        'drugs', 'steal', 'terrorism', 'attack','ecomerce'
    ]

    # Only reject if there are clearly non-university keywords and no university keywords
    prompt_lower = user_prompt.lower()

    # If any of the non-university keywords are found, check if there are any university keywords
    if any(keyword in prompt_lower for keyword in non_university_keywords):
        university_keywords = [
            'university','algeria','usthb', 'college', 'campus', 'student', 'faculty', 'professor',
            'course', 'degree', 'academic', 'enrollment', 'registration',
            'admission', 'education', 'form', 'document', 'application'
        ]
        return any(keyword in prompt_lower for keyword in university_keywords)

    # By default, accept the prompt
    return True

def extract_json(text):
    """Extract JSON content from text, handling markdown code blocks if present."""
    # Check for JSON in code blocks
    json_match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()
    return text.strip()

def chat_with_ai(form_context, conversation_history=None, conversation_id=None, current_form=None):
    """
    Uses the AI to ask a relevant follow-up question based on the context, conversation history,
    and current form state if available.
    """
    try:
        genai.configure(api_key="(put your own key here)")
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Build the conversation context
        context = ""
        if conversation_history:
            for entry in conversation_history:
                if 'user' in entry:
                    context += f"User: {entry['user']}\n"
                if 'assistant' in entry:
                    context += f"Assistant: {entry['assistant']}\n"

            # Add the current form context
            context += f"User: {form_context}\n"
        else:
            context = f"User: {form_context}\n"

        # Add current form state information if available
        current_form_description = ""
        if current_form:
            current_form_description = "Current form state:\n"
            try:
                if isinstance(current_form, str):
                    current_form = json.loads(current_form)

                # Format the current form state to be readable
                if "categories" in current_form:
                    for category in current_form["categories"]:
                        current_form_description += f"Category: {category.get('category_name', 'Unnamed')}\n"
                        if "questions" in category:
                            for question in category["questions"]:
                                current_form_description += f"  - Question: {question.get('question_text', 'Unnamed')}"
                                if "question_type" in question:
                                    current_form_description += f" (Type: {question['question_type']})"
                                current_form_description += "\n"
            except Exception as e:
                current_form_description += f"Error parsing current form: {str(e)}\n"

        prompt = (
            f"You are a university form creation assistant. You're having a conversation with a user to understand "
            f"what kind of university form they need. Here's the conversation history so far:\n\n"
            f"{context}\n"
            f"{current_form_description}\n"
            f"Generate ONE relevant follow-up question that would help gather more context about what the user needs "
            f"for their university form. Ask for specific details that would make the form more accurate and useful.\n\n"
            f"If the user already has some form elements, acknowledge them and ask about additional sections "
            f"or information they might want to include.\n\n"
            f"Return ONLY a JSON object with this structure:\n"
            f'{{"question":"YOUR FOLLOW-UP QUESTION HERE"}}\n\n'
        )

        response = model.generate_content(prompt)

        if response.text:
            # Extract JSON data
            json_str = extract_json(response.text)
            result = json.loads(json_str)

            # Add conversation_id to the response
            if conversation_id:
                result['conversation_id'] = conversation_id
            else:
                result['conversation_id'] = generate_conversation_id()

            return result
        else:
            # Fallback in case of empty response
            return {
                "question": "Could you provide more details about what specific information you need to collect with this form?",
                "conversation_id": conversation_id or generate_conversation_id()
            }
    except Exception as e:
        # Fallback question
        return {
            "question": "What specific details would you like to include in this university form?",
            "conversation_id": conversation_id or generate_conversation_id()
        }

def generate_form(form_context, conversation_id=None, current_form=None):
    """
    Calls the AI model to generate form questions in the specified JSON format.
    Uses conversation history if a conversation_id is provided.
    Preserves existing form elements if current_form is provided.
    """
    try:
        genai.configure(api_key="(put your own key here)")
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Build context description including conversation history if available
        context_description = "Form context:\n"

        # Include conversation history if available
        if conversation_id and conversation_id in conversation_store:
            context_description += "Conversation history:\n"
            for entry in conversation_store[conversation_id]:
                if 'user' in entry:
                    context_description += f"User: {entry['user']}\n"
                if 'assistant' in entry:
                    context_description += f"Assistant: {entry['assistant']}\n"
                if 'form_state' in entry:
                    context_description += f"Previous form state was saved\n"

        # Add the form context
        if isinstance(form_context, dict):
            for key, value in form_context.items():
                # Convert key from snake_case to readable text
                readable_key = key.replace('_', ' ').capitalize()
                context_description += f"{readable_key}: {value}\n"
        else:
            context_description += f"{form_context}\n"

        # Process current form state if available
        existing_form_json = "{}"
        existing_categories = []

        if current_form:
            try:
                if isinstance(current_form, str):
                    current_form_data = json.loads(current_form)
                else:
                    current_form_data = current_form

                if "categories" in current_form_data:
                    existing_categories = current_form_data["categories"]

                existing_form_json = json.dumps(current_form_data, indent=2)

                context_description += "\nEXISTING FORM STRUCTURE TO PRESERVE:\n"
                context_description += f"{existing_form_json}\n"
            except Exception as e:
                context_description += f"\nError parsing existing form structure: {str(e)}\n"

        # Create prompt for generation
        prompt_for_generation = (
            f"Generate a university form based on this context:\n{context_description}\n"
            f"Create a well-structured form with appropriate categories and questions "
            f"for a university form. Each category should have 2-4 related questions.\n\n"
        )

        # Add instructions for handling existing form elements
        if existing_categories:
            prompt_for_generation += (
                f"IMPORTANT: You MUST preserve all existing categories and questions exactly as provided. "
                f"DO NOT modify, remove, or change any existing elements. Only add new categories or questions "
                f"that complement the existing form.\n\n"
            )

        prompt_for_generation += (
            f"The form should follow typical university data collection standards.\n\n"
            f"Return ONLY a JSON object with this exact structure:\n"
            f'{{\n'
            f'  "form_name": "Generate an appropriate form name",\n'
            f'  "form_description": "Generate a description for the form",\n'
            f'  "categories": [\n'
            f'    {{\n'
            f'      "category_name": "Category Name",\n'
            f'      "questions": [\n'
            f'        {{\n'
            f'          "question_text": "Question text here?",\n'
            f'          "question_type": "text or select",\n'
            f'          "answer_type": "question courte, question longue, document, numéro de téléphone, nombre, choix multiple, choix unique, date, dropdownor email",\n'
            f'          "required": true or false,\n'
            f'          "choices": [\n'
            f'            {{ "text": "Choice 1" }},\n'
            f'            {{ "text": "Choice 2" }}\n'
            f'          ]\n'
            f'        }}\n'
            f'      ]\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"IMPORTANT INSTRUCTIONS:\n"
            f"1. Generate a clear, descriptive form_name that reflects the purpose of the form\n"
            f"2. Generate a helpful form_description that explains what the form is for\n"
            f"3. For text questions without choices, omit the 'choices' field entirely\n"
            f"4. Use 'required': true for essential information, false otherwise\n"
            f"5. Only use question_type values of 'text' or 'select'\n"
            f"6. Only use answer_type values: 'question courte', 'question longue', 'document', 'numéro de téléphone', 'nombre', 'choix multiple', 'choix unique', 'date', 'dropdown' or 'email'\n"
            f"7. When question_type='select', you MUST include choices and use answer_type values: 'choix multiple', 'choix unique' or 'dropdown'\n"
            f"8. When question_type='text', omit the choices field and use other answer_type values\n"
            f"9. Ensure the JSON is properly formatted and valid\n"
        )

        if existing_categories:
            prompt_for_generation += (
                f"8. Start your response with ALL existing categories and questions exactly as they are. "
                f"DO NOT rearrange or modify them. Add new categories only at the end.\n"
            )

        prompt_for_generation += "Return ONLY the JSON with no additional text or explanations"

        response = model.generate_content(prompt_for_generation)

        if response.text:
            # Extract and parse the JSON response
            json_str = extract_json(response.text)
            result = json.loads(json_str)

            # Verify that existing categories are preserved if they were provided
            if existing_categories:
                # Check if existing categories were preserved
                if not verify_preserved_categories(existing_categories, result.get("categories", [])):
                    # If not preserved correctly, manually combine them
                    result["categories"] = existing_categories + [
                        cat for cat in result.get("categories", [])
                        if cat.get("category_name") not in [ec.get("category_name") for ec in existing_categories]
                    ]

            return result
        else:
            raise ValueError("No content returned from AI model.")
    except Exception as e:
        raise Exception(f"Error generating form: {str(e)}")

def verify_preserved_categories(existing_categories, generated_categories):
    """
    Verify that all existing categories are preserved in the generated form.
    Returns True if preserved, False otherwise.
    """
    if not existing_categories:
        return True

    existing_names = {cat.get("category_name") for cat in existing_categories if "category_name" in cat}

    # Check if all existing category names appear in the generated categories
    found_names = {cat.get("category_name") for cat in generated_categories
                   if "category_name" in cat and cat.get("category_name") in existing_names}

    # All existing categories should be found in the generated list
    return len(found_names) == len(existing_names)

# -------------------- Flask Routes --------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

# Dictionary to store conversation history
conversation_store = {}

def generate_conversation_id():
    """Generate a unique conversation ID"""
    return f"conv_{random.randint(10000, 99999)}_{int(time.time())}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing prompt"}), 400

    # Extract conversation ID if provided
    conversation_id = data.get('conversation_id', None)

    # Extract current form state if provided
    current_form = data.get('current_form', None)

    try:
        # More lenient validation - only reject clearly problematic content
        if not validate_university_context(data['prompt']):
            return jsonify({
                "question": "I need to focus on creating university-related forms. Could you please provide a prompt related to educational or academic forms?",
                "conversation_id": conversation_id or generate_conversation_id()
            })

        # Get conversation history if ID exists
        conversation_history = None
        if conversation_id and conversation_id in conversation_store:
            conversation_history = conversation_store[conversation_id]

        # Get AI response, passing the existing conversation_id and current form
        response = chat_with_ai(data['prompt'], conversation_history, conversation_id, current_form)

        # Get the conversation ID (either existing or newly created)
        conversation_id = response.get('conversation_id')

        # Initialize conversation history if this is a new conversation
        if conversation_id not in conversation_store:
            conversation_store[conversation_id] = []

        # Add the current exchange to history
        history_entry = {
            'user': data['prompt'],
            'assistant': response['question']
        }

        # Save current form state if provided
        if current_form:
            history_entry['form_state'] = current_form

        conversation_store[conversation_id].append(history_entry)

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data or 'context' not in data:
        return jsonify({"error": "Missing form context"}), 400

    # Get conversation ID if provided
    conversation_id = data.get('conversation_id', None)

    # Get current form state if provided
    current_form = data.get('current_form', None)

    try:
        # More lenient validation - only reject clearly problematic content
        if isinstance(data['context'], str) and not validate_university_context(data['context']):
            return jsonify({
                "error": "Please provide a context related to educational or academic forms.",
                "suggestion": "Try focusing on university registration, application, or other educational forms."
            }), 400

        # Pass the conversation_id and current_form to use conversation history and preserve existing elements
        result = generate_form(data['context'], conversation_id, current_form)

        # If a conversation exists, store the final form as part of the conversation history
        if conversation_id and conversation_id in conversation_store:
            conversation_store[conversation_id].append({
                'form_generated': True,
                'form_data': result
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- App Runner --------------------
if __name__ == "__main__":
    app.run(debug=True)