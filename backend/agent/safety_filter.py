"""
Content safety filter for children's spelling app.
Two layers: rule-based (fast) + LLM check (thorough).
backend/agent/safety_filter.py
"""

import re

# Words never allowed in responses to children
BLOCKED_WORDS = {
    "wrong", "incorrect", "bad", "stupid", "dumb",
    "idiot", "fail", "failed", "failure", "terrible",
    "awful", "horrible", "worst", "loser", "pathetic",
    "useless", "hopeless", "never", "impossible",
    "give up", "quit", "can't", "cannot do",
}

POSITIVE_ENDINGS = [
    "You can do this!",
    "Keep going!",
    "You're doing great!",
    "Amazing effort!",
    "You're getting better every day!",
    "Practice makes perfect!",
]


def check_response(text: str) -> dict:
    """
    Layer 1: Rule-based safety check.
    Returns: {safe: bool, issues: list, fixed: str}
    """
    if not text:
        return {"safe": False, "issues": ["empty"],
                "fixed": "Let's try again!"}

    issues   = []
    text_low = text.lower()

    # Check for blocked words
    for word in BLOCKED_WORDS:
        if word in text_low:
            issues.append(f"negative word: {word}")

    # Check for URLs
    if re.search(r'http|www\.', text_low):
        issues.append("contains URL")

    # Check response ends positively
    last_sentence = text.strip().split(".")[-1].strip()
    has_positive  = any(
        p.lower() in text_low
        for p in ["great", "amazing", "wonderful",
                  "excellent", "fantastic", "awesome",
                  "brilliant", "perfect", "good job",
                  "well done", "keep", "try", "you can"]
    )

    if not has_positive:
        issues.append("missing encouragement")

    if issues:
        fixed = fix_response(text, issues)
        return {"safe": False, "issues": issues,
                "fixed": fixed}

    return {"safe": True, "issues": [], "fixed": text}


def fix_response(text: str, issues: list) -> str:
    """Auto-fix common safety issues."""
    # Replace negative words
    replacements = {
        "wrong":     "great try",
        "incorrect": "almost there",
        "bad":       "interesting",
        "failed":    "tried hard",
        "failure":   "learning moment",
        "terrible":  "tricky",
        "awful":     "challenging",
    }

    fixed = text
    for bad, good in replacements.items():
        fixed = re.sub(
            rf'\b{bad}\b', good, fixed,
            flags=re.IGNORECASE
        )

    # Add encouragement if missing
    if "missing encouragement" in issues:
        import random
        fixed += " " + random.choice(POSITIVE_ENDINGS)

    # Remove URLs
    fixed = re.sub(r'https?://\S+', '', fixed)
    fixed = re.sub(r'www\.\S+', '', fixed)
    fixed = re.sub(r'\s+', ' ', fixed).strip()

    return fixed


def is_appropriate_input(text: str) -> dict:
    """Check if student input is appropriate."""
    if not text or len(text.strip()) == 0:
        return {"ok": False,
                "reason": "empty input"}

    if len(text) > 500:
        return {"ok": False,
                "reason": "input too long"}

    # Only allow letters, spaces, punctuation
    if re.search(r'[^\w\s\'\-\.,!?]', text):
        return {"ok": False,
                "reason": "unusual characters"}

    return {"ok": True, "reason": ""}