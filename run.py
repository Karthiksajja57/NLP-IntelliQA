"""Optional helper: python run.py  (same as: cd backend && python -m uvicorn main:app --reload)"""
import os, sys, subprocess
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
try:
    import nltk; nltk.download("stopwords", quiet=True)
except Exception:
    pass
print("Open http://127.0.0.1:8000/app")
subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--reload"])
