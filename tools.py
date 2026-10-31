
"""Deterministic tools used by the Resume Reviewer agent."""
import re
from io import BytesIO
from pypdf import PdfReader

SKILL_BANK = [
    "python", "java", "javascript", "typescript", "c++", "sql", "mysql", "postgresql",
    "mongodb", "machine learning", "deep learning", "natural language processing", "nlp",
    "artificial intelligence", "generative ai", "llm", "langchain", "langgraph", "rag",
    "prompt engineering", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "data analysis", "data visualization", "power bi", "tableau", "excel", "statistics",
    "docker", "kubernetes", "aws", "azure", "google cloud", "git", "github", "linux",
    "fastapi", "flask", "django", "streamlit", "react", "node.js", "html", "css",
    "communication", "leadership", "problem solving", "project management", "agile"
]


def extract_resume_text(pdf_bytes: bytes) -> str:
    """Extract selectable text from a PDF. Scanned PDFs need OCR."""
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")

    reader = PdfReader(BytesIO(pdf_bytes))

    text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    )

    text = re.sub(r"[ \t]+", " ", text)

    if not text.strip():
        raise ValueError(
            "No selectable text was found. This may be a scanned PDF; "
            "use a text-based PDF."
        )

    return text.strip()


def keyword_skills(text: str) -> list[str]:
    """Fallback skill extraction based on a transparent vocabulary."""
    lower = text.lower()
    found = []

    for skill in SKILL_BANK:
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"

        if re.search(pattern, lower):
            found.append(
                skill.title()
                if skill not in {"nlp", "llm", "aws", "sql", "html", "css", "c++"}
                else skill.upper()
            )

    return found


def calculate_ats_score(
    resume_text: str,
    required_skills: list[str]
) -> dict:
    """Transparent keyword-match indicator, not a real ATS vendor score."""

    required = list(dict.fromkeys(
        s.strip() for s in required_skills if s and s.strip()
    ))

    lower = resume_text.lower()
    matched, missing = [], []

    for skill in required:
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(skill.lower())
            + r"(?![a-z0-9])"
        )

        (matched if re.search(pattern, lower) else missing).append(skill)

    score = (
        round(100 * len(matched) / len(required))
        if required else 0
    )

    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "score_breakdown": {
            "matched": len(matched),
            "required": len(required)
        }
    }
