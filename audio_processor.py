

# audio_processor.py
import os
from openai import OpenAI
from text_processor import analyze_text
from dotenv import load_dotenv

load_dotenv()  # Load OPENAI_API_KEY from .env

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_audio(audio_file):
    """
    Transcribe audio using OpenAI Whisper API and send text to moderation.
    Supports: .mp3, .wav, .m4a
    Returns moderation + editorial review JSON.
    """
    try:
        # Ensure file is opened in binary mode
        if isinstance(audio_file, str):
            file_obj = open(audio_file, "rb")
        else:
            # If uploaded file from Streamlit
            file_obj = audio_file

        # Transcribe using OpenAI Whisper
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=file_obj
        )

        # Get the transcribed text
        text = transcription.text

        # Pass the text to your text moderation workflow
        result = analyze_text(text)

        # Close file if opened
        if isinstance(audio_file, str):
            file_obj.close()

        return result

    except Exception as e:
        return {
            "summary": "",
            "error": str(e),
            "decision": "ERROR",
            "manual_review": False,
            "unsafe": False,
            "editor_approved": False,
            "editor_comments": "",
            "review_reasons": []
        }