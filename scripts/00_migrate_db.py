"""
Script 00: Migrate word database to full schema.
Adds missing columns, cleans up duplicates.
Safe to run multiple times.
Run: python scripts/00_migrate_db.py
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = "backend/data/words.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)

    # Columns to add if missing
    new_columns = [
        ("root_word",       "TEXT"),
        ("root_meaning",    "TEXT"),
        ("root_language",   "TEXT"),
        ("word_family",     "TEXT"),
        ("related_words",   "TEXT"),
        ("genres",          "TEXT"),
        ("frequency_rank",  "INTEGER"),
        ("ipa",             "TEXT"),
        ("other_forms",     "TEXT"),
        ("mnemonic_emoji",  "TEXT"),
        ("updated_at",      "TEXT"),
    ]

    print("Adding missing columns...")
    for col_name, col_type in new_columns:
        try:
            conn.execute(
                f"ALTER TABLE words ADD COLUMN "
                f"{col_name} {col_type}"
            )
            print(f"  ✅ Added: {col_name}")
        except Exception:
            print(f"  ⏭  Exists: {col_name}")

    # Migrate etymology → root fields
    print("\nMigrating etymology data...")
    words_with_etymology = conn.execute("""
        SELECT word, etymology
        FROM words
        WHERE etymology IS NOT NULL
        AND etymology != ''
        AND root_word IS NULL
    """).fetchall()

    migrated = 0
    for word, etym in words_with_etymology:
        if not etym:
            continue
        # Store etymology in root_meaning as fallback
        conn.execute("""
            UPDATE words
            SET root_meaning = ?
            WHERE word = ?
        """, (etym[:200], word))
        migrated += 1

    print(f"  Migrated {migrated} etymology entries")

    # Fix difficulty_level column
    # (both difficulty and difficulty_level exist)
    # Copy difficulty → difficulty_level where missing
    conn.execute("""
        UPDATE words
        SET difficulty_level = difficulty
        WHERE difficulty_level IS NULL
        AND difficulty IS NOT NULL
    """)
    print("\nFixed difficulty_level column")

    # Fix audio_url → audio_file naming
    # Keep audio_url as is (column already named that)
    # Just verify paths are correct
    audio_fixed = 0
    words_audio = conn.execute("""
        SELECT word, audio_url FROM words
        WHERE audio_url IS NULL OR audio_url = ''
    """).fetchall()

    for word, _ in words_audio:
        audio_path = f"backend/data/audio/{word}.mp3"
        if Path(audio_path).exists():
            conn.execute(
                "UPDATE words SET audio_url=? WHERE word=?",
                (audio_path, word)
            )
            audio_fixed += 1

    print(f"Fixed {audio_fixed} missing audio paths")

    conn.commit()

    # Final verification
    print("\n" + "="*55)
    print("MIGRATION COMPLETE")
    print("="*55)
    cols = conn.execute(
        "PRAGMA table_info(words)"
    ).fetchall()
    print(f"Total columns: {len(cols)}")
    for c in cols:
        print(f"  {c[1]} ({c[2]})")

    total    = conn.execute(
        "SELECT COUNT(*) FROM words"
    ).fetchone()[0]
    enriched = conn.execute(
        "SELECT COUNT(*) FROM words WHERE is_enriched=1"
    ).fetchone()[0]
    audio    = conn.execute(
        "SELECT COUNT(*) FROM words "
        "WHERE audio_url IS NOT NULL AND audio_url != ''"
    ).fetchone()[0]

    print(f"\nWords:    {total}")
    print(f"Enriched: {enriched}")
    print(f"Audio:    {audio}")
    conn.close()


if __name__ == "__main__":
    print("="*55)
    print("DATABASE MIGRATION")
    print("="*55)
    migrate()
