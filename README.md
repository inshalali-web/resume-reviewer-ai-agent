# Resume Reviewer AI Agent

A classroom MVP demonstrating a multi-step LangGraph workflow with PDF extraction, job-description analysis, Python keyword scoring, AI recommendations, shared state, execution logs, and fallback handling.

## Requirements
- Windows 10/11
- Python 3.10 or newer
- VS Code with Python extension
- Optional Gemini API key from https://aistudio.google.com/apikey

## Setup (PowerShell terminal in VS Code)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and replace `PASTE_YOUR_KEY_HERE` with your Gemini API key. If you leave it unchanged, the app runs in fallback/demo mode.

## Run

```powershell
streamlit run app.py
```

## Workflow
1. Resume Parser: extracts PDF text with PyMuPDF and optionally asks Gemini for a structured profile.
2. Job Analyzer: identifies required skills with Gemini; falls back to a local skill vocabulary.
3. Resume Evaluator: calls a Python tool to compare keywords and calculate a transparent score.
4. Improvement Coach: generates tailored suggestions with Gemini or a deterministic fallback.
5. Quality Check: validates required outputs and logs the result.

## Demo tips
- Use a text-based PDF, not a scanned image-only PDF.
- Paste a job description with specific skills.
- Show the Agent Trace tab to the evaluator.
- Test an empty job description in the UI and an image-only/scanned PDF to demonstrate validation.
- Disconnect the API key (or use an invalid key) to demonstrate fallback behavior.

## Important limitation
The score is a simple exact-keyword match indicator over extracted skills. It is not a real ATS vendor score, does not assess hiring probability, and should not be used as the sole basis for hiring decisions. The app processes resume data locally for PDF extraction, but when Gemini is configured, extracted resume text is sent to Google's Gemini API for analysis. Use sample or consented data for classroom demos.
