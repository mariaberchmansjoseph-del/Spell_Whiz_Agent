import os
import json
import sqlite3
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

DB_PATH  = "backend/data/words.db"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
MODEL    = "openai/gpt-oss-20b"

test_words = [
    ("necessary",    4),
    ("ephemeral",    8),
    ("photograph",   5),
    ("conscientious", 7),
    ("rhythm",       3),
]

client = Groq(api_key=GROQ_KEY)

for word, grade in test_words:
    prompt = f"""For the spelling word "{word}" (grade {grade}):

Provide this information as JSON:
{{
  "definition": "one clear sentence defining {word}",
  "child_definition": "simple explanation for grade {grade}",
  "part_of_speech": "noun or verb or adjective or adverb",
  "example1": "a sentence using {word}",
  "example2": "another sentence using {word}",
  "mnemonic": "memory trick to spell {word}",
  "synonyms": ["similar1", "similar2"],
  "root": "Latin or Greek root if applicable"
}}"""

    try:
        response = client.chat.completions.create(
            model    = MODEL,
            messages = [
                {"role": "system",
                 "content": "You are a dictionary. "
                            "Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature = 0.1,
            max_tokens  = 400,
        )
        text = response.choices[0].message.content
        data = json.loads(text)
        print(f"✅ {word}: {data.get('definition','')[:60]}")
    except Exception as e:
        print(f"❌ {word}: {str(e)[:60]}")