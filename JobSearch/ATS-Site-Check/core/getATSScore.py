import os
import sys
import fitz  # PyMuPDF
from docx import Document
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

FOLDER = "resume-jd"

def read_file(path):
    """Read and extract text from TXT, DOCX, or PDF files."""
    if path.endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            return f.read()

    elif path.endswith(".docx"):
        doc = Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif path.endswith(".pdf"):
        text = []
        with fitz.open(path) as pdf:
            for page in pdf:
                text.append(page.get_text())
        return "\n".join(text)

    else:
        raise ValueError(f"Unsupported file type: {path}")

def compute_ats_score(resume_text, jd_text, model):
    """Compute cosine similarity between resume and JD embeddings."""
    emb = model.encode([resume_text, jd_text])
    return round(cosine_similarity([emb[0]], [emb[1]])[0][0] * 100, 2)

def main():
    if len(sys.argv) < 3:
        print("Usage: python ats_score.py <resume_filename> <jd_filename>")
        sys.exit(1)

    resume_name = sys.argv[1]
    jd_name = sys.argv[2]

    # allow full or relative paths
    resume_path = resume_name if os.path.exists(resume_name) else os.path.join(FOLDER, resume_name)
    jd_path = jd_name if os.path.exists(jd_name) else os.path.join(FOLDER, jd_name)

    if not os.path.exists(resume_path):
        print(f"Resume file not found: {resume_path}")
        sys.exit(1)
    if not os.path.exists(jd_path):
        print(f"JD file not found: {jd_path}")
        sys.exit(1)

    model = SentenceTransformer("all-MiniLM-L6-v2")

    resume_text = read_file(resume_path)
    jd_text = read_file(jd_path)

    score = compute_ats_score(resume_text, jd_text, model)
    print(f"{os.path.basename(resume_path)} vs {os.path.basename(jd_path)} → ATS Score: {score}%")

if __name__ == "__main__":
    main()