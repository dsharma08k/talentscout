"""
TalentScout AI Hiring Assistant - Main Application
A Streamlit-based chatbot that screens job candidates using Groq LLM API.
Collects candidate information through conversation and generates
technical interview questions based on the candidate's tech stack.
"""

import streamlit as st
from openai import OpenAI
from config import GROQ_API_KEY, GROQ_BASE_URL, MODEL_NAME, MAX_TOKENS, TEMPERATURE
from prompts import GREETING_PROMPT, FAREWELL_PROMPT, SYSTEM_PROMPT
from utils import (
    initialize_session_state,
    detect_exit_intent,
    extract_candidate_info,
    save_candidate_data,
    format_chat_history,
    sanitize_input,
    MAX_MESSAGES,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TalentScout Hiring Assistant",
    page_icon="logo",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS for dark professional theme
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Hide default Streamlit hamburger menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Dark background */
    .stApp {
        background-color: #0f1117;
    }

    /* Top header bar */
    .top-header {
        background: linear-gradient(90deg, #1E88E5, #1565C0);
        padding: 1rem 2rem;
        border-radius: 0 0 12px 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .top-header h1 {
        color: #ffffff;
        font-size: 1.8rem;
        margin: 0;
        font-weight: 700;
    }
    .top-header p {
        color: #bbdefb;
        font-size: 0.95rem;
        margin: 0.25rem 0 0 0;
    }

    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* User message bubble */
    [data-testid="stChatMessage"]:has(.stMarkdown) {
        border-radius: 12px;
    }

    /* Assistant message styling */
    .assistant-bubble {
        background-color: #1e1e2e;
        padding: 1rem;
        border-radius: 12px;
        color: #e0e0e0;
        margin-bottom: 0.5rem;
    }

    /* User message styling */
    .user-bubble {
        background-color: #1E88E5;
        padding: 1rem;
        border-radius: 12px;
        color: #ffffff;
        margin-bottom: 0.5rem;
        text-align: right;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #161b22;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #c9d1d9;
    }

    /* Chat input area */
    .stChatInput {
        border-color: #1E88E5;
    }

    /* Success banner */
    .success-banner {
        background-color: #1b5e20;
        color: #c8e6c9;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 1rem 0;
        font-weight: 600;
    }

    /* Sidebar info cards */
    .info-card {
        background-color: #21262d;
        padding: 0.75rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 3px solid #1E88E5;
    }
    .info-card strong {
        color: #58a6ff;
    }
    .info-card span {
        color: #c9d1d9;
    }

    /* Button styling */
    .stButton > button {
        background-color: #1E88E5;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        background-color: #1565C0;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Initialize session state
# ---------------------------------------------------------------------------
initialize_session_state()

# ---------------------------------------------------------------------------
# API key check - stop early if not configured
# ---------------------------------------------------------------------------
if not GROQ_API_KEY:
    st.error("Groq API key not found. Please add it to your .env file.")
    st.stop()

# ---------------------------------------------------------------------------
# Groq LLM API call function
# ---------------------------------------------------------------------------

def get_llm_response(messages: list) -> str:
    """
    Send the conversation history to the Groq API (OpenAI-compatible) and
    return the assistant's reply.

    Args:
        messages: Formatted list of message dicts including the system prompt.

    Returns:
        The text content of the assistant's response, or an error message
        if the API call fails.
    """
    try:
        client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e).lower()
        if "authentication" in error_msg or "api key" in error_msg:
            return "Authentication error. Please check your API key in the .env file."
        if "rate limit" in error_msg or "rate_limit" in error_msg:
            return (
                "I'm receiving too many requests right now. "
                "Please wait a moment and try again."
            )
        if "connection" in error_msg:
            return (
                "Connection issue. Please check your internet and try again."
            )
        # Log the real error privately, show generic message to user
        print(f"Unexpected LLM error: {e}")
        return (
            "Something went wrong. Please try again or refresh the page."
        )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## TalentScout")
    st.markdown("_AI-Powered Hiring Assistant_")
    st.markdown("---")

    # Candidate info section - updates dynamically
    st.markdown("### Candidate Info")

    info = st.session_state.candidate_info or {}
    field_labels = {
        "name": "Name",
        "email": "Email",
        "phone": "Phone",
        "experience": "Experience",
        "position": "Position",
        "location": "Location",
        "tech_stack": "Tech Stack",
    }
    for key, label in field_labels.items():
        value = info.get(key, "-- not yet collected --")
        st.markdown(
            f'<div class="info-card"><strong>{label}:</strong> '
            f"<span>{value}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Reset conversation button
    if st.button("Reset Conversation"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "TalentScout is an AI-powered recruitment screening tool. "
        "It collects candidate information through a friendly conversation "
        "and generates tailored technical interview questions based on "
        "the candidate's tech stack."
    )

# ---------------------------------------------------------------------------
# Main chat area - header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="top-header">
        <h1>TalentScout AI Hiring Assistant</h1>
        <p>Your intelligent partner for candidate screening</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Display chat history
# ---------------------------------------------------------------------------

# On first load, send the greeting message
if not st.session_state.messages:
    st.session_state.messages.append(
        {"role": "assistant", "content": GREETING_PROMPT}
    )

# Render all messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Success banner when conversation has ended
# ---------------------------------------------------------------------------
if st.session_state.conversation_ended:
    st.markdown(
        '<div class="success-banner">'
        "Your profile has been saved! "
        "We will be in touch within 3-5 business days."
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Start New Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ---------------------------------------------------------------------------
# Chat input handling
# ---------------------------------------------------------------------------
if not st.session_state.conversation_ended:
    user_input = st.chat_input("Type your message here...")

    if user_input:
        # Sanitize and validate user input
        user_input = sanitize_input(user_input)
        if not user_input:
            st.warning("Please enter a valid message.")
            st.stop()

        # Check rate limit
        if st.session_state.message_count >= MAX_MESSAGES:
            st.warning("Session message limit reached. Please start a new session.")
            st.stop()

        # Display and store the user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Check for exit intent
        if detect_exit_intent(user_input):
            # End the conversation gracefully
            farewell = FAREWELL_PROMPT
            st.session_state.messages.append(
                {"role": "assistant", "content": farewell}
            )
            with st.chat_message("assistant"):
                st.markdown(farewell)

            # Extract and save whatever candidate info we have
            st.session_state.candidate_info = extract_candidate_info(
                st.session_state.messages
            )
            save_candidate_data(st.session_state.candidate_info)
            st.session_state.conversation_ended = True
            st.rerun()
        else:
            # Build formatted message history and call the LLM
            formatted_messages = format_chat_history(st.session_state.messages)

            with st.chat_message("assistant"):
                with st.spinner("Alex is typing..."):
                    response = get_llm_response(formatted_messages)
                st.markdown(response)

            # Store assistant response and increment message counter
            st.session_state.messages.append(
                {"role": "assistant", "content": response}
            )
            st.session_state.message_count += 1

            # Update candidate info in session state for the sidebar
            st.session_state.candidate_info = extract_candidate_info(
                st.session_state.messages
            )
