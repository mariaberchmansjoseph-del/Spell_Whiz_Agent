"""
Script 04c: Smart multi-source word enrichment.
Priority chain:
  1. dictionaryapi.dev (free, unlimited)
  2. Merriam-Webster School Dictionary (free, 1000/day)
  3. Datamuse (synonyms/antonyms only, free unlimited)
  4. Groq LLM (sparingly, rate limited)
Run: python scripts/04c_enrich_smart.py
"""

import os
import re
import json
import time
import sqlite3
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY      = os.getenv("GROQ_API_KEY", "")
MW_SCHOOL_KEY = os.getenv("MW_SCHOOL_KEY", "")

DB_PATH   = "backend/data/words.db"
MAX_LLM   = 30

# API endpoints
DICT_API  = "https://api.dictionaryapi.dev/api/v2/entries/en"
MW_SCHOOL = "https://www.dictionaryapi.com/api/v3/references/sd4/json"
DATAMUSE  = "https://api.datamuse.com/words"

# Shared session with headers
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "SpellingBeeEducational/1.0"
})


# ── TEXT CLEANING ─────────────────────────────────────────────

def clean_mw(text: str) -> str:
    """Remove Merriam-Webster markup tags."""
    text = re.sub(r'\{[^}]+\}', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── SOURCE 1: FREE DICTIONARY API ────────────────────────────

def fetch_dict_api(word: str) -> dict:
    """
    dictionaryapi.dev — free, unlimited.
    Good coverage for common English words.
    """
    try:
        r = SESSION.get(
            f"{DICT_API}/{word.lower()}",
            timeout=8
        )
        if r.status_code != 200:
            return {}

        data = r.json()
        if not data or not isinstance(data, list):
            return {}

        entry    = data[0]
        phonetic = entry.get("phonetic", "")

        # Get phonetic from phonetics array if not in root
        if not phonetic:
            for p in entry.get("phonetics", []):
                if p.get("text"):
                    phonetic = p["text"]
                    break

        meanings       = entry.get("meanings", [])
        definition     = ""
        part_of_speech = ""
        examples       = []
        synonyms       = []
        antonyms       = []

        for meaning in meanings:
            defs = meaning.get("definitions", [])
            if defs and not definition:
                part_of_speech = meaning.get(
                    "partOfSpeech", ""
                )
                definition = defs[0].get("definition", "")

                for d in defs[:3]:
                    ex = d.get("example", "")
                    if ex:
                        examples.append(ex)
                    synonyms.extend(
                        d.get("synonyms", [])[:2]
                    )
                    antonyms.extend(
                        d.get("antonyms", [])[:2]
                    )

            # Collect synonyms from meaning level too
            synonyms.extend(
                meaning.get("synonyms", [])[:2]
            )
            antonyms.extend(
                meaning.get("antonyms", [])[:2]
            )

        if not definition:
            return {}

        return {
            "definition":    definition,
            "child_definition": definition,
            "part_of_speech": part_of_speech,
            "phonetic":      phonetic,
            "examples":      examples[:2],
            "synonyms":      list(set(synonyms))[:3],
            "antonyms":      list(set(antonyms))[:2],
            "source":        "dictionaryapi.dev"
        }

    except Exception:
        return {}


# ── SOURCE 2: MERRIAM-WEBSTER SCHOOL DICTIONARY ───────────────

def fetch_mw_school(word: str) -> dict:
    """
    Merriam-Webster School Dictionary.
    Child-friendly definitions.
    Uses shortdef for clean one-line definitions.
    1000 calls/day free.
    """
    if not MW_SCHOOL_KEY:
        return {}

    try:
        r = SESSION.get(
            f"{MW_SCHOOL}/{word.lower()}",
            params={"key": MW_SCHOOL_KEY},
            timeout=8
        )
        if r.status_code != 200:
            return {}

        data = r.json()
        if not data or not isinstance(data, list):
            return {}

        # Word not found — API returns suggestions as strings
        if isinstance(data[0], str):
            return {}

        entry = data[0]

        # Part of speech
        fl = entry.get("fl", "")

        # Pronunciation
        phonetic = ""
        prs = entry.get("hwi", {}).get("prs", [])
        if prs and isinstance(prs, list):
            phonetic = prs[0].get("mw", "")

        # shortdef is the cleanest definition
        shortdefs  = entry.get("shortdef", [])
        definition = shortdefs[0] if shortdefs else ""

        # If no shortdef, parse from def structure
        if not definition:
            for d in entry.get("def", []):
                for sseq in d.get("sseq", []):
                    for sg in sseq:
                        if not isinstance(sg, list) \
                                or len(sg) < 2:
                            continue
                        if not isinstance(sg[1], dict):
                            continue
                        for item in sg[1].get("dt", []):
                            if isinstance(item, list) \
                                    and item[0] == "text":
                                definition = clean_mw(
                                    item[1]
                                )
                                break
                        if definition:
                            break
                    if definition:
                        break
                if definition:
                    break

        if not definition:
            return {}

        # Extract example sentences from vis tags
        examples = []
        for d in entry.get("def", []):
            for sseq in d.get("sseq", []):
                for sg in sseq:
                    if not isinstance(sg, list) \
                            or len(sg) < 2:
                        continue
                    if not isinstance(sg[1], dict):
                        continue
                    for item in sg[1].get("dt", []):
                        if not isinstance(item, list) \
                                or len(item) < 2:
                            continue
                        if item[0] == "vis":
                            for vis in item[1]:
                                t = clean_mw(
                                    vis.get("t", "")
                                )
                                if t:
                                    examples.append(t)
                    if len(examples) >= 2:
                        break

        return {
            "definition":     definition,
            "child_definition": definition,
            "part_of_speech": fl,
            "phonetic":       phonetic,
            "examples":       examples[:2],
            "source":         "mw-school"
        }

    except Exception:
        return {}


# ── SOURCE 3: DATAMUSE ────────────────────────────────────────

def fetch_datamuse(word: str) -> dict:
    """
    Datamuse API — synonyms and antonyms only.
    Free, unlimited, no key needed.
    """
    result = {}
    try:
        r = SESSION.get(
            DATAMUSE,
            params={"rel_syn": word, "max": 5},
            timeout=6
        )
        if r.status_code == 200:
            result["synonyms"] = [
                w["word"] for w in r.json()
            ]
        time.sleep(0.1)

        r2 = SESSION.get(
            DATAMUSE,
            params={"rel_ant": word, "max": 3},
            timeout=6
        )
        if r2.status_code == 200:
            result["antonyms"] = [
                w["word"] for w in r2.json()
            ]
    except Exception:
        pass
    return result


# ── SOURCE 4: GROQ LLM ────────────────────────────────────────

def fetch_llm(
    word: str, grade: int, client
) -> dict:
    """
    Groq LLM — last resort for rare words.
    Rate limited so only used sparingly.
    """
    if not client:
        return {}

    age_map = {
        range(2, 4):  "7-8 year old child",
        range(4, 6):  "10 year old student",
        range(6, 8):  "12 year old student",
        range(8, 11): "15 year old student",
    }
    age = "12 year old student"
    for r, a in age_map.items():
        if grade in r:
            age = a
            break

    prompt = (
        f'Define the spelling word "{word}" '
        f'for a {age}.\n'
        f'Return only JSON:\n'
        f'{{"definition":"one sentence definition",'
        f'"child_definition":"simple version",'
        f'"part_of_speech":"noun/verb/adjective/adverb",'
        f'"example":"one example sentence",'
        f'"mnemonic":"memory trick to spell {word}"}}'
    )

    try:
        r = client.chat.completions.create(
            model    = "qwen/qwen3.8-27b",
            messages = [
                {"role": "system",
                 "content": "You are a dictionary. "
                            "Return JSON only. No markdown."},
                {"role": "user",
                 "content": prompt}
            ],
            temperature = 0.1,
            max_tokens  = 200,
        )

        # Handle reasoning model response
        text = getattr(
            r.choices[0].message, "content", ""
        ) or ""
        if not text:
            text = getattr(
                r.choices[0].message, "reasoning", ""
            ) or ""

        if not text:
            return {}

        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        data = json.loads(text)

        examples = []
        if data.get("example"):
            examples = [data["example"]]

        return {
            "definition":       data.get("definition", ""),
            "child_definition": data.get(
                "child_definition", ""
            ),
            "part_of_speech":   data.get("part_of_speech", ""),
            "examples":         examples,
            "mnemonic_text":    data.get("mnemonic", ""),
            "source":           "llm"
        }

    except Exception:
        return {}


# ── DATA MERGING ──────────────────────────────────────────────

def merge(primary: dict, extra: dict) -> dict:
    """
    Merge two data sources.
    Primary takes precedence for all fields.
    Extra fills in missing fields only.
    """
    result = {**primary}
    for field in ["synonyms", "antonyms",
                  "examples", "mnemonic_text",
                  "phonetic", "child_definition"]:
        if not result.get(field) and extra.get(field):
            result[field] = extra[field]
    return result


# ── DATABASE SAVE ─────────────────────────────────────────────

def save_word(
    conn: sqlite3.Connection,
    word: str,
    data: dict
) -> bool:
    """Save enriched word data to database."""
    if not data:
        return False

    definition = data.get("definition", "")
    if not definition or len(definition) < 5:
        return False

    examples = data.get("examples", [])
    if isinstance(examples, str):
        examples = [examples]

    synonyms = data.get("synonyms", [])
    if isinstance(synonyms, str):
        synonyms = [synonyms]

    antonyms = data.get("antonyms", [])
    if isinstance(antonyms, str):
        antonyms = [antonyms]

    try:
        conn.execute("""
            UPDATE words SET
              definition        = ?,
              child_definition  = COALESCE(
                  NULLIF(child_definition, ''), ?),
              part_of_speech    = COALESCE(
                  NULLIF(part_of_speech, ''), ?),
              phonetic          = COALESCE(
                  NULLIF(phonetic, ''), ?),
              examples          = ?,
              mnemonic_text     = COALESCE(
                  NULLIF(mnemonic_text, ''), ?),
              synonyms          = ?,
              antonyms          = ?,
              is_enriched       = 1,
              source            = ?,
              updated_at        = datetime('now')
            WHERE word = ?
        """, (
            definition,
            data.get("child_definition", definition),
            data.get("part_of_speech", ""),
            data.get("phonetic", ""),
            json.dumps(examples),
            data.get("mnemonic_text", ""),
            json.dumps(synonyms),
            json.dumps(antonyms),
            data.get("source", "unknown"),
            word,
        ))
        conn.commit()
        return True

    except Exception:
        return False


# ── MAIN ──────────────────────────────────────────────────────

def enrich_smart():
    conn = sqlite3.connect(DB_PATH)

    missing = conn.execute("""
        SELECT word, grade_level
        FROM words
        WHERE is_enriched = 0
           OR definition IS NULL
           OR length(definition) < 5
        ORDER BY grade_level, word
    """).fetchall()

    conn.close()

    print("="*55)
    print("SMART MULTI-SOURCE WORD ENRICHMENT")
    print("="*55)
    print(f"Words to enrich:        {len(missing)}")
    print(f"Source 1: dict API      free unlimited")
    print(f"Source 2: MW School     {'✅ enabled' if MW_SCHOOL_KEY else '❌ add MW_SCHOOL_KEY to .env'}")
    print(f"Source 3: Datamuse      free unlimited")
    print(f"Source 4: Groq LLM      max {MAX_LLM} calls")
    print()

    if not missing:
        print("All words already enriched!")
        return

    # Init Groq client
    groq_client = None
    if GROQ_KEY:
        try:
            from groq import Groq
            groq_client = Groq(api_key=GROQ_KEY)
        except Exception:
            pass

    stats = {
        "dict_api": 0,
        "mw_school": 0,
        "llm": 0,
        "failed": 0,
    }
    llm_calls = 0
    conn      = sqlite3.connect(DB_PATH)

    for word, grade in tqdm(missing, desc="Enriching"):

        saved = False

        # ── Source 1: Free Dictionary API ────────────
        data = fetch_dict_api(word)
        time.sleep(0.2)

        if data.get("definition"):
            dm   = fetch_datamuse(word)
            data = merge(data, dm)
            if save_word(conn, word, data):
                stats["dict_api"] += 1
                saved = True

        # ── Source 2: Merriam-Webster School ─────────
        if not saved and MW_SCHOOL_KEY:
            mw_data = fetch_mw_school(word)
            time.sleep(0.15)

            if mw_data.get("definition"):
                dm      = fetch_datamuse(word)
                mw_data = merge(mw_data, dm)
                if save_word(conn, word, mw_data):
                    stats["mw_school"] += 1
                    saved = True

        # ── Source 4: Groq LLM ────────────────────────
        if not saved and llm_calls < MAX_LLM:
            dm       = fetch_datamuse(word)
            llm_data = fetch_llm(word, grade, groq_client)
            llm_calls += 1
            time.sleep(1.5)

            if llm_data.get("definition"):
                merged = merge(llm_data, dm)
                if save_word(conn, word, merged):
                    stats["llm"] += 1
                    saved = True

        if not saved:
            stats["failed"] += 1

    conn.close()

    # Final stats
    conn      = sqlite3.connect(DB_PATH)
    total     = conn.execute(
        "SELECT COUNT(*) FROM words"
    ).fetchone()[0]
    enriched  = conn.execute(
        "SELECT COUNT(*) FROM words WHERE is_enriched=1"
    ).fetchone()[0]
    remaining = total - enriched
    conn.close()

    print(f"\n{'='*55}")
    print(f"ENRICHMENT COMPLETE")
    print(f"{'='*55}")
    print(f"Dict API:        {stats['dict_api']:>5,}")
    print(f"MW School:       {stats['mw_school']:>5,}")
    print(f"LLM:             {stats['llm']:>5,}")
    print(f"Failed:          {stats['failed']:>5,}")
    print(f"─────────────────────────")
    print(f"Total enriched:  {enriched}/{total}")
    print(f"Remaining:       {remaining}")

    if remaining > 0:
        pct = enriched / total * 100
        print(f"Progress:        {pct:.0f}%")
        print(f"\nRun again to retry {remaining} words.")
    else:
        print(f"\n✅ All words enriched!")


if __name__ == "__main__":
    enrich_smart()