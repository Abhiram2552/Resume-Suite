# Review-Suite — Resume ↔ Job Description Matcher

Fast, lightweight resume analysis. Upload a resume + paste a JD, get:
- A **match score**
- Clear **strengths** & **gaps**
- Plain-English feedback (LLM) with a **keyword fallback** when the model underperforms

Works great on CPU with a small model locally; you can switch to a stronger model when you deploy.

---

##  Project Structure

```
repo-root/
├─ review-suite/
│  ├─ backend/              # FastAPI app (LLM + fallback, FAISS index, endpoints)
│  └─ frontend/             # Static frontend (HTML/CSS/JS)
├─ requirements.txt         # Python deps for HF and local
├─ runtime.txt              # Python version hint (for HF Spaces)
└─ README.md                # this file
```

> Put `requirements.txt` and `runtime.txt` **at the repo root** (same level as `review-suite/`).

---

##  Features

- **LLM scoring** using `google/flan-t5-base` (CPU-friendly)
- **Robust JSON parsing** (won’t crash if model returns a bare number like `78`)
- **Keyword fallback** (TF-IDF / simple overlap) only when LLM output is unusable
- **Clear frontend text output** (not raw JSON)
- **FAISS** chunk retrieval for JD/resume context

---

##  Local Development

### 1) Prereqs
- Python **3.10** (recommended for Hugging Face & packages)
- Node (optional, only if you want a local static server for the frontend)
- Git

### 2) Create & activate a venv
```bash
cd path/to/repo-root
python3.10 -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3) Install deps
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Run the backend
```bash
cd review-suite/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Backend now at: `http://localhost:8000`

### 5) Open the frontend
- Option A: simply open `review-suite/frontend/index.html` in your browser  
- Option B (nice dev server):  
  ```bash
  cd review-suite/frontend
  python -m http.server 5173
  ```
  Visit `http://localhost:5173`

---

##  API Overview (FastAPI)

Endpoints under `/api/*`:

1. **Upload resume** → `POST /api/upload-resume`  
2. **Extract text** → `POST /api/extract-text`  
3. **Analyze resume** → `POST /api/analyze-resume`  

Response includes:  
```json
{
  "match_score": 78,
  "strengths": ["…"],
  "weaknesses": ["…"],
  "feedback_text": "Plain-English feedback…"
}
```

---

##  Model & Fallback Logic

- Ask LLM for JSON `{ Match Score, Strengths, Weaknesses }`  
- If invalid → fallback to keyword scorer  
- Still produce usable results

---

##  Files You Must Have

### `requirements.txt`
```
fastapi==0.110.0
uvicorn[standard]==0.29.0
pydantic==2.7.4
python-multipart==0.0.9
jinja2==3.1.4
transformers==4.42.4
torch==2.3.1
accelerate==0.33.0
faiss-cpu==1.8.0
sentence-transformers==3.0.1
scikit-learn==1.4.2
numpy==1.26.4
tqdm==4.66.4
```

### `runtime.txt`
```
python-3.10
```

---

##  Deploy to Hugging Face Spaces

Use a **Gradio Space** with an `app.py` mounting FastAPI.  
Frontend can be served separately (Static Space) or together.

---

## Quick Test
```bash
curl -X POST http://localhost:8000/api/analyze-resume   -H "Content-Type: application/json"   -d '{"job_description":"Python dev","resume_text":"I worked with FastAPI"}'
```

---

## 📝 License

MIT (or your choice). Add a `LICENSE` file if you want!
