from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import numpy as np
from pathlib import Path
import aiofiles
import uuid
import faiss
import re, json

app = FastAPI(title="AI Resume RAG Suite", version="3.4.0")

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ensure uploads directory exists
Path("uploads").mkdir(parents=True, exist_ok=True)

# ---------------- Model Setup ----------------
EMBED_MODEL = "thenlper/gte-base"
print(f"🔹 Loading embeddings: {EMBED_MODEL}")
embedding_model = pipeline("feature-extraction", model=EMBED_MODEL)

LLM_MODEL = "google/flan-t5-small"  # lighter model for CPU
print(f"🔹 Loading LLM: {LLM_MODEL}")
llm_tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
llm_model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL)

dimension = 768  # gte-base embedding size
index = faiss.IndexFlatL2(dimension)
resume_chunks = []
chunk_ids = []

# ---------------- Utilities ----------------
def embed_text(text: str) -> np.ndarray:
    result = embedding_model(text, truncation=True, max_length=512)
    return np.mean(result[0], axis=0).astype("float32")

def chunk_text(text: str, max_tokens: int = 300) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i+max_tokens]) for i in range(0, len(words), max_tokens)]

STOPWORDS = set(["the","and","for","with","that","this","from","your","you","will","have","has","a","an","in","on","of","to","is","are","as","be","by","or","at","we","our","skills","experience","have","years","work"])

def extract_keywords(text: str, top_n: int = 25) -> List[str]:
    s = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    tokens = [t for t in s.split() if len(t) > 2 and t not in STOPWORDS and not t.isdigit()]
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    kws = sorted(freq.keys(), key=lambda k: freq[k], reverse=True)
    return kws[:top_n]

def simple_keyword_feedback(job_desc: str, retrieved_chunks: List[str]) -> str:
    job_kws = extract_keywords(job_desc, top_n=25)
    joined = " ".join(retrieved_chunks).lower() if retrieved_chunks else ""

    strengths = [kw for kw in job_kws if kw in joined]
    weaknesses = [kw for kw in job_kws if kw not in joined]

    score = 0
    if job_kws:
        score = int(round(len(strengths) / max(1, len(job_kws)) * 100))

    # Scale scores a little to avoid very low values
    score = min(100, max(10, score))

    feedback = f"Match Score: {score}/100\n\n"
    if strengths:
        feedback += "✅ Strengths:\n" + "\n".join([f"- {s}" for s in strengths[:10]]) + "\n\n"
    if weaknesses:
        feedback += "⚠️ Weaknesses:\n" + "\n".join([f"- {w}" for w in weaknesses[:10]]) + "\n"

    return feedback.strip()

def safe_parse_feedback(raw_text: str):
    try:
        return json.loads(raw_text)
    except:
        if raw_text.strip().isdigit():
            return {"Match Score": raw_text.strip(), "Strengths": [], "Weaknesses": []}
        return None

def generate_feedback(job_desc: str, retrieved_chunks: List[str]) -> str:
    context = "\n".join(retrieved_chunks[:3])
    prompt = f"""
You are an AI resume evaluator.
Compare the following resume context against the job description.
Return ONLY JSON like this:
{{
  "Match Score": "78",
  "Strengths": ["Python", "Teamwork"],
  "Weaknesses": ["Leadership"]
}}

Job Description:
{job_desc}

Resume Context:
{context}
"""

    inputs = llm_tokenizer(prompt, return_tensors="pt", truncation=True)
    outputs = llm_model.generate(**inputs, max_new_tokens=300)
    raw_text = llm_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    print("[LLM RAW OUTPUT]:", raw_text)

    parsed = safe_parse_feedback(raw_text)

    if not isinstance(parsed, dict):
        print("[LLM RESULT NOT USABLE] Falling back to keyword scorer")
        return simple_keyword_feedback(job_desc, retrieved_chunks)

    score = parsed.get("Match Score", "0")
    strengths = parsed.get("Strengths", [])
    weaknesses = parsed.get("Weaknesses", [])

    feedback = f"Match Score: {score}/100\n\n"
    if strengths:
        feedback += "✅ Strengths:\n" + "\n".join([f"- {s}" for s in strengths]) + "\n\n"
    if weaknesses:
        feedback += "⚠️ Weaknesses:\n" + "\n".join([f"- {w}" for w in weaknesses]) + "\n"

    return feedback.strip()

# ---------------- API Models ----------------
class JobDescription(BaseModel):
    text: str

# ---------------- API Routes ----------------
@app.get("/")
async def root():
    return {"message": "AI Resume Suite (RAG)", "version": "3.4.0"}

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    file_id = str(uuid.uuid4())
    file_path = Path("uploads") / f"{file_id}.pdf"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(str(file_path))
        text = "".join([p.extract_text() or "" for p in reader.pages])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

    chunks = chunk_text(text)
    added = 0
    for chunk in chunks:
        if not chunk.strip():
            continue
        emb = embed_text(chunk)
        index.add(np.array([emb]))
        resume_chunks.append(chunk)
        chunk_ids.append(file_id)
        added += 1

    print(f"[UPLOAD] Added {added} chunks. index.ntotal={index.ntotal}")
    return {"status": "success", "chunks_added": added}

@app.post("/api/extract-text")
async def extract_text(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    file_path = Path("uploads") / f"jd_{uuid.uuid4()}.pdf"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(str(file_path))
        text = "".join([p.extract_text() or "" for p in reader.pages])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

    return {"text": text}

@app.post("/api/analyze-resume")
async def analyze_resume(job_description: JobDescription):
    if index.ntotal == 0:
        raise HTTPException(status_code=400, detail="No resumes uploaded")

    jd_emb = embed_text(job_description.text)
    D, I = index.search(np.array([jd_emb]), k=3)
    retrieved = [resume_chunks[i] for i in I[0] if i < len(resume_chunks)]

    print(f"[ANALYZE] Retrieved {len(retrieved)} chunks for JD")

    feedback = generate_feedback(job_description.text, retrieved)
    return {"feedback": feedback}
