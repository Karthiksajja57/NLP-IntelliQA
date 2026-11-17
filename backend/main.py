import os, re, sys, shutil
# pyrefly: ignore[missing-import]
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # imports work from any folder
# pyrefly: ignore[missing-import]
from fastapi import FastAPI, File, UploadFile, HTTPException, Header, Depends, Request
# pyrefly: ignore[missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore[missing-import]
from fastapi.responses import RedirectResponse
# pyrefly: ignore[missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore[missing-import]
from pydantic import BaseModel

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB
import database
from services import auth_service
from services.admin_service import ensure_admin
from services.pdf_service import extract_document
from services.chunking import chunk_pages
from services.qa_service import QAEngine

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(BASE, "uploads")
FRONTEND = os.path.join(BASE, "..", "frontend")
os.makedirs(UPLOADS, exist_ok=True)
database.init_db()
ensure_admin()

app = FastAPI(title="IntelliQA")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# The NLP engine is kept per user (in memory). It does not depend on authentication code.
engines = {}   # user_id -> {"engine": QAEngine, "filename": str, "pages": int, "chunks": int}


# ---------- request models ----------
class RegisterBody(BaseModel):
    full_name: str = ""
    email: str = ""
    password: str = ""
    confirm_password: str = ""


class LoginBody(BaseModel):
    email: str = ""
    password: str = ""


class QuestionBody(BaseModel):
    question: str = ""


# ---------- authentication helpers ----------
def get_token(authorization: str = Header(None)):
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def current_user(token: str = Depends(get_token)):
    user = auth_service.user_from_token(token)
    if not user:
        raise HTTPException(401, "Please log in to continue.")
    return user


def admin_user(user: dict = Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required.")
    return user


# ---------- public routes ----------
@app.get("/")
def root(request: Request):
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/app/")
    return {"message": "IntelliQA NLP Question Answering System is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register", status_code=201)
def register(body: RegisterBody):
    try:
        token, user = auth_service.register(body.full_name, body.email, body.password, body.confirm_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except LookupError as exc:
        raise HTTPException(409, str(exc))
    return {"success": True, "token": token, "user": user}


@app.post("/login")
def login(body: LoginBody):
    if not body.email.strip() or not body.password:
        raise HTTPException(400, "Email and password are required.")
    try:
        token, user = auth_service.login(body.email, body.password)
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    return {"success": True, "token": token, "user": user}


@app.post("/logout")
def logout(token: str = Depends(get_token), user: dict = Depends(current_user)):
    auth_service.logout(token)
    engines.pop(user["id"], None)
    return {"success": True}


@app.get("/me")
def me(user: dict = Depends(current_user)):
    return {"success": True, "user": user}


# ---------- document + question answering (login required) ----------
def safe_filename(name):
    name = os.path.basename(name or "document")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:80]


@app.post("/upload")
async def upload(file: UploadFile = File(...), user: dict = Depends(current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported file type. Please upload a PDF or TXT file.")
    path = os.path.join(UPLOADS, f"user{user['id']}{ext}")
    size = 0
    with open(path, "wb") as out:
        while True:
            block = await file.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                out.close(); os.remove(path)
                raise HTTPException(413, f"File too large. Maximum size is {MAX_UPLOAD_MB} MB.")
            out.write(block)
    if size == 0:
        raise HTTPException(400, "The uploaded file is empty.")
    try:
        pages, total_pages = extract_document(path, ext)
        chunks = chunk_pages(pages)
        engine = QAEngine(chunks)
    except ValueError as exc:
        raise HTTPException(400, str(exc) or "The document has no usable words.")
    name = safe_filename(file.filename)
    engines[user["id"]] = {"engine": engine, "filename": name, "pages": total_pages, "chunks": len(chunks)}
    database.documents.insert_one({"user_id": user["id"], "filename": name, "pages": total_pages, "chunks": len(chunks), "created_at": database.now_utc()})
    return {"success": True, "filename": name, "pages": total_pages, "chunks": len(chunks),
            "message": "Document processed successfully."}


@app.post("/ask")
def ask(body: QuestionBody, user: dict = Depends(current_user)):
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Please type a question.")
    doc = engines.get(user["id"])
    if not doc:
        raise HTTPException(400, "Please upload a document first.")
    result = doc["engine"].ask(question)
    database.questions.insert_one({"user_id": user["id"], "question": question, "answer": result["answer"], "similarity": result["similarity"], "page": result["page"], "created_at": database.now_utc()})
    return result


@app.get("/document-info")
def document_info(user: dict = Depends(current_user)):
    doc = engines.get(user["id"])
    docs_count = database.documents.count_documents({"user_id": user["id"]})
    q_count = database.questions.count_documents({"user_id": user["id"]})
    sim_values = [x.get("similarity", 0) for x in database.questions.find({"user_id": user["id"], "similarity": {"$ne": None}}, {"similarity": 1})]
    avg = sum(sim_values) / len(sim_values) if sim_values else 0
    return {"uploaded": bool(doc), "filename": doc["filename"] if doc else None,
            "pages": doc["pages"] if doc else 0, "chunks": doc["chunks"] if doc else 0,
            "documents_processed": docs_count, "questions": q_count,
            "average_similarity": round(avg, 1)}


@app.get("/history")
def history(user: dict = Depends(current_user)):
    rows = database.questions.find({"user_id": user["id"]}).sort("created_at", -1).limit(50)
    data = []
    for r in rows:
        data.append({"question": r.get("question", ""), "answer": r.get("answer", ""),
                     "similarity": r.get("similarity", 0), "page": r.get("page"),
                     "created_at": r.get("created_at").isoformat() if r.get("created_at") else ""})
    return {"success": True, "history": data}


# ---------- admin routes ----------
@app.get("/admin/stats")
def admin_stats(user: dict = Depends(admin_user)):
    return {
        "success": True,
        "users": database.users.count_documents({}),
        "documents": database.documents.count_documents({}),
        "questions": database.questions.count_documents({}),
        "admins": database.users.count_documents({"role": "admin"})
    }


@app.get("/admin/users")
def admin_users(user: dict = Depends(admin_user)):
    rows = database.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(100)
    data = []
    for r in rows:
        data.append({"id": str(r["_id"]), "full_name": r.get("full_name", ""), "email": r.get("email", ""),
                     "role": r.get("role", "user"), "created_at": r.get("created_at").isoformat() if r.get("created_at") else ""})
    return {"success": True, "users": data}


# Frontend at http://127.0.0.1:8000/app
app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="frontend")
