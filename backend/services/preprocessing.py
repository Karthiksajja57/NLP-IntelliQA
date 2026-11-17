"""STEP 1 - NLP PREPROCESSING: lowercase -> remove punctuation -> tokenize -> remove stop-words."""
import re
from nltk.tokenize import RegexpTokenizer

try:
    from nltk.corpus import stopwords
    STOP_WORDS = set(stopwords.words("english"))
except Exception:  # NLTK corpus not downloaded -> built-in fallback list
    STOP_WORDS = set("""a an the is are was were be been being am of in on at to for from by with
    and or but if then so as it its this that these those what which who whom whose how when where why
    do does did can could should would will shall may might has have had i you he she we they me""".split())

# Words that only ask the question; they never belong to the topic (keywords).
QUESTION_WORDS = {"what", "who", "whom", "whose", "where", "when", "which", "why", "how"}
STOP_WORDS |= QUESTION_WORDS

_tokenizer = RegexpTokenizer(r"\w+")


def normalize_text(text):
    """Lowercase and collapse extra whitespace."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def remove_punctuation(text):
    """Replace punctuation / special symbols by spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def tokenize_text(text):
    """Split text into individual words (NLTK RegexpTokenizer, no downloads needed)."""
    return _tokenizer.tokenize(text)


def remove_stopwords(tokens):
    return [t for t in tokens if t not in STOP_WORDS]


def preprocess(text):
    """Full pipeline. Returns the processed text as one string."""
    return " ".join(remove_stopwords(tokenize_text(remove_punctuation(normalize_text(text)))))


def preprocess_steps(text):
    """Every intermediate result, used by the 'NLP Processing' panel in the UI."""
    lower = normalize_text(text)
    cleaned = remove_punctuation(lower)
    tokens = tokenize_text(cleaned)
    return {"original": text, "lowercase": lower, "cleaned": cleaned, "tokens": tokens,
            "no_stopwords": remove_stopwords(tokens)}
