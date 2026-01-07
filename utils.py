
from rules import AUTO_BLOCK, MANUAL_REVIEW

def evaluate_safety(results: dict) -> dict:
    auto_block = any(results.get(cat, False) for cat in AUTO_BLOCK)
    manual_review = any(results.get(cat, False) for cat in MANUAL_REVIEW)

    if auto_block:
        decision = "BLOCK"
    elif manual_review:
        decision = "REVIEW"
    else:
        decision = "SAFE"

    review_reasons = [k for k in MANUAL_REVIEW if results.get(k)]

    results.update({
        "decision": decision,
        "manual_review": manual_review,
        "unsafe": auto_block,
        "editor_approved": False,
        "editor_comments": "",
        "review_reasons": review_reasons
    })

    return results