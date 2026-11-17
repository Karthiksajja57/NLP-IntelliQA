"""Terminal demo of the NLP pipeline (no server, no login):  python test_pipeline.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.pdf_service import extract_document
from services.chunking import chunk_pages
from services.qa_service import QAEngine

pages, _ = extract_document(os.path.join(os.path.dirname(__file__), "..", "sample_document.txt"), ".txt")
engine = QAEngine(chunk_pages(pages))
for q in ["What is National Bird?", "What is National Animal?", "What is the capital of India?",
          "Who is the founder of Microsoft?", "Where is the Taj Mahal?", "Who painted the Mona Lisa?"]:
    r = engine.ask(q); n = r["nlp"]
    print(f"Q: {q}\n  lowercase : {n['lowercase']}\n  tokens    : {n['tokens']}\n  keywords  : {n['keywords']}"
          f"\n  similarity: {r['similarity']}%\n  sentence  : {n['relevant_sentence']}\n  pattern   : {n['extraction_pattern']}"
          f"\n  ANSWER    : {r['answer']}\n")
