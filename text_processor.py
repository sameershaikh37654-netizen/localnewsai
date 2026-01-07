

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

from utils import evaluate_safety
from safe_json import safe_json_parse

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_text(text: str) -> dict:
    # 🔒 STRICT COMPLIANCE PROMPT
    prompt = """
You are a news compliance AI.

You MUST respond with ONLY valid JSON.
Do NOT include explanations, markdown, or text outside JSON.

Evaluate the text strictly against:
- Legal rules: court orders, national security, victim identity, investigations
- Editorial standards: sensationalism, verification, right of reply
- Ethical rules: communal harmony, defamation, deepfakes
- Broadcasting restrictions: adult content, violence, false claims

JSON schema (EXACT):
{
  "summary": "",
  "fake_news": false,
  "unverified_claims": false,
  "hate_speech": false,
  "political_bias": false,
  "adult_content": false,
  "violence": false,
  "national_security_risk": false,
  "communal_tension": false,
  "defamation_risk": false,
  "court_violation": false,
  "victim_identity_exposed": false,
  "investigation_interference": false,
  "deepfake_or_ai_manipulation": false,
  "copyright_violation": false
}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt + "\nTEXT:\n" + text
    )

    try:
        data = safe_json_parse(response.output_text)
    except Exception:
        # ⚠️ FAIL-SAFE: FORCE MANUAL REVIEW
        data = {
            "summary": "AI output could not be parsed safely. Manual editorial review required.",
            "fake_news": False,
            "unverified_claims": True,
            "hate_speech": False,
            "political_bias": False,
            "adult_content": False,
            "violence": False,
            "national_security_risk": False,
            "communal_tension": False,
            "defamation_risk": False,
            "court_violation": False,
            "victim_identity_exposed": False,
            "investigation_interference": False,
            "deepfake_or_ai_manipulation": False,
            "copyright_violation": False
        }

    return evaluate_safety(data)