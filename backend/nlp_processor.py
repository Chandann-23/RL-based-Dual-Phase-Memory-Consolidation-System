import spacy
import re
import sys

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Fallback for local development if model isn't downloaded
    print("spaCy model 'en_core_web_sm' not found. Please run 'python -m spacy download en_core_web_sm'")
    # We don't want to crash during build, but we need it for runtime
    nlp = None

IMPORTANCE_KEYWORDS = {
    "exam", "deadline", "urgent", "important", "project",
    "meeting", "submit", "assignment", "test", "due", "quiz"
}

def extract_concepts(text: str) -> list[dict]:
    """
    Extract key concepts from user input.
    Returns a list of concept dicts with keyword_flag set.
    """
    if nlp is None:
        return []
    doc = nlp(text.lower())
    concepts = []

    seen = set()
    for token in doc:
        if token.is_stop or token.is_punct or token.is_space:
            continue
        lemma = token.lemma_.strip()
        if len(lemma) < 3 or lemma in seen:
            continue
        seen.add(lemma)
        concepts.append({
            "concept": lemma,
            "keyword_flag": 1 if lemma in IMPORTANCE_KEYWORDS else 0
        })

    # Also pick named entities
    for ent in doc.ents:
        lemma = ent.text.lower().strip()
        if lemma not in seen and len(lemma) >= 2:
            seen.add(lemma)
            concepts.append({
                "concept": lemma,
                "keyword_flag": 1 if lemma in IMPORTANCE_KEYWORDS else 0
            })

    return concepts