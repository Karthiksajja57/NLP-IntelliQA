"""Registration, login and secure server-side sessions using MongoDB."""
import re, hmac, hashlib, secrets
from datetime import timedelta
import database
from config import MIN_PASSWORD_LENGTH, SESSION_DAYS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def _public(row):
    return {"id": str(row["_id"]), "full_name": row["full_name"], "email": row["email"], "role": row.get("role", "user")}


def _new_session(user_id):
    token = secrets.token_urlsafe(32)
    database.sessions.insert_one({
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "user_id": user_id,
        "created_at": database.now_utc()
    })
    return token


def register(full_name, email, password, confirm):
    full_name, email = full_name.strip(), email.strip().lower()
    if not full_name or not email or not password or not confirm:
        raise ValueError("All fields are required.")
    if not EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    if database.users.find_one({"email": email}):
        raise LookupError("An account with this email already exists.")
    doc = {
        "full_name": full_name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "user",
        "created_at": database.now_utc()
    }
    try:
        result = database.users.insert_one(doc)
    except Exception as exc:
        if "duplicate" in str(exc).lower():
            raise LookupError("An account with this email already exists.")
        raise
    doc["_id"] = result.inserted_id
    return _new_session(result.inserted_id), _public(doc)


def login(email, password):
    user = database.users.find_one({"email": email.strip().lower()})
    if not user or not verify_password(password, user["password_hash"]):
        raise PermissionError("Invalid email or password.")
    return _new_session(user["_id"]), _public(user)


def user_from_token(token):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = database.sessions.find_one({"token_hash": token_hash})
    if not session:
        return None
    if session.get("created_at", database.now_utc()) < database.now_utc() - timedelta(days=SESSION_DAYS):
        database.sessions.delete_one({"_id": session["_id"]})
        return None
    user = database.users.find_one({"_id": session["user_id"]})
    return _public(user) if user else None


def logout(token):
    if token:
        database.sessions.delete_one({"token_hash": hashlib.sha256(token.encode()).hexdigest()})
