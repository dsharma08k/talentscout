# TalentScout Hiring Assistant

## Project Overview

TalentScout is an AI-powered hiring assistant chatbot built for a technology recruitment agency. It conducts structured candidate screening interviews through a conversational interface, collecting personal and professional details one question at a time, then generating tailored technical interview questions based on the candidate's reported tech stack.

The application is built with Python, Streamlit, and the Groq API (serving the Llama 3.3 70B model via an OpenAI-compatible interface). It runs entirely in the browser as a single-page Streamlit application.

### Key Features

- Conversational candidate screening that collects seven required fields
- Automatic tech stack detection from candidate responses
- Dynamic generation of 3-5 technical interview questions per technology
- Real-time sidebar display of collected candidate information
- Local JSON file storage for candidate data
- Graceful conversation exit handling with keyword detection
- Input validation for email and phone number formats
- Off-topic redirection to keep the conversation focused
- Dark-themed, professional UI with custom CSS styling

## Tech Stack Used

- **Python 3.9+** - Core programming language
- **Streamlit** - Web UI framework for the chat interface
- **Groq API (Llama 3.3 70B)** - LLM inference via OpenAI-compatible endpoint
- **python-dotenv** - Environment variable management for API key storage

## Installation and Setup

### Prerequisites

- Python 3.9 or higher installed on your system
- A Groq API key (obtain one free at https://console.groq.com/keys)

### Step-by-step Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd talentscout
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**

   On Windows:
   ```bash
   venv\Scripts\activate
   ```

   On macOS / Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Configure your API key**

   Open the `.env` file in the project root and replace the placeholder value:
   ```
   GROQ_API_KEY=gsk-your-actual-api-key-here
   ```

6. **Run the application**

   ```bash
   streamlit run app.py
   ```

   The app will open in your default browser at `http://localhost:8501`.

## Usage Guide

1. **Greeting** - The bot introduces itself as Alex from TalentScout and asks for your full name.
2. **Information collection** - Alex asks for each of the seven required fields one at a time:
   - Full Name
   - Email Address
   - Phone Number
   - Years of Experience
   - Desired Position(s)
   - Current Location
   - Tech Stack (languages, frameworks, databases, tools)
3. **Technical questions** - After all information is collected, Alex generates 3-5 technical questions for each technology in the reported tech stack.
4. **Answer questions** - The candidate answers the technical questions conversationally.
5. **End the session** - Type any exit keyword ("bye", "exit", "quit", "goodbye", "done", "stop", "end", or "finish") to end the conversation.
6. **Data saved** - Candidate information is automatically written to `candidates_data.json` in the project directory.

The sidebar displays collected candidate info in real time as the conversation progresses.

## Prompt Design Explanation

### System Prompt Structure

The system prompt defines the LLM's persona (Alex), its strict behavioral rules, and the exact sequence of information to collect. By embedding all instructions in a single system message that is prepended to every API call, the model maintains consistent behavior throughout the conversation. Key design decisions:

- **One-at-a-time collection**: The prompt explicitly instructs the model to never ask for multiple fields simultaneously, ensuring a natural conversational flow.
- **Validation instructions**: The prompt tells the model to check for invalid inputs (like letters in a phone number) and request re-entry, adding a layer of validation on top of the regex checks in the code.
- **Topic control**: Explicit rules about staying on topic prevent the model from being sidetracked by off-topic user messages.

### Technical Question Generation

When the candidate provides their tech stack, the system prompt instructs the model to generate 3-5 questions per technology. A separate `QUESTION_GENERATION_PROMPT` template with a `{tech_stack}` placeholder is available for standalone question generation, but in the main flow, the system prompt handles this transition naturally as part of the conversation.

### Context Maintenance

The full `st.session_state.messages` list is passed to the Groq API on every call. This means the model always has access to the complete conversation history, preventing it from re-asking questions or losing track of what has been collected. The system prompt is prepended as the first message in every request.

## Project Structure

```
talentscout/
  app.py              - Main Streamlit application with UI, chat logic, and API calls
  prompts.py          - All prompt templates (system, greeting, question generation, etc.)
  utils.py            - Utility functions for validation, session state, and data handling
  config.py           - Configuration and environment variable loading
  requirements.txt    - Python package dependencies
  .env                - Environment variables (API key) - not committed to version control
  README.md           - Project documentation
  candidates_data.json - Generated at runtime to store candidate screening data
```

### File Responsibilities

- **config.py** - Loads the `.env` file using python-dotenv and exposes `GROQ_API_KEY`, `GROQ_BASE_URL`, `MODEL_NAME`, `MAX_TOKENS`, and `TEMPERATURE` as module-level constants.
- **prompts.py** - Contains five prompt templates: `SYSTEM_PROMPT`, `GREETING_PROMPT`, `QUESTION_GENERATION_PROMPT`, `FALLBACK_PROMPT`, and `FAREWELL_PROMPT`.
- **utils.py** - Provides helper functions for session state initialization, exit keyword detection, email/phone validation, candidate info extraction from chat history, JSON file saving, and chat history formatting.
- **app.py** - Orchestrates the entire application: page config, custom CSS injection, sidebar rendering, chat message display, user input handling, LLM calls, and conversation state management.

## Challenges and Solutions

### Maintaining Conversation Context

**Challenge**: LLMs are stateless - each API call is independent, so the model has no memory of previous turns unless explicitly provided.

**Solution**: The complete message history from `st.session_state.messages` is sent with every API request, with the system prompt prepended. This ensures the model always has full context to continue the conversation naturally.

### Validating User Inputs

**Challenge**: Users may provide malformed email addresses, phone numbers with letters, or non-numeric experience values. Relying solely on the LLM for validation is unreliable.

**Solution**: A two-layer approach is used. The system prompt instructs the LLM to check for and reject invalid inputs. Additionally, `utils.py` provides regex-based `validate_email()` and `validate_phone()` functions for programmatic validation. The LLM acts as the primary validator in the conversational flow.

### Keeping the Bot on Topic

**Challenge**: Users may attempt to steer the conversation off-topic, ask the bot unrelated questions, or try prompt injection to override its instructions.

**Solution**: The system prompt contains explicit instructions to only discuss hiring and recruitment topics and to politely redirect off-topic messages. The structured field-by-field collection flow also creates natural guardrails.

### Sensitive Data Handling

**Challenge**: Candidate personal data (name, email, phone) must be handled responsibly.

**Solution**: All data is stored locally in `candidates_data.json` and is never transmitted to any third-party service beyond the Groq API (which is necessary for the LLM inference). No data is logged to external servers or analytics platforms.

## Data Privacy

- All candidate data is stored locally in `candidates_data.json` on the machine running the application.
- No data is sent to third-party services other than Groq for generating LLM responses.
- The conversation content sent to Groq is subject to Groq's data usage policies.
- The application follows a data minimization approach: only the information required for screening is collected.
- For production deployment, additional measures such as encryption at rest, access controls, and explicit user consent should be implemented.
- The `.env` file containing the API key should never be committed to version control. Add it to `.gitignore`.
