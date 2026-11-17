"""MongoDB Atlas storage for IntelliQA."""
import os
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "intelliqa")

client = None
db = None
users = sessions = documents = questions = None


def init_db():
    global client, db, users, sessions, documents, questions
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set. Add your MongoDB Atlas connection string to backend/.env")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000, tz_aware=True)
    client.admin.command("ping")
    db = client[MONGODB_DB]
    users = db["users"]
    sessions = db["sessions"]
    documents = db["documents"]
    questions = db["questions"]

    users.create_index([("email", ASCENDING)], unique=True)
    sessions.create_index([("token_hash", ASCENDING)], unique=True)
    sessions.create_index([("created_at", DESCENDING)])
    documents.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    questions.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])


def now_utc():
    return datetime.now(timezone.utc)


def get_db():
    if db is None:
        init_db()
    return db
