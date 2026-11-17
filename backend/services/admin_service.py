"""Admin bootstrap and admin-only database operations."""
import os
import database
from services.auth_service import hash_password


def ensure_admin():
    email = os.getenv("ADMIN_EMAIL", "admin@intelliqa.local").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    name = os.getenv("ADMIN_NAME", "IntelliQA Administrator").strip()
    if not password:
        return
    existing = database.users.find_one({"email": email})
    if not existing:
        database.users.insert_one({
            "full_name": name,
            "email": email,
            "password_hash": hash_password(password),
            "role": "admin",
            "created_at": database.now_utc()
        })
    elif existing.get("role") != "admin":
        database.users.update_one({"_id": existing["_id"]}, {"$set": {"role": "admin"}})
