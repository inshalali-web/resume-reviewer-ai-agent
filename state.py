from typing import TypedDict, List, Dict, Any


class ResumeState(TypedDict, total=False):
    resume_bytes: bytes
    resume_filename: str
    job_description: str
    resume_text: str
    resume_profile: Dict[str, Any]
    required_skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    ats_score: int
    score_breakdown: Dict[str, int]
    feedback: str
    improved_summary: str
    logs: List[str]
    error: str
    retry_count: int
    used_fallback: bool
