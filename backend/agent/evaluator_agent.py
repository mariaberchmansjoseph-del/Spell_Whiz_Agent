"""
Evaluator Agent: checks spelling accuracy.
Returns structured evaluation with error categorisation.
backend/agent/evaluator_agent.py
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
MODEL    = "openai/gpt-oss-20b"

SYSTEM_PROMPT = """You evaluate children's spelling attempts.
Given the correct word and the child's attempt, return JSON.

ERROR TYPES:
  phonetic_error:   sounds right but wrong letters
  double_letter:    wrong doubling decision
  missing_letter:   left out a letter
  extra_letter:     added an extra letter
  transposition:    swapped adjacent letters
  silent_letter:    forgot or added silent letter
  vowel_confusion:  wrong vowel choice
  wrong_ending:     wrong suffix
  correct:          spelling is correct

Return ONLY valid JSON:
{
  "is_correct": false,
  "similarity": 0.85,
  "error_type": "double_letter",
  "wrong_part": "nec-c-essary",
  "correct_part": "nec-essary",
  "hint_type": "syllable",
  "hint_text": "Try: ne-ces-sa-ry",
  "encouragement": "So close! Just one letter off!"
}"""


class EvaluatorAgent:

    def __init__(self):
        self.client = Groq(api_key=GROQ_KEY) \
                      if GROQ_KEY else None

    def evaluate(
        self,
        correct_word:    str,
        student_attempt: str
    ) -> dict:
        """Evaluate a spelling attempt."""

        # Quick exact match check
        if correct_word.lower() == \
                student_attempt.lower().strip():
            return {
                "is_correct":   True,
                "similarity":   1.0,
                "error_type":   "correct",
                "wrong_part":   "",
                "correct_part": "",
                "hint_type":    "",
                "hint_text":    "",
                "encouragement": "Perfect spelling!"
            }

        if not self.client:
            return self._simple_evaluate(
                correct_word, student_attempt
            )

        prompt = (f"Correct word: {correct_word}\n"
                  f"Student typed: {student_attempt}")

        try:
            response = self.client.chat.completions.create(
                model    = MODEL,
                messages = [
                    {"role": "system",
                     "content": SYSTEM_PROMPT},
                    {"role": "user",
                     "content": prompt}
                ],
                temperature = 0.0,
                max_tokens  = 200,
            )
            text   = response.choices[0].message.content
            result = json.loads(text)
            return result

        except Exception:
            return self._simple_evaluate(
                correct_word, student_attempt
            )

    def _simple_evaluate(
        self,
        correct: str,
        attempt: str
    ) -> dict:
        """Fallback evaluation without LLM."""
        correct = correct.lower().strip()
        attempt = attempt.lower().strip()

        # Calculate similarity
        matches = sum(
            1 for a, b in zip(correct, attempt) if a == b
        )
        similarity = matches / max(len(correct), 1)

        # Detect error type
        error_type = "missing_letter"
        if len(attempt) > len(correct):
            error_type = "extra_letter"
        elif len(attempt) == len(correct):
            error_type = "wrong_letter"

        return {
            "is_correct":   False,
            "similarity":   round(similarity, 2),
            "error_type":   error_type,
            "wrong_part":   attempt,
            "correct_part": correct,
            "hint_type":    "syllable",
            "hint_text":    f"Check each letter carefully",
            "encouragement": "Great try! Almost there!"
        }