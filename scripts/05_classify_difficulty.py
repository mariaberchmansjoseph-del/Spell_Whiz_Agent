"""
Script 05: Classify words as easy or difficult
within each grade level.
Run: python scripts/05_classify_difficulty.py
"""

import sqlite3

DB_PATH = "backend/data/words.db"

# Words that are exceptions — always difficult
# regardless of length
ALWAYS_DIFFICULT = {
    "colonel", "conscience", "conscientious",
    "necessary", "occurrence", "separate",
    "definitely", "embarrass", "accommodate",
    "rhythm", "pneumonia", "psychology",
    "bureaucracy", "onomatopoeia", "mnemonic",
    "lieutenant", "Wednesday", "February",
    "February", "necessary", "privilege",
    "prejudice", "perseverance", "questionnaire",
}

# Words that are exceptions — always easy
# regardless of other factors
ALWAYS_EASY = {
    "about", "after", "again", "always",
    "animal", "another", "around", "because",
    "before", "being", "better", "between",
    "bring", "carry", "change", "children",
    "clean", "close", "coming", "could",
    "country", "different", "during", "early",
}


def score_word(
    word:         str,
    grade:        int,
    definition:   str,
    root_meaning: str,
    etymology:    str,
) -> int:
    """
    Score a word for difficulty.
    Higher score = more difficult.
    Threshold: >= 4 = difficult, < 4 = easy
    """
    score = 0
    word_lower = word.lower()

    # Hard exceptions
    if word_lower in ALWAYS_DIFFICULT:
        return 10
    if word_lower in ALWAYS_EASY:
        return 0

    # Word length
    length = len(word)
    if length > 12:
        score += 4
    elif length > 9:
        score += 3
    elif length > 7:
        score += 2
    elif length > 5:
        score += 1

    # Grade level weight
    if grade >= 9:
        score += 3
    elif grade >= 7:
        score += 2
    elif grade >= 5:
        score += 1

    # Classical origin (Latin/Greek = harder)
    combined = (
        (root_meaning or "") + " " + (etymology or "")
    ).lower()
    if any(lang in combined for lang in [
        "latin", "greek", "french", "old english"
    ]):
        score += 2

    # Tricky letter patterns
    tricky_patterns = [
        "ph",   # photograph, philosophy
        "gh",   # knight, through, rough
        "sch",  # school, scheme
        "chr",  # christmas, chronicle
        "rh",   # rhythm, rhapsody
        "mn",   # mnemonic, column
        "ps",   # psychology, psalm
        "wr",   # write, wrong, wreck
        "kn",   # knight, know, knock
        "gn",   # gnome, align, sign
        "mb",   # bomb, lamb, climb
        "bt",   # doubt, debt
        "ck",   # back, check (easy but pattern worth noting)
        "tch",  # catch, watch
        "dge",  # judge, bridge
        "igh",  # night, light, fight
        "augh", # daughter, caught
        "ough", # through, though, tough
        "eau",  # beautiful, bureau
        "que",  # unique, technique
        "tion", # nation, education
        "sion", # version, mission
        "cious", # precious, conscious
        "tious", # cautious, infectious
    ]
    pattern_hits = sum(
        1 for p in tricky_patterns
        if p in word_lower
    )
    score += min(pattern_hits * 1, 3)

    # Double letters
    for i in range(len(word_lower) - 1):
        if word_lower[i] == word_lower[i + 1] \
                and word_lower[i].isalpha():
            score += 1
            break  # only count once

    # Silent letters check
    silent_combos = [
        ("kn", 0),  # silent k
        ("wr", 0),  # silent w
        ("gn", 0),  # silent g
        ("mb", -1), # silent b at end
        ("bt", 0),  # silent b
    ]
    for combo, pos in silent_combos:
        if combo in word_lower:
            score += 2
            break

    return score


def classify_all():
    conn  = sqlite3.connect(DB_PATH)

    # Get all words with their data
    words = conn.execute("""
        SELECT word, grade_level,
               definition, root_meaning, etymology
        FROM words
    """).fetchall()

    print("="*55)
    print("DIFFICULTY CLASSIFIER")
    print("="*55)
    print(f"Words to classify: {len(words)}")
    print()

    easy_count       = 0
    difficult_count  = 0
    updates          = []

    for word, grade, definition, root_meaning, \
            etymology in words:

        score = score_word(
            word         = word or "",
            grade        = grade or 5,
            definition   = definition or "",
            root_meaning = root_meaning or "",
            etymology    = etymology or "",
        )

        level = "difficult" if score >= 4 else "easy"
        updates.append((level, word))

        if level == "easy":
            easy_count += 1
        else:
            difficult_count += 1

    # Batch update
    conn.executemany(
        "UPDATE words SET difficulty_level=? WHERE word=?",
        updates
    )
    conn.commit()

    print(f"Easy words:      {easy_count:,}")
    print(f"Difficult words: {difficult_count:,}")
    print()

    # Show breakdown by grade
    print("By grade:")
    for grade in range(2, 11):
        e = conn.execute("""
            SELECT COUNT(*) FROM words
            WHERE grade_level = ?
            AND difficulty_level = 'easy'
        """, (grade,)).fetchone()[0]

        d = conn.execute("""
            SELECT COUNT(*) FROM words
            WHERE grade_level = ?
            AND difficulty_level = 'difficult'
        """, (grade,)).fetchone()[0]

        print(f"  Grade {grade:>2}: "
              f"{e:>4} easy  |  {d:>4} difficult")

    # Show sample difficult words per grade
    print("\nSample difficult words:")
    for grade in [3, 5, 7, 9]:
        samples = conn.execute("""
            SELECT word FROM words
            WHERE grade_level = ?
            AND difficulty_level = 'difficult'
            ORDER BY RANDOM()
            LIMIT 3
        """, (grade,)).fetchall()
        sample_words = [r[0] for r in samples]
        print(f"  Grade {grade}: {', '.join(sample_words)}")

    conn.close()
    print(f"\nNext: python scripts/04_enrich_missing_words.py")


if __name__ == "__main__":
    classify_all()