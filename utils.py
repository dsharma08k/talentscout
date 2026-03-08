"""
Utility functions for TalentScout Hiring Assistant.
Handles session state management, input validation, data extraction,
file operations, and chat history formatting.
"""

import re
import json
import os
from datetime import datetime
import streamlit as st
from prompts import SYSTEM_PROMPT


# Maximum number of messages allowed per session to prevent API abuse
MAX_MESSAGES = 50


def initialize_session_state():
    """
    Safely initialize all required Streamlit session state variables.
    Uses a defaults dict so new keys can be added in one place.
    Only initializes variables that don't already exist to preserve state across reruns.
    """
    defaults = {
        "messages": [],
        "candidate_info": {},
        "conversation_stage": "greeting",
        "info_collected": False,
        "questions_asked": False,
        "conversation_ended": False,
        "message_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def sanitize_input(user_input: str) -> str:
    """
    Clean and limit user input to prevent token abuse and remove
    excessive whitespace.

    Args:
        user_input: The raw text message from the user.

    Returns:
        A stripped and length-limited version of the input.
    """
    if not user_input:
        return ""
    # Strip excessive whitespace
    user_input = user_input.strip()
    # Limit input length to prevent token abuse
    user_input = user_input[:500]
    return user_input


def detect_exit_intent(user_input: str) -> bool:
    """
    Check whether the user's message contains an exit keyword.
    Matches whole words only to avoid false positives (e.g., 'done' inside 'condone').

    Args:
        user_input: The raw text message from the user.

    Returns:
        True if an exit keyword is detected, False otherwise.
    """
    exit_keywords = ["bye", "exit", "quit", "goodbye", "done", "stop", "end", "finish"]
    user_lower = user_input.lower().strip()
    for keyword in exit_keywords:
        # Match the keyword as a whole word using word boundaries
        if re.search(r"\b" + re.escape(keyword) + r"\b", user_lower):
            return True
    return False


def validate_email(email: str) -> bool:
    """
    Validate an email address using a standard regex pattern.

    Args:
        email: The email string to validate.

    Returns:
        True if the email matches a valid format, False otherwise.
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """
    Validate a phone number. Accepts 10 or more digits with optional
    country code prefix (+), dashes, spaces, and parentheses.

    Args:
        phone: The phone number string to validate.

    Returns:
        True if the phone number is valid, False otherwise.
    """
    # Strip common formatting characters and check for at least 10 digits
    digits_only = re.sub(r"[^\d]", "", phone.strip())
    if len(digits_only) < 10:
        return False
    # Ensure the original input only contains valid phone characters
    pattern = r"^[+]?[\d\s\-().]{10,}$"
    return bool(re.match(pattern, phone.strip()))


def extract_candidate_info(messages: list) -> dict:
    """
    Parse the conversation history to extract candidate information
    that has been mentioned or confirmed during the screening.

    Scans both user and assistant messages for patterns matching
    the seven required fields: name, email, phone, experience,
    position, location, and tech_stack.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        A dict with keys for each recognized field and their extracted values.
    """
    info = {}

    # Build a single string of all user messages for pattern matching
    user_messages = [
        msg["content"] for msg in messages if msg["role"] == "user"
    ]
    assistant_messages = [
        msg["content"] for msg in messages if msg["role"] == "assistant"
    ]

    all_user_text = " ".join(user_messages)
    all_assistant_text = " ".join(assistant_messages)

    # Extract email if present in user messages
    email_match = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", all_user_text
    )
    if email_match:
        info["email"] = email_match.group()

    # Extract phone number if present in user messages
    phone_match = re.search(r"[+]?[\d][\d\s\-().]{9,}", all_user_text)
    if phone_match:
        info["phone"] = phone_match.group().strip()

    # Extract years of experience if a number followed by 'year' is found
    exp_match = re.search(r"(\d+)\s*(?:\+\s*)?year", all_user_text, re.IGNORECASE)
    if exp_match:
        info["experience"] = exp_match.group()

    # For name, position, location, and tech_stack, we rely on context from
    # the assistant confirming the field. These are harder to regex reliably,
    # so we check if the assistant has acknowledged them.
    # We look at conversation flow: assistant asks -> user answers -> next question asked

    # Track which fields have been asked and answered based on conversation order
    field_sequence = [
        "name", "email", "phone", "experience",
        "position", "location", "tech_stack"
    ]
    field_keywords = {
        "name": ["full name", "your name", "name"],
        "email": ["email"],
        "phone": ["phone", "contact number", "phone number"],
        "experience": ["experience", "years of experience", "how many years"],
        "position": ["position", "desired position", "role", "desired role"],
        "location": ["location", "where are you", "current location", "based"],
        "tech_stack": [
            "tech stack", "technologies", "programming languages",
            "technical skills", "tools", "frameworks"
        ],
    }

    # Walk through messages to determine which fields have been collected
    current_field_index = 0
    for i, msg in enumerate(messages):
        if msg["role"] == "assistant" and current_field_index < len(field_sequence):
            content_lower = msg["content"].lower()
            current_field = field_sequence[current_field_index]

            # Check if the assistant is asking about the next field
            next_index = current_field_index + 1
            if next_index < len(field_sequence):
                next_field = field_sequence[next_index]
                next_keywords = field_keywords[next_field]
                if any(kw in content_lower for kw in next_keywords):
                    # The previous field was collected; the user's last message is the answer
                    for j in range(i - 1, -1, -1):
                        if messages[j]["role"] == "user":
                            field_name = field_sequence[current_field_index]
                            if field_name not in info:
                                info[field_name] = messages[j]["content"].strip()
                            break
                    current_field_index = next_index

    # Check if the last field in sequence was answered (tech_stack)
    # by looking for the assistant generating technical questions
    if "tech_stack" not in info:
        for i, msg in enumerate(messages):
            if msg["role"] == "assistant" and current_field_index == len(field_sequence) - 1:
                content_lower = msg["content"].lower()
                if "technical" in content_lower and "question" in content_lower:
                    for j in range(i - 1, -1, -1):
                        if messages[j]["role"] == "user":
                            info["tech_stack"] = messages[j]["content"].strip()
                            break
                    break

    return info


def save_candidate_data(candidate_info: dict):
    """
    Save candidate data securely to a local JSON file (candidates_data.json).
    Appends the new candidate entry to the existing list in the file.
    Creates the file if it does not exist. Skips saving if info is empty.

    Each entry includes a timestamp for when the data was recorded.

    Args:
        candidate_info: Dict containing the candidate's collected information.
    """
    # Never save empty data
    if not candidate_info:
        return

    file_path = "candidates_data.json"

    # Add timestamp to the candidate record
    candidate_entry = {
        "submitted_at": datetime.now().isoformat(),
        "candidate": candidate_info,
    }

    # Load existing data or start with empty list
    candidates = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                candidates = json.load(f)
        except (json.JSONDecodeError, IOError):
            # If the file is corrupted or unreadable, start fresh
            candidates = []

    candidates.append(candidate_entry)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2, ensure_ascii=False)
        print(f"Candidate data saved successfully at {candidate_entry['submitted_at']}")
    except IOError as e:
        print(f"Error saving candidate data: {e}")


def format_chat_history(messages: list) -> list:
    """
    Convert session messages into the format expected by the OpenAI Chat API.
    Prepends the system prompt as the first message so the LLM maintains
    its persona and instructions throughout the conversation.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
                  from Streamlit session state.

    Returns:
        A list of dicts formatted for the OpenAI API, with the system
        prompt as the first entry followed by all conversation messages.
    """
    formatted = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        formatted.append({"role": msg["role"], "content": msg["content"]})
    return formatted
