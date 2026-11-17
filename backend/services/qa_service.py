"""
Question answering in three clearly separated stages:
  1. NLP PREPROCESSING  (preprocessing.py)
  2. INFORMATION RETRIEVAL  - TF-IDF + cosine similarity -> most relevant sentence   (QAEngine.ask)
  3. ANSWER EXTRACTION  - pattern rules -> the specific answer, e.g. "Peacock"        (extract_answer)
"""
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import SIMILARITY_THRESHOLD, NOT_FOUND_MESSAGE
from services.preprocessing import preprocess, preprocess_steps, tokenize_text
from services.chunking import split_sentences

COPULA = re.compile(r"\s(?:is|are|was|were)\s|\s*[:=]\s*|\s+-\s+", re.IGNORECASE)
ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
YEAR_OR_DATE = re.compile(
    r"\b(?:\d{1,2}\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"(?:\s+\d{1,2})?(?:,?\s+\d{4})?\b|\b(?:1\d{3}|20\d{2})\b", re.IGNORECASE)
PLACE = re.compile(r"\b(?:in|at|near|on|inside)\s+(.+)$", re.IGNORECASE)


def _clean(text):
    return text.strip(" .,;:!?\"'")


def _keywords(question):
    from services.preprocessing import remove_stopwords
    return remove_stopwords(tokenize_text(preprocess_steps(question)["cleaned"]))


def _split_copula(sentence):
    """'National Bird Is a Peacock.' -> ('National Bird', 'a Peacock.')  or None."""
    m = COPULA.search(sentence)
    return (sentence[:m.start()], sentence[m.end():]) if m else None


def extract_answer(question, sentence, keywords):
    """Return (answer, pattern_name). Falls back to the whole sentence when unsure."""
    q = question.lower().strip()
    qword = next((w for w in ("who", "where", "when", "which", "what") if re.search(rf"\b{w}\b", q)), "what")

    if qword == "when":
        m = YEAR_OR_DATE.search(sentence)
        if m:
            return m.group(0).strip(), "when -> date/year"
    if qword == "where":
        m = PLACE.search(sentence)
        if m:
            return _clean(m.group(1)), "where -> place phrase"

    parts = _split_copula(sentence)
    if parts and keywords:
        subject, rest = _clean(parts[0]), _clean(parts[1])
        subject_tokens = set(tokenize_text(subject.lower()))
        rest_tokens = set(tokenize_text(rest.lower()))
        if all(k in subject_tokens for k in keywords) and rest:
            # "National Bird IS a Peacock"  ->  text after the verb
            short = ARTICLE.sub("", rest)
            answer = short if len(short.split()) <= 4 else rest[0].upper() + rest[1:]
            return answer, "X is Y -> Y"
        if all(k in rest_tokens for k in keywords) and subject and not subject_tokens & set(keywords):
            # "Peacock IS the national bird" -> text before the verb
            return subject, "Y is X -> Y"
    return sentence, "fallback (whole sentence)"


class QAEngine:
    def __init__(self, chunks):
        self.chunks = chunks
        self.sentences, sent_chunk = [], []
        for i, chunk in enumerate(chunks):
            for s in split_sentences(chunk["text"]):
                self.sentences.append(s)
                sent_chunk.append(i)
        self.sentence_chunk = np.array(sent_chunk)
        # TF-IDF is fitted on the preprocessed chunks (ValueError if the text has no usable words).
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        self.matrix = self.vectorizer.fit_transform([preprocess(c["text"]) for c in chunks])
        self.sentence_matrix = self.vectorizer.transform([preprocess(s) for s in self.sentences])

    def ask(self, question):
        steps = preprocess_steps(question)
        keywords = steps["no_stopwords"]
        nlp = {"original_question": question, "lowercase": steps["lowercase"],
               "cleaned_question": steps["cleaned"], "tokens": steps["tokens"],
               "keywords": keywords, "tfidf_terms": [], "relevant_sentence": None,
               "extraction_pattern": None}
        if not keywords:
            return self._not_found(0.0, nlp)

        # ---- INFORMATION RETRIEVAL: TF-IDF vector + cosine similarity ----
        q_vec = self.vectorizer.transform([" ".join(keywords)])
        terms = self.vectorizer.get_feature_names_out()
        nz = q_vec.nonzero()[1]
        nlp["tfidf_terms"] = [{"term": terms[j], "weight": round(float(q_vec[0, j]), 3)} for j in nz]

        chunk_scores = cosine_similarity(q_vec, self.matrix)[0]
        sent_scores = cosine_similarity(q_vec, self.sentence_matrix)[0]
        # small bonus when the sentence SUBJECT contains all keywords ("Machine learning is ...")
        adjusted = sent_scores.copy()
        for i, s in enumerate(self.sentences):
            parts = _split_copula(s)
            if parts and sent_scores[i] > 0 and all(k in tokenize_text(parts[0].lower()) for k in keywords):
                adjusted[i] += 0.2
        best_in_chunk = np.zeros(len(self.chunks))
        for i, score in enumerate(adjusted):
            c = self.sentence_chunk[i]
            best_in_chunk[c] = max(best_in_chunk[c], score)
        final = np.maximum(chunk_scores, best_in_chunk)

        best = int(final.argmax())
        idx = np.where(self.sentence_chunk == best)[0]
        top = max(idx, key=lambda i: adjusted[i])
        sentence = self.sentences[top]
        # The reported score is the real cosine similarity (without the subject bonus).
        similarity = min(1.0, float(max(chunk_scores[best], sent_scores[top])))
        if similarity < SIMILARITY_THRESHOLD:
            return self._not_found(similarity, nlp)

        # ---- ANSWER EXTRACTION ----
        answer, pattern = extract_answer(question, sentence, keywords)
        nlp.update(relevant_sentence=sentence, extraction_pattern=pattern)
        return {"success": True, "answer": answer, "similarity": round(similarity * 100, 1),
                "page": self.chunks[best]["page"], "source_text": sentence, "nlp": nlp}

    @staticmethod
    def _not_found(score, nlp):
        return {"success": False, "answer": NOT_FOUND_MESSAGE, "similarity": round(score * 100, 1),
                "page": None, "source_text": None, "nlp": nlp}
