"""
Script 03: Generate audio pronunciations for all words.
Uses gTTS (Google Text-to-Speech) — free, no API key.
Run: python scripts/03_generate_audio.py
"""

import json
import time
import sqlite3
from pathlib import Path
from gtts import gTTS
from tqdm import tqdm

Path("backend/data/audio").mkdir(
    parents=True, exist_ok=True
)
DB_PATH = "backend/data/words.db"


def generate_audio():
    conn  = sqlite3.connect(DB_PATH)
    words = conn.execute(
        "SELECT word, grade_level FROM words "
        "ORDER BY grade_level, word"
    ).fetchall()
    conn.close()

    print("="*55)
    print("AUDIO GENERATION")
    print("="*55)
    print(f"Words to process: {len(words)}")
    print()

    success  = 0
    skipped  = 0
    failed   = 0

    for word, grade in tqdm(words, desc="Generating"):
        audio_path = Path(
            f"backend/data/audio/{word}.mp3"
        )

        # Skip if already exists
        if audio_path.exists():
            skipped += 1
            continue

        try:
            # Generate slow pronunciation for learning
            tts = gTTS(
                text=word,
                lang="en",
                slow=True
            )
            tts.save(str(audio_path))
            success += 1
            time.sleep(0.3)

        except Exception as e:
            failed += 1

    # Update database with audio file paths
    conn = sqlite3.connect(DB_PATH)
    for word, grade in words:
        audio_path = f"backend/data/audio/{word}.mp3"
        if Path(audio_path).exists():
            conn.execute(
                "UPDATE words SET audio_url=? "
                "WHERE word=?",
                (audio_path, word)
            )
    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"AUDIO COMPLETE")
    print(f"{'='*55}")
    print(f"Generated: {success:,}")
    print(f"Skipped:   {skipped:,}")
    print(f"Failed:    {failed:,}")
    print(f"Location:  backend/data/audio/")
    print(f"\nNext: python scripts/04_build_vector_index.py")


if __name__ == "__main__":
    generate_audio()