"""Split page text into sentences, then group sentences into small chunks (page number is kept)."""
import re
from config import CHUNK_MIN_WORDS, CHUNK_MAX_WORDS


def split_sentences(text):
    """Split at . ! ? and also at line breaks (so 'National Bird Is a Peacock' lines stay separate)."""
    parts = []
    for line in re.split(r"[\r\n]+", text):
        line = re.sub(r"\s+", " ", line).strip()
        parts += [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    return parts


def chunk_pages(pages):
    chunks, chunk_id = [], 1
    for page in pages:
        current, count = [], 0
        for sentence in split_sentences(page["text"]):
            words = len(sentence.split())
            if current and (count >= CHUNK_MIN_WORDS or count + words > CHUNK_MAX_WORDS):
                chunks.append({"chunk_id": chunk_id, "page": page["page"], "text": " ".join(current)})
                chunk_id, current, count = chunk_id + 1, [], 0
            current.append(sentence)
            count += words
        if current:
            chunks.append({"chunk_id": chunk_id, "page": page["page"], "text": " ".join(current)})
            chunk_id += 1
    return chunks
