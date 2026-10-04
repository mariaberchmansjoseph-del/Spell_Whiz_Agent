"""
Script 02: Enrich words with definitions, etymology,
syllables, examples using free dictionary APIs.
Run: python scripts/02_enrich_words.py
"""

import json
import time
import requests
import sqlite3
from pathlib import Path
from tqdm import tqdm

Path("backend/data").mkdir(parents=True, exist_ok=True)

# Free dictionary API — no key needed
DICT_API   = "https://api.dictionaryapi.dev/api/v2/entries/en"
DATAMUSE   = "https://api.datamuse.com/words"


def fetch_word_data(word: str) -> dict:
    """Fetch word data from free dictionary API."""
    try:
        time.sleep(0.3)
        r = requests.get(
            f"{DICT_API}/{word}", timeout=10
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        if not data or not isinstance(data, list):
            return {}
        entry = data[0]

        # Extract phonetics
        phonetic   = entry.get("phonetic", "")
        audio_url  = ""
        phonetics  = entry.get("phonetics", [])
        for p in phonetics:
            if p.get("audio"):
                audio_url = p["audio"]
                break
            if not phonetic and p.get("text"):
                phonetic = p["text"]

        # Extract meanings
        meanings       = entry.get("meanings", [])
        definition     = ""
        part_of_speech = ""
        examples       = []

        for meaning in meanings:
            pos = meaning.get("partOfSpeech", "")
            defs = meaning.get("definitions", [])
            if defs and not definition:
                definition     = defs[0].get(
                    "definition", ""
                )
                part_of_speech = pos
                for d in defs[:3]:
                    ex = d.get("example", "")
                    if ex:
                        examples.append(ex)

        # Extract etymology
        etymology = entry.get("origin", "")

        return {
            "phonetic":      phonetic,
            "audio_url":     audio_url,
            "part_of_speech": part_of_speech,
            "definition":    definition,
            "examples":      examples[:3],
            "etymology":     etymology,
        }
    except Exception:
        return {}


def fetch_related_words(word: str) -> dict:
    """Fetch synonyms, antonyms from Datamuse."""
    try:
        synonyms = []
        antonyms = []

        time.sleep(0.2)
        r = requests.get(
            DATAMUSE,
            params={"rel_syn": word, "max": 5},
            timeout=10
        )
        if r.status_code == 200:
            synonyms = [w["word"] for w in r.json()]

        time.sleep(0.2)
        r2 = requests.get(
            DATAMUSE,
            params={"rel_ant": word, "max": 5},
            timeout=10
        )
        if r2.status_code == 200:
            antonyms = [w["word"] for w in r2.json()]

        return {
            "synonyms": synonyms,
            "antonyms": antonyms
        }
    except Exception:
        return {"synonyms": [], "antonyms": []}


def get_syllables(word: str) -> list:
    """
    Simple syllable splitter.
    Not perfect but good enough for display.
    """
    vowels  = "aeiouy"
    word    = word.lower()
    syllables = []
    current   = ""

    for i, char in enumerate(word):
        current += char
        if char in vowels:
            if i + 1 < len(word) and \
               word[i + 1] not in vowels:
                if i + 2 < len(word) and \
                   word[i + 2] not in vowels:
                    syllables.append(current)
                    current = ""
            elif i + 1 >= len(word):
                syllables.append(current)
                current = ""

    if current:
        if syllables:
            syllables[-1] += current
        else:
            syllables.append(current)

    return syllables if syllables else [word]


def make_child_definition(definition: str,
                           word: str) -> str:
    """Simplify definition for children."""
    if not definition:
        return f"A word that describes {word}."

    # Keep it short
    if len(definition) > 100:
        definition = definition[:100].rsplit(" ", 1)[0]

    return definition


def generate_mnemonic(word: str,
                       definition: str) -> str:
    """Simple mnemonic hint."""
    if not definition:
        return ""
    first_letters = " ".join(
        [c.upper() for c in word[:3] if c.isalpha()]
    )
    return (f"Remember: the first letters "
            f"'{first_letters}' in {word.upper()}")


def init_database() -> sqlite3.Connection:
    """Create SQLite database."""
    conn = sqlite3.connect("backend/data/words.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id              INTEGER PRIMARY KEY,
            word            TEXT UNIQUE NOT NULL,
            grade_level     INTEGER NOT NULL,
            difficulty      TEXT,
            syllables       TEXT,
            syllable_count  INTEGER,
            phonetic        TEXT,
            audio_url       TEXT,
            part_of_speech  TEXT,
            definition      TEXT,
            child_definition TEXT,
            examples        TEXT,
            mnemonic_text   TEXT,
            etymology       TEXT,
            synonyms        TEXT,
            antonyms        TEXT,
            is_enriched     INTEGER DEFAULT 0,
            source          TEXT
        )
    """)
    conn.commit()
    return conn


def enrich_all_words():
    """Load word lists and enrich each word."""

    wordlist_dir = Path("backend/data/wordlists")
    if not wordlist_dir.exists():
        print("❌ Run 01_download_wordlists.py first")
        return

    conn = init_database()

    # Grade to difficulty mapping
    difficulty_map = {
        2: "easy", 3: "easy", 4: "medium",
        5: "medium", 6: "hard", 7: "hard",
        8: "advanced", 9: "advanced", 10: "expert"
    }

    total_enriched = 0
    total_failed   = 0

    for grade_file in sorted(wordlist_dir.glob(
        "grade_*.json"
    )):
        with open(grade_file, encoding="utf-8") as f:
            data = json.load(f)

        grade      = data["grade"]
        words      = data["words"]
        difficulty = difficulty_map.get(grade, "medium")

        print(f"\nGrade {grade} ({len(words)} words)...")

        for word in tqdm(words, desc=f"  Grade {grade}"):
            # Skip if already in database
            existing = conn.execute(
                "SELECT id FROM words WHERE word=?",
                (word,)
            ).fetchone()
            if existing:
                continue

            # Fetch data
            word_data    = fetch_word_data(word)
            related      = fetch_related_words(word)
            syllables    = get_syllables(word)
            definition   = word_data.get("definition", "")
            child_def    = make_child_definition(
                definition, word
            )
            mnemonic     = generate_mnemonic(
                word, definition
            )

            # Save to database
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO words
                    (word, grade_level, difficulty,
                     syllables, syllable_count,
                     phonetic, audio_url,
                     part_of_speech, definition,
                     child_definition, examples,
                     mnemonic_text, etymology,
                     synonyms, antonyms,
                     is_enriched, source)
                    VALUES
                    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    word, grade, difficulty,
                    json.dumps(syllables),
                    len(syllables),
                    word_data.get("phonetic", ""),
                    word_data.get("audio_url", ""),
                    word_data.get("part_of_speech", ""),
                    definition,
                    child_def,
                    json.dumps(
                        word_data.get("examples", [])
                    ),
                    mnemonic,
                    word_data.get("etymology", ""),
                    json.dumps(related.get(
                        "synonyms", []
                    )),
                    json.dumps(related.get(
                        "antonyms", []
                    )),
                    1 if definition else 0,
                    "dictionaryapi.dev"
                ))
                conn.commit()
                total_enriched += 1
            except Exception as e:
                total_failed += 1

    conn.close()

    print(f"\n{'='*55}")
    print(f"ENRICHMENT COMPLETE")
    print(f"{'='*55}")
    print(f"Enriched: {total_enriched:,}")
    print(f"Failed:   {total_failed:,}")
    print(f"Database: backend/data/words.db")
    print(f"\nNext: python scripts/03_build_agent.py")


if __name__ == "__main__":
    print("="*55)
    print("WORD ENRICHMENT PIPELINE")
    print("="*55)
    enrich_all_words()