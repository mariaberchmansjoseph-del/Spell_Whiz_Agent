"""
Script 04b: Enrich words in small daily batches.
Respects Groq free tier limits.
Run daily: python scripts/04b_enrich_batch.py
"""

import os
import json
import time
import sqlite3
from groq import Groq
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY   = os.getenv("GROQ_API_KEY", "")
MODEL      = "openai/gpt-oss-20b"
DB_PATH    = "backend/data/words.db"
BATCH_SIZE = 150   # safe daily limit
DELAY      = 3.0   # seconds between words


def enrich_word(client, word, grade):
    if grade <= 3:
        age = "7-8 year old"
    elif grade <= 5:
        age = "10 year old"
    elif grade <= 7:
        age = "12 year old"
    else:
        age = "15 year old"

    prompt = (
        f'Define the word "{word}" for a {age} student.\n'
        f'Return JSON only:\n'
        f'{{"definition":"one sentence",'
        f'"child_definition":"simple version",'
        f'"part_of_speech":"noun/verb/adjective/adverb",'
        f'"example":"one example sentence",'
        f'"mnemonic":"spelling memory trick",'
        f'"synonyms":["word1","word2"]}}'
    )

    try:
        r = client.chat.completions.create(
            model    = MODEL,
            messages = [
                {"role": "system",
                 "content": "Dictionary assistant. "
                            "JSON only. No markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature = 0.1,
            max_tokens  = 300,
        )
        text = r.choices[0].message.content
        if not text or len(text) < 10:
            return {}
        text = text.strip().strip("```json").strip("```")
        return json.loads(text)
    except Exception:
        return {}


def run_batch():
    if not GROQ_KEY:
        print("No GROQ_API_KEY in .env")
        return

    client = Groq(api_key=GROQ_KEY)
    conn   = sqlite3.connect(DB_PATH)

    missing = conn.execute("""
        SELECT word, grade_level FROM words
        WHERE is_enriched = 0
           OR definition IS NULL
           OR length(definition) < 5
        ORDER BY grade_level, word
        LIMIT ?
    """, (BATCH_SIZE,)).fetchall()

    conn.close()

    if not missing:
        print("All words enriched!")
        return

    print(f"Enriching batch of {len(missing)} words...")
    success = 0
    conn    = sqlite3.connect(DB_PATH)

    for word, grade in tqdm(missing):
        data = enrich_word(client, word, grade)

        if data and data.get("definition"):
            examples = []
            if data.get("example"):
                examples = [data["example"]]

            conn.execute("""
                UPDATE words SET
                  definition       = ?,
                  child_definition = ?,
                  part_of_speech   = ?,
                  examples         = ?,
                  mnemonic_text    = ?,
                  synonyms         = ?,
                  is_enriched      = 1,
                  updated_at       = datetime('now')
                WHERE word = ?
            """, (
                data.get("definition", ""),
                data.get("child_definition", ""),
                data.get("part_of_speech", ""),
                json.dumps(examples),
                data.get("mnemonic", ""),
                json.dumps(data.get("synonyms", [])),
                word,
            ))
            conn.commit()
            success += 1

        time.sleep(DELAY)

    conn.close()

    conn     = sqlite3.connect(DB_PATH)
    total    = conn.execute(
        "SELECT COUNT(*) FROM words"
    ).fetchone()[0]
    enriched = conn.execute(
        "SELECT COUNT(*) FROM words WHERE is_enriched=1"
    ).fetchone()[0]
    remaining = total - enriched
    conn.close()

    print(f"\nBatch complete: {success}/{len(missing)}")
    print(f"Total enriched: {enriched}/{total}")
    print(f"Remaining:      {remaining}")
    if remaining > 0:
        days = remaining // BATCH_SIZE + 1
        print(f"Run again tomorrow. ~{days} days to complete.")


if __name__ == "__main__":
    run_batch()