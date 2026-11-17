# One place to tune the system.
SIMILARITY_THRESHOLD = 0.25      # below this the answer is "not found"
CHUNK_MIN_WORDS = 40             # a chunk is closed once it has at least this many words...
CHUNK_MAX_WORDS = 90             # ...or would go beyond this many
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_UPLOAD_MB = 10
MIN_PASSWORD_LENGTH = 6
SESSION_DAYS = 7
NOT_FOUND_MESSAGE = "No relevant answer was found in the uploaded document."
