

import os
import base64
import cv2
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from utils import evaluate_safety
from safe_json import safe_json_parse

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_image(image_input):
    """
    Accepts:
    - Streamlit uploaded file
    - OpenCV numpy frame
    Returns:
    - dict with keys: summary, decision, review_reasons
    """

    # -------- HANDLE INPUT TYPES --------
    if isinstance(image_input, np.ndarray):
        success, buffer = cv2.imencode(".jpg", image_input)
        if not success:
            raise ValueError("Failed to encode video frame")
        image_bytes = buffer.tobytes()
    else:
        image_bytes = image_input.read()

    # -------- BASE64 ENCODE --------
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_data_url = f"data:image/jpeg;base64,{image_base64}"

    # -------- GPT PROMPT --------
    prompt = """
You are a digital forensics and news compliance AI.

Your task is to identify SAFETY and AUTHENTICITY RISKS.

IMPORTANT:
- If there is ANY reasonable suspicion of AI generation or manipulation,
  mark suspected_ai_generated_or_manipulated as true.
- False positives are acceptable.
- False negatives are NOT acceptable.

Check for:
- Deepfake artifacts
- AI-generated faces or bodies
- Unreal textures or lighting
- Diffusion artifacts
- Face swaps
- Manipulated visuals

Return ONLY valid JSON.

Schema:
{
  "summary": "",
  "suspected_ai_generated_or_manipulated": false,
  "adult_content": false,
  "violence": false,
  "hate_speech": false,
  "political_bias": false,
  "national_security_risk": false,
  "defamation_risk": false,
  "copyright_violation": false
}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_data_url}
                ]
            }]
        )

        # -------- SAFE JSON PARSE --------
        data = safe_json_parse(response.output_text)

    except Exception:
        # fallback if GPT fails
        data = {
            "suspected_ai_generated_or_manipulated": True
        }

    # -------- DECISION LOGIC --------
    suspected_ai = data.get("suspected_ai_generated_or_manipulated", False)

    if suspected_ai:
        return {
            "summary": "Image shows indicators of possible AI generation or manipulation.",
            "decision": "REVIEW",
            "review_reasons": ["suspected_ai_generated_or_manipulated"]
        }

    return {
        "summary": "No major editorial or authenticity risks detected in image.",
        "decision": "SAFE",
        "review_reasons": []
    }