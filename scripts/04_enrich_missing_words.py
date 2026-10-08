def enrich_word(
    client: Groq,
    word:   str,
    grade:  int,
    retry:  int = 3
) -> dict:
    """Enrich one word with retry on rate limit."""

    if grade <= 3:
        age_note = "7-8 year old child"
    elif grade <= 5:
        age_note = "10 year old student"
    elif grade <= 7:
        age_note = "12 year old student"
    else:
        age_note = "15 year old student"

    prompt = f"""For the spelling word "{word}" (grade {grade}):

Provide this information as JSON:
{{
  "definition": "one clear sentence defining {word}",
  "child_definition": "simple explanation for a {age_note}",
  "part_of_speech": "noun or verb or adjective or adverb",
  "example1": "a sentence using {word} in context",
  "example2": "another sentence using {word}",
  "mnemonic": "a memory trick to remember how to spell {word}",
  "synonyms": ["similar word 1", "similar word 2"],
  "root": "the Latin or Greek root if applicable"
}}"""

    for attempt in range(retry):
        try:
            response = client.chat.completions.create(
                model    = MODEL,
                messages = [
                    {"role": "system",
                     "content": "You are a dictionary. "
                                "Respond with valid JSON only."},
                    {"role": "user",
                     "content": prompt}
                ],
                temperature = 0.1,
                max_tokens  = 400,
            )

            text = response.choices[0].message.content

            # Empty response — likely rate limited
            if not text or len(text.strip()) < 10:
                wait = 60 * (attempt + 1)
                tqdm.write(
                    f"  Empty response for '{word}'. "
                    f"Waiting {wait}s..."
                )
                time.sleep(wait)
                continue

            # Clean markdown
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text  = "\n".join(lines[1:-1])

            data = json.loads(text)
            return data

        except Exception as e:
            err = str(e).lower()
            if "rate" in err or "limit" in err or "429" in err:
                wait = 60 * (attempt + 1)
                tqdm.write(
                    f"  Rate limit hit. Waiting {wait}s..."
                )
                time.sleep(wait)
            elif attempt < retry - 1:
                time.sleep(5)

    return {}