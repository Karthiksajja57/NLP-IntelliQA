# IntelliQA — NLP Document Question Answering System

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FKarthiksajja57%2FNLP-IntelliQA)

IntelliQA lets users register/login, upload PDF/TXT documents, ask questions, inspect NLP processing, and view question history. MongoDB Atlas stores users, sessions, documents, and question history.

## 1. MongoDB Atlas setup

1. Create a MongoDB Atlas cluster.
2. Create a database user and password.
3. In **Network Access**, allow your development machine's IP address (or `0.0.0.0/0` only for temporary development/testing).
4. Copy the application's MongoDB connection string.
5. Copy `backend/.env.example` to `backend/.env` and edit it:

```env
MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=intelliqa
ADMIN_NAME=IntelliQA Administrator
ADMIN_EMAIL=admin@intelliqa.local
ADMIN_PASSWORD=ChangeThisAdminPassword123!
```

Use a strong admin password and do not commit `.env` to GitHub.

## 2. Install dependencies

From the IntelliQA folder:

```bash
cd backend
py -m pip install -r requirements.txt
```

If using `python` instead of `py`, use `python -m pip`.

## 3. Start the application

```bash
cd backend
py -m uvicorn main:app --reload
```

Open:

`http://127.0.0.1:8000/app/`

You can also run:

```bash
cd IntelliQA
py run.py
```

## 4. User registration/login

Click **Register**, create a normal account, then log in. Normal users can upload documents, ask questions, inspect NLP processing, and view their own history.

## 5. Admin login

Admin is created automatically on startup from `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`.

Example development credentials from `.env.example`:

- Email: `admin@intelliqa.local`
- Password: `ChangeThisAdminPassword123!`

**Change the password before using the project outside local testing.**

The same login form is used. After an admin logs in, the **Admin Panel** appears in the sidebar. It shows user/document/question counts and registered users.

## 6. MongoDB collections

The application creates these collections automatically:

- `users`
- `sessions`
- `documents`
- `questions`

Indexes are also created automatically for email, sessions, and user history.

## 7. Document test

Upload the provided `IntelliQA_Test_Document.pdf` and ask:

- What is the national bird of India?
- What is the national animal of India?
- What is the capital of India?
- What is machine learning?
- Who founded Microsoft?
- What are the applications of NLP?

## Project structure

```text
IntelliQA/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   └── services/
│       ├── auth_service.py
│       ├── admin_service.py
│       ├── qa_service.py
│       ├── preprocessing.py
│       ├── chunking.py
│       └── pdf_service.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── sample_document.txt
└── run.py
```
