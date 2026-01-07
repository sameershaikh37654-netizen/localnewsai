

import json
import re

def safe_json_parse(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Empty AI response")

    # Remove markdown code blocks
    text = re.sub(r"```json|```", "", text).strip()

    # Extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")

    return json.loads(match.group())