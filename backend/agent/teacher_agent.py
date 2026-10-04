"""
Teacher Agent (Bee): main interaction with the child.
Warm, encouraging, child-safe spelling coach.
backend/agent/teacher_agent.py
"""

import os
import random
import sqlite3
import json
from groq import Groq
from dotenv import load_dotenv
from backend.agent.safety_filter   import (
    check_response, is_appropriate_input
)
from backend.agent.evaluator_agent import EvaluatorAgent

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
MODEL    = "openai/gpt-oss-20b"
DB_PATH  = "backend/data/words.db"

SYSTEM_PROMPT = """You are Bee — a friendly spelling coach
for children aged 7-15.

YOUR PERSONALITY:
- Warm, patient, enthusiastic
- Celebrate every attempt — even wrong ones
- Use the child's name frequently
- Short sentences — max 3 sentences per response
- Make learning feel like an adventure
- One emoji maximum per message

RULES (never break these):
- Never say: wrong, incorrect, bad, failed
- Always end with encouragement
- Never discuss anything except spelling and words
- Never share external websites or links
- Keep language age-appropriate at all times"""


class TeacherAgent:

    def __init__(self):
        self.client    = Groq(api_key=GROQ_KEY) \
                         if GROQ_KEY else None
        self.evaluator = EvaluatorAgent()

    def get_word_data(self, word: str) -> dict:
        """Fetch word details from database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            row  = conn.execute(
                "SELECT * FROM words WHERE word=?",
                (word.lower(),)
            ).fetchone()
            conn.close()

            if not row:
                return {"word": word}

            cols = [
                "id", "word", "grade_level",
                "difficulty", "syllables",
                "syllable_count", "phonetic",
                "audio_url", "part_of_speech",
                "definition", "child_definition",
                "examples", "mnemonic_text",
                "etymology", "synonyms", "antonyms",
                "is_enriched", "source"
            ]
            data = dict(zip(cols, row))

            for field in ["syllables", "examples",
                          "synonyms", "antonyms"]:
                if data.get(field):
                    try:
                        data[field] = json.loads(
                            data[field]
                        )
                    except Exception:
                        pass

            return data
        except Exception:
            return {"word": word}

    def quiz_response(
        self,
        student_name:    str,
        word:            str,
        student_attempt: str,
        attempt_number:  int,
        grade_level:     int = 5
    ) -> dict:
        """Generate quiz feedback for a spelling attempt."""

        # Safety check on input
        input_check = is_appropriate_input(student_attempt)
        if not input_check["ok"]:
            return {
                "response":    "Let's try again with "
                               "just the spelling! 🐝",
                "is_correct":  False,
                "eval":        {},
                "word_data":   {}
            }

        # Evaluate spelling
        eval_result = self.evaluator.evaluate(
            word, student_attempt
        )
        word_data   = self.get_word_data(word)
        is_correct  = eval_result.get("is_correct", False)

        # Generate response
        if is_correct:
            response = self._correct_response(
                student_name, word, word_data
            )
        else:
            response = self._incorrect_response(
                student_name, word, word_data,
                eval_result, attempt_number
            )

        # Safety check on output
        safety = check_response(response)
        final  = (safety["fixed"]
                  if not safety["safe"]
                  else response)

        return {
            "response":   final,
            "is_correct": is_correct,
            "eval":       eval_result,
            "word_data":  word_data,
            "safe":       safety["safe"]
        }

    def _correct_response(
        self,
        name:      str,
        word:      str,
        word_data: dict
    ) -> str:
        """Generate encouraging correct answer response."""
        celebrations = [
            f"🌟 YES! {name} got it perfectly!",
            f"⭐ Brilliant, {name}! That's correct!",
            f"🎉 Amazing, {name}! Perfect spelling!",
            f"🏆 Outstanding, {name}! You nailed it!",
        ]
        base = random.choice(celebrations)

        # Add a fun fact if available
        etymology = word_data.get("etymology", "")
        if etymology and len(etymology) > 10:
            fact = f" Fun fact: {etymology[:100]}"
            return base + fact

        definition = word_data.get(
            "child_definition", ""
        )
        if definition:
            return base + f" {word.capitalize()} means: "\
                          f"{definition[:80]}"

        return base + " Keep up the fantastic work!"

    def _incorrect_response(
        self,
        name:        str,
        word:        str,
        word_data:   dict,
        eval_result: dict,
        attempt:     int
    ) -> str:
        """Generate helpful incorrect answer response."""
        syllables = word_data.get("syllables", [])
        mnemonic  = word_data.get("mnemonic_text", "")

        if attempt == 1:
            # First wrong: give syllable hint
            if syllables and isinstance(syllables, list):
                syl_str = "-".join(syllables)
                return (
                    f"Great try, {name}! 💪 "
                    f"Here's a hint — try breaking "
                    f"it down: {syl_str}. "
                    f"Give it another go!"
                )
            return (
                f"Great try, {name}! 💪 "
                f"Listen carefully to each sound "
                f"in the word. Try again!"
            )

        elif attempt == 2:
            # Second wrong: give mnemonic
            if mnemonic:
                return (
                    f"So close, {name}! 🌟 "
                    f"Here's a memory trick: "
                    f"{mnemonic[:100]}. "
                    f"One more try!"
                )
            hint = eval_result.get("hint_text", "")
            return (
                f"So close, {name}! 🌟 "
                f"{hint} "
                f"You've got this!"
            )

        else:
            # Third wrong: show answer and explanation
            definition = word_data.get(
                "child_definition", ""
            )
            return (
                f"That's a really tricky one, {name}! "
                f"The correct spelling is: {word}. "
                f"{definition[:80] if definition else ''} "
                f"We'll come back to this word — "
                f"you're doing amazingly! 💪"
            )

    def learn_response(
        self,
        student_name: str,
        word:         str,
        grade_level:  int = 5
    ) -> dict:
        """Generate a learn mode response for a word."""
        word_data  = self.get_word_data(word)
        syllables  = word_data.get("syllables", [])
        definition = word_data.get(
            "child_definition",
            word_data.get("definition", "")
        )
        etymology  = word_data.get("etymology", "")
        examples   = word_data.get("examples", [])
        mnemonic   = word_data.get("mnemonic_text", "")

        syl_str   = "-".join(syllables) \
                    if isinstance(syllables, list) \
                    else word
        phonetic  = word_data.get("phonetic", "")

        response  = (
            f"Let's learn '{word}'! 📚 "
            f"Pronunciation: {phonetic or word} "
            f"({syl_str}). "
            f"It means: {definition[:100] if definition else 'see below'}. "
        )

        if etymology:
            response += (
                f"It comes from {etymology[:80]}. "
            )

        if mnemonic:
            response += f"Memory trick: {mnemonic[:80]}. "

        if examples:
            response += (
                f"Example: '{examples[0][:100]}'. "
            )

        response += (
            f"Now, {student_name}, "
            f"can you spell '{word}'? Give it a try! 🐝"
        )

        safety = check_response(response)
        final  = (safety["fixed"]
                  if not safety["safe"]
                  else response)

        return {
            "response":  final,
            "word_data": word_data,
            "word":      word
        }