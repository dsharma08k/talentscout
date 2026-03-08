"""
Configuration module for TalentScout Hiring Assistant.
Loads environment variables and stores application-wide settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Model settings
MODEL_NAME = "llama-3.3-70b-versatile"
MAX_TOKENS = 1000
TEMPERATURE = 0.7
