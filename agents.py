"""LangGraph workflow: parser -> job analyzer -> evaluator -> improvement coach."""
import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, START, END

from state import ResumeState
from tools import extract_resume_text, keyword_skills, calculate_ats_score

load_dotenv()


def _client():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "PASTE_YOUR_KEY_HERE":
        return None
    return genai.Client(api_key=key)


def _model_name():
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"


def _ask_gemini(prompt: str, json_mode: bool = False) -> str:
    client = _client()
    if client is None:
        raise RuntimeError("Gemini API key is not configured. Running fallback mode.")
    config = types.GenerateContentConfig(temperature=0.2)
    if json_mode:
        config = types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
    response = client.models.generate_content(model=_model_name(), contents=prompt, config=config)
    result = (response.text or "").strip()
    if not result:
        raise RuntimeError("Gemini returned an empty response.")
    return result


def _json_from_text(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError("The AI response was not valid JSON.")
        return json.loads(match.group(0))


def parse_resume(state: ResumeState) -> dict:
    logs = state.get("logs", []) + ["Resume Parser: extracting PDF text with PyMuPDF"]
    try:
        resume_text = extract_resume_text(state["resume_bytes"])
        profile = {"skills": keyword_skills(resume_text), "summary": resume_text[:1200]}
        used_fallback = False
        try:
            prompt = f"""Extract a concise factual resume profile. Do not invent details. Return JSON only with keys: name (string or empty), skills (array of strings), education (array of strings), experience (array of strings), projects (array of strings), strengths (array of strings).\nRESUME:\n{resume_text[:14000]}"""
            profile = _json_from_text(_ask_gemini(prompt, json_mode=True))
            used_fallback = False
            logs.append("Resume Parser: Gemini profile extraction completed")
        except Exception as exc:
            profile["name"] = ""
            profile["education"] = []
            profile["experience"] = []
            profile["projects"] = []
            profile["strengths"] = []
            used_fallback = True
            logs.append(f"Resume Parser: fallback used ({type(exc).__name__})")
        return {"resume_text": resume_text, "resume_profile": profile, "used_fallback": used_fallback, "logs": logs}
    except Exception as exc:
        return {"error": str(exc), "logs": logs + [f"Resume Parser ERROR: {exc}"]}


def analyze_job(state: ResumeState) -> dict:
    logs = state.get("logs", []) + ["Job Analyzer: identifying required skills from job description"]
    try:
        prompt = f"""Read this job description and return JSON only: {{\"required_skills\": [\"skill 1\", \"skill 2\"]}}. Include 6-15 concrete technical or role-relevant skills explicitly required or strongly implied. Do not add unrelated skills.\nJOB DESCRIPTION:\n{state['job_description'][:10000]}"""
        data = _json_from_text(_ask_gemini(prompt, json_mode=True))
        skills = data.get("required_skills", [])
        if not isinstance(skills, list) or not skills:
            raise ValueError("No required skills were returned.")
        skills = list(dict.fromkeys(str(s).strip() for s in skills if str(s).strip()))[:20]
        logs.append(f"Job Analyzer: identified {len(skills)} job requirements using Gemini")
        return {"required_skills": skills, "logs": logs}
    except Exception as exc:
        # Resilient fallback: infer requirements from known skill terms in the JD.
        skills = keyword_skills(state["job_description"])
        logs.append(f"Job Analyzer: keyword fallback used ({type(exc).__name__}); found {len(skills)} skills")
        if not skills:
            return {"required_skills": [], "error": "Could not identify skills. Add a more detailed job description.", "logs": logs}
        return {"required_skills": skills, "used_fallback": True, "logs": logs}


def evaluate_resume(state: ResumeState) -> dict:
    logs = state.get("logs", []) + ["Resume Evaluator: calling Python ATS keyword scoring tool"]
    result = calculate_ats_score(state["resume_text"], state.get("required_skills", []))
    logs.append(f"Resume Evaluator: score calculated = {result['score']}/100")
    return {
        "ats_score": result["score"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "score_breakdown": result["score_breakdown"],
        "logs": logs
    }


def improvement_coach(state: ResumeState) -> dict:
    logs = state.get("logs", []) + ["Improvement Agent: generating recommendations"]
    profile = state.get("resume_profile", {})
    prompt = f"""You are a practical resume coach. Give specific, truthful suggestions based only on the provided information. Never invent experience, qualifications, employers, metrics, or skills.\nJOB DESCRIPTION:\n{state['job_description'][:5000]}\nRESUME PROFILE:\n{json.dumps(profile, ensure_ascii=False)[:5000]}\nMATCHED SKILLS: {state.get('matched_skills', [])}\nMISSING SKILLS: {state.get('missing_skills', [])}\nATS KEYWORD MATCH: {state.get('ats_score', 0)}/100\nReturn concise Markdown with headings: Top Findings, Priority Improvements (3-5 bullets), Keywords to Add (only if truthful), and Interview Preparation (2 questions). Then on a final line write IMPROVED_SUMMARY: followed by a 2-3 sentence draft using only supported facts. If a fact is missing, use a placeholder rather than inventing it."""
    try:
        feedback = _ask_gemini(prompt)
        summary = ""
        if "IMPROVED_SUMMARY:" in feedback:
            feedback, summary = feedback.split("IMPROVED_SUMMARY:", 1)
            summary = summary.strip()
        logs.append("Improvement Agent: Gemini recommendations generated")
        return {"feedback": feedback.strip(), "improved_summary": summary, "logs": logs}
    except Exception as exc:
        matched = ", ".join(state.get("matched_skills", [])) or "No direct keyword matches detected"
        missing = ", ".join(state.get("missing_skills", [])) or "No missing keywords detected"
        feedback = (
            "### Top Findings\n"
            f"- The resume has a {state.get('ats_score', 0)}% keyword match against the selected requirements.\n"
            f"- Matching skills: {matched}.\n"
            f"- Missing skills: {missing}.\n\n"
            "### Priority Improvements\n"
            "- Add measurable outcomes to project and work bullets where you can verify the numbers.\n"
            "- Put the most relevant skills near the top of the resume.\n"
            "- Tailor project descriptions to the responsibilities in the job description.\n"
            "- Use clear action verbs and consistent date formatting.\n\n"
            "### Keywords to Add\n"
            "Only add missing keywords if you genuinely have the skill or experience.\n\n"
            "### Interview Preparation\n"
            "- Explain one project that demonstrates your strongest matching skill.\n"
            "- Describe how you would approach a responsibility listed in the job description."
        )
        logs.append(f"Improvement Agent: fallback feedback used ({type(exc).__name__})")
        return {"feedback": feedback, "improved_summary": "Write a 2-3 sentence summary connecting your verified experience and strongest matching skills to this role.", "used_fallback": True, "logs": logs}


def validate_output(state: ResumeState) -> dict:
    logs = state.get("logs", []) + ["Quality Check: validating required output fields"]
    issues = []
    if not state.get("resume_text"):
        issues.append("Resume text missing")
    if not state.get("required_skills"):
        issues.append("Required skills missing")
    if not state.get("feedback"):
        issues.append("Feedback missing")
    if issues:
        logs.append("Quality Check: incomplete output - " + "; ".join(issues))
        return {"error": "; ".join(issues), "logs": logs}
    logs.append("Quality Check: passed")
    return {"logs": logs}


def route_after_parse(state: ResumeState) -> str:
    return "stop" if state.get("error") else "continue"


def build_graph():
    graph = StateGraph(ResumeState)
    graph.add_node("resume_parser", parse_resume)
    graph.add_node("job_analyzer", analyze_job)
    graph.add_node("resume_evaluator", evaluate_resume)
    graph.add_node("improvement_coach", improvement_coach)
    graph.add_node("quality_check", validate_output)
    graph.add_edge(START, "resume_parser")
    graph.add_conditional_edges("resume_parser", route_after_parse, {"continue": "job_analyzer", "stop": END})
    graph.add_edge("job_analyzer", "resume_evaluator")
    graph.add_edge("resume_evaluator", "improvement_coach")
    graph.add_edge("improvement_coach", "quality_check")
    graph.add_edge("quality_check", END)
    return graph.compile()


resume_agent = build_graph()


def run_resume_review(pdf_bytes: bytes, filename: str, job_description: str) -> dict:
    initial_state: ResumeState = {
        "resume_bytes": pdf_bytes,
        "resume_filename": filename,
        "job_description": job_description,
        "logs": [],
        "retry_count": 0,
        "used_fallback": False,
    }
    return resume_agent.invoke(initial_state)
