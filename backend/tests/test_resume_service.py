from __future__ import annotations

from pathlib import Path

import fitz

from app.services.resume_service import (
    AI_CRITERIA,
    FORMAT_CHECK_MAX,
    SECTION_MAX,
    evaluate_resume,
    extract_template_sections,
    score_resume,
)


SAMPLE_RESUME = """Prateek Rai
+91 9876543210 | prateek@example.com | https://linkedin.com/in/prateek | https://github.com/prateek | https://prateek.dev
SUMMARY
Builds Python backend systems focused on AI products and seeks a Python Backend Intern role.
EDUCATION
Lloyd Institute of Engineering and Technology | 2023 - 2027
B.Tech CSE | CGPA: 8.2/10
ABC School — 12th Standard | CBSE | 85% | 2023
ABC School — 10th Standard | CBSE | 90% | 2021
EXPERIENCE
Example Labs | Backend Intern | Jan 2025 - Apr 2025
Built FastAPI services and reduced response time by 20%.
Collaborated with the team to ship an API used by 10 testers.
Tech: Python, FastAPI, PostgreSQL
PROJECTS
Campus AI | FastAPI, React, PostgreSQL | Jan 2026
Built a campus assistant for students using searchable study documents.
Implemented retrieval with PostgreSQL and embeddings.
Tested with 20 students.
Live: https://campus.example.com Code: https://github.com/prateek/campus
Payment Safety | Python, FastAPI | Dec 2025
Built a payment safety tool that warns users about suspicious URLs.
Implemented URL risk scoring and validation rules.
Tested with 30 sample URLs.
Live: https://safety.example.com Code: https://github.com/prateek/safety
TECHNICAL SKILLS
Languages: Python, JavaScript, SQL
Frontend: React, Tailwind CSS
Backend: FastAPI
Databases: PostgreSQL
Cloud & DevOps: Docker, GitHub Actions
AI / ML: RAG, Gemini API
Developer Tools: VS Code, Postman
ACHIEVEMENTS
• Top 10 in a hackathon with a team of 4.
CERTIFICATIONS
• Python Certificate — ABC Academy https://example.com/certificate Jan 2026
"""


def make_ai_review(rating: str = "good") -> dict:
    evidence_by_criterion = {
        "summary_one_line": "Builds Python backend systems focused on AI products and seeks a Python Backend Intern role.",
        "summary_what_build": "Builds Python backend systems focused on AI products and seeks a Python Backend Intern role.",
        "summary_niche_strength": "Builds Python backend systems focused on AI products and seeks a Python Backend Intern role.",
        "summary_target_role": "Builds Python backend systems focused on AI products and seeks a Python Backend Intern role.",
        "experience_company_role_dates": "Example Labs | Backend Intern | Jan 2025 - Apr 2025",
        "experience_built_tech_impact": "Built FastAPI services and reduced response time by 20%.",
        "experience_owned_outcome": "Collaborated with the team to ship an API used by 10 testers.",
        "experience_bullet_quality": "Built FastAPI services and reduced response time by 20%.",
        "projects_name_stack_dates": "Campus AI | FastAPI, React, PostgreSQL | Jan 2026",
        "projects_problem_users": "Built a campus assistant for students using searchable study documents.",
        "projects_implementation_decision": "Implemented retrieval with PostgreSQL and embeddings.",
        "projects_outcome": "Tested with 20 students.",
        "achievements_context": "Top 10 in a hackathon with a team of 4.",
        "achievements_specificity": "Top 10 in a hackathon with a team of 4.",
        "certifications_name_issuer": "Python Certificate — ABC Academy",
    }
    assessments = []
    for criterion_id in AI_CRITERIA:
        assessments.append(
            {
                "criterion_id": criterion_id,
                "rating": rating,
                "evidence": evidence_by_criterion[criterion_id],
                "finding": "Assessed against the reference template.",
                "suggestion": "",
            }
        )
    return {
        "extracted_resume": {
            "name": "Prateek Rai",
            "projects": [{"name": "Campus AI"}, {"name": "Payment Safety"}],
        },
        "criterion_assessments": assessments,
        "strengths": ["Projects include a problem statement and implementation details."],
        "priority_changes": [],
        "jd_alignment": {
            "available": True,
            "summary": "Example alignment summary.",
            "requirements": [
                {"requirement": "Python", "importance": "required", "status": "evidenced", "evidence": "Python", "reason": "Skill appears in the resume.", "suggestion": ""},
                {"requirement": "Docker", "importance": "preferred", "status": "not_found", "evidence": "", "reason": "No evidence found.", "suggestion": "Add evidence only if you have used it."},
            ],
        },
    }


def make_pdf(path: Path, text: str = SAMPLE_RESUME) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    y = 42
    for line in text.splitlines():
        if not line:
            continue
        font_size = 10
        if line.strip().upper() in {"SUMMARY", "EDUCATION", "EXPERIENCE", "PROJECTS", "TECHNICAL SKILLS", "ACHIEVEMENTS", "CERTIFICATIONS"}:
            font_size = 12
        page.insert_text((48, y), line[:95], fontsize=font_size)
        y += 16
        if y > 750:
            break
    doc.save(path)
    doc.close()
    return path


def test_template_rubric_sums_to_100() -> None:
    assert sum(SECTION_MAX.values()) == 80
    assert sum(FORMAT_CHECK_MAX.values()) == 20
    assert sum(SECTION_MAX.values()) + sum(FORMAT_CHECK_MAX.values()) == 100


