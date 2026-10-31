
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Resume Reviewer AI Agent",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Resume Reviewer AI Agent")
st.markdown("AI-powered resume analysis using a multi-agent workflow.")

with st.sidebar:
    st.header("Agent Settings")

    api_key = os.getenv("GEMINI_API_KEY", "")

    if api_key and api_key != "PASTE_YOUR_KEY_HERE":
        st.success("Gemini API key detected")
    else:
        st.warning("Demo Mode: No API key")

    st.markdown("---")
    st.markdown("""
    **Agent Workflow**
    1. Resume Parser
    2. Job Analyzer
    3. Resume Evaluator
    4. Improvement Coach
    5. Quality Check
    """)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Upload Resume")

    uploaded_file = st.file_uploader(
        "Upload your resume (PDF)",
        type=["pdf"]
    )

with col2:
    st.subheader("💼 Job Description")

    job_description = st.text_area(
        "Paste the target job description",
        height=220,
        placeholder="Enter the skills, qualifications and experience required..."
    )

if st.button("🚀 Analyze Resume", type="primary", use_container_width=True):

    if uploaded_file is None:
        st.error("Please upload a PDF resume.")

    elif not job_description.strip():
        st.error("Please enter a job description.")

    else:
        try:
            with st.spinner("AI Agents are analyzing your resume..."):

                from agents import run_resume_review

                result = run_resume_review(
                    uploaded_file.getvalue(),
                    uploaded_file.name,
                    job_description
                )

            if result.get("error") and not result.get("resume_text"):
                st.error(result["error"])

            else:
                st.success("Resume analysis completed!")

                st.divider()
                st.header("📊 Analysis Results")

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "ATS Keyword Match",
                    f"{result.get('ats_score', 0)}%"
                )

                c2.metric(
                    "Matched Skills",
                    len(result.get("matched_skills", []))
                )

                c3.metric(
                    "Missing Skills",
                    len(result.get("missing_skills", []))
                )

                st.progress(
                    result.get("ats_score", 0) / 100
                )

                tab1, tab2, tab3, tab4 = st.tabs([
                    "Skill Match",
                    "Resume Profile",
                    "Recommendations",
                    "Agent Execution Logs"
                ])

                with tab1:
                    left, right = st.columns(2)

                    with left:
                        st.subheader("✅ Matched Skills")
                        st.write(
                            result.get("matched_skills", [])
                        )

                    with right:
                        st.subheader("⚠️ Missing Skills")
                        st.write(
                            result.get("missing_skills", [])
                        )

                    st.subheader("Required Job Skills")
                    st.write(
                        result.get("required_skills", [])
                    )

                with tab2:
                    st.json(result.get("resume_profile", {}))

                with tab3:
                    st.markdown(
                        result.get("feedback", "No feedback available.")
                    )

                    st.subheader("Improved Professional Summary")

                    st.write(
                        result.get("improved_summary", "")
                    )

                with tab4:
                    for log in result.get("logs", []):
                        st.code(log)

                    st.subheader("Shared Agent State")
                    st.json({
                        key: value
                        for key, value in result.items()
                        if key not in ["resume_bytes", "resume_text"]
                    })

        except Exception as e:
            st.error("Something went wrong while executing the agents.")
            st.exception(e)

st.divider()

st.caption(
    "Powered by Python | Streamlit | LangGraph | Gemini | PyMuPDF"
)