def test_extract_template_sections_detects_reference_headings() -> None:
    sections, positions, _ = extract_template_sections(SAMPLE_RESUME)
    assert "SUMMARY" in positions
    assert "TECHNICAL SKILLS" in positions
    assert "Prateek Rai" in sections["header"]
    assert any("Python" in line for line in sections["skills"])


def test_resume_template_evaluation_has_section_and_format_breakdown(tmp_path: Path) -> None:
    pdf_path = make_pdf(tmp_path / "resume.pdf")
    result = evaluate_resume(SAMPLE_RESUME, make_ai_review(), pdf_path, None)

    assert 0 <= result["resume_score"] <= 100
    assert result["score_breakdown"]["total"]["max_score"] == 100
    assert result["score_breakdown"]["total"]["rubric"].startswith("ATS_Resume_Template_2026")
    assert set(result["score_breakdown"]["content_sections"]) == {
        "header", "summary", "education", "experience", "projects", "skills", "achievements", "certifications"
    }
    assert result["score_breakdown"]["format"]["max_score"] == 20
    format_checks = result["feedback"]["format_feedback"]["checks"]
    assert len(format_checks) == 8
    assert sum(item["max_score"] for item in format_checks) == 20
    assert result["keyword_coverage"]["available"] is False


def test_missing_section_cannot_receive_ai_content_points(tmp_path: Path) -> None:
    resume_without_projects = SAMPLE_RESUME.replace("PROJECTS\n", "WORK SAMPLES\n")
    pdf_path = make_pdf(tmp_path / "missing_projects.pdf", resume_without_projects)
    result = evaluate_resume(resume_without_projects, make_ai_review("good"), pdf_path, None)

    projects = result["score_breakdown"]["content_sections"]["projects"]
    assert projects["score"] == 0
    assert projects["max_score"] == 18


def test_ai_rating_is_mapped_to_fixed_rubric_points(tmp_path: Path) -> None:
    pdf_path = make_pdf(tmp_path / "partial.pdf")
    result = evaluate_resume(SAMPLE_RESUME, make_ai_review("partial"), pdf_path, None)
    summary = result["score_breakdown"]["content_sections"]["summary"]

    # The one point heading is deterministic; remaining seven summary points are AI-rated at 50%.
    assert summary["score"] == 4.5
    assert summary["max_score"] == 8


def test_job_description_alignment_is_separate_from_template_score(tmp_path: Path) -> None:
    pdf_path = make_pdf(tmp_path / "jd.pdf")
    without_jd = evaluate_resume(SAMPLE_RESUME, make_ai_review(), pdf_path, None)
    with_jd = evaluate_resume(SAMPLE_RESUME, make_ai_review(), pdf_path, "Python and Docker required")

    assert with_jd["resume_score"] == without_jd["resume_score"]
    assert with_jd["keyword_coverage"]["available"] is True
    assert with_jd["keyword_coverage"]["alignment_score"] is not None
    assert with_jd["keyword_coverage"]["requirements_count"] == 2


def test_model_evidence_must_be_an_exact_resume_quote(tmp_path: Path) -> None:
    review = make_ai_review()
    review["criterion_assessments"][0]["evidence"] = "This quote is not actually in the resume."
    pdf_path = make_pdf(tmp_path / "evidence.pdf")
    result = evaluate_resume(SAMPLE_RESUME, review, pdf_path, None)
    summary_criteria = result["score_breakdown"]["content_sections"]["summary"]["criteria"]
    first_criterion = next(item for item in summary_criteria if item["id"] == "summary_one_line")
    assert first_criterion["score"] == 0
    assert first_criterion["evidence"] == ""


def test_backward_compatible_score_helper_is_template_specific() -> None:
    score, breakdown = score_resume(SAMPLE_RESUME, make_ai_review())
    assert 0 <= score <= 80  # This legacy helper does not include PDF-format points.
    assert breakdown["total"]["max_score"] == 100


def test_reference_template_pdf_layout_matches_its_own_format_rules() -> None:
    reference_pdf = Path(__file__).resolve().parents[1] / "reference" / "ATS_Resume_Template_2026.pdf"
    doc = fitz.open(reference_pdf)
    text = "\n".join(f"[Page {i + 1}]\n{page.get_text()}" for i, page in enumerate(doc))
    doc.close()
    _, positions, _ = extract_template_sections(text)
    result = evaluate_resume(text, make_ai_review(), reference_pdf, None)
    assert result["score_breakdown"]["format"]["score"] == 20
    assert result["score_breakdown"]["format"]["max_score"] == 20


def test_template_placeholder_links_are_not_counted_as_real_links() -> None:
    from app.services.resume_service import _pdf_link_regions

    reference_pdf = Path(__file__).resolve().parents[1] / "reference" / "ATS_Resume_Template_2026.pdf"
    links = _pdf_link_regions(reference_pdf)
    assert links["header"] == []
    assert links["projects"] == []


def test_job_alignment_requires_verifiable_resume_evidence(tmp_path: Path) -> None:
    review = make_ai_review()
    review["jd_alignment"]["requirements"][0]["evidence"] = "This fabricated quote is not in the resume."
    pdf_path = make_pdf(tmp_path / "jd_evidence.pdf")
    result = evaluate_resume(SAMPLE_RESUME, review, pdf_path, "Python required")
    requirement = result["keyword_coverage"]["requirements"][0]
    assert requirement["status"] == "not_found"
    assert requirement["evidence"] == ""
    assert "verbatim quote" in requirement["reason"]
    assert result["keyword_coverage"]["alignment_score"] == 0
