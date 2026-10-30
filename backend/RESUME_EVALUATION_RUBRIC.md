# Resume evaluation rubric — ATS_Resume_Template_2026

This rubric is derived from the section names, examples, and content instructions in the user-provided `reference/ATS_Resume_Template_2026.pdf`. The reference PDF does not itself define point values; the weights below are the application's explicit, transparent scoring design.

## Score composition

- Template content: 80 points
- PDF format: 20 points
- Total: 100 points
- Job-description alignment: separate optional report; it never changes the 100-point template score.

## Template content: 80 points

| Section | Criterion | Points |
|---|---|---:|
| Header | Candidate name | 2 |
| Header | Email address | 2 |
| Header | Phone number | 2 |
| Header | LinkedIn profile | 1.5 |
| Header | GitHub profile | 1.5 |
| Header | Portfolio link | 1 |
| **Header subtotal** | | **10** |
| Summary | `SUMMARY` heading | 1 |
| Summary | Concise, approximately one-line summary | 1 |
| Summary | Says what the candidate builds | 2 |
| Summary | States niche or strength | 2 |
| Summary | Names target role | 2 |
| **Summary subtotal** | | **8** |
| Education | `EDUCATION` heading | 1 |
| Education | College/institution | 2 |
| Education | Degree | 2 |
| Education | Dates | 1 |
| Education | CGPA/GPA | 1 |
| Education | Class 12 school, board, result and date | 1.5 |
| Education | Class 10 school, board, result and date | 1.5 |
| **Education subtotal** | | **10** |
| Experience | `EXPERIENCE` heading | 1 |
| Experience | Company, role and dates | 2 |
| Experience | Built/designed/led work with technology and impact | 3 |
| Experience | Ownership/collaboration and outcome | 3 |
| Experience | Clear, concrete bullets | 1 |
| Experience | Actual technologies used are listed | 2 |
| **Experience subtotal** | | **12** |
| Projects | `PROJECTS` heading | 1 |
| Projects | Two project entries, as shown in the reference | 2 |
| Projects | Project name, stack and date | 3 |
| Projects | Problem and affected users | 3 |
| Projects | What was built and a key technical decision | 4 |
| Projects | Quantified or verifiable outcome | 3 |
| Projects | Live demo and source-code links | 2 |
| **Projects subtotal** | | **18** |
| Technical Skills | `TECHNICAL SKILLS` heading | 1 |
| Technical Skills | Languages category | 1 |
| Technical Skills | Frontend category | 1 |
| Technical Skills | Backend category | 1 |
| Technical Skills | Databases category | 1 |
| Technical Skills | Cloud & DevOps category | 1 |
| Technical Skills | AI / ML category | 1 |
| Technical Skills | Developer Tools category | 1 |
| Technical Skills | Categories contain actual skills | 2 |
| Technical Skills | Skills are grouped under category labels | 2 |
| **Technical Skills subtotal** | | **12** |
| Achievements | `ACHIEVEMENTS` heading | 1 |
| Achievements | At least one achievement entry | 1 |
| Achievements | Rank, team size or meaningful award context | 2 |
| Achievements | Entry is specific and interpretable | 1 |
| **Achievements subtotal** | | **5** |
| Certifications | `CERTIFICATIONS` heading | 1 |
| Certifications | At least one certification entry | 1 |
| Certifications | Certificate name and issuing body | 1 |
| Certifications | Certificate link | 1 |
| Certifications | Certificate date | 1 |
| **Certifications subtotal** | | **5** |
| **Content total** | | **80** |

## PDF format: 20 points

| Format check | Points | What the code checks |
|---|---:|---|
| Page count | 3 | Reference is one page; two pages receive partial credit; more pages receive no points. |
| Section order | 3 | Detected template headings follow the reference order. |
| Single-column layout | 3 | PDF text geometry is checked for repeated side-by-side body-text rows. |
| Typography | 3 | Extracted font sizes are checked for readability and extreme variation. |
| Margins and alignment | 3 | Text remains within page bounds and section headings align consistently. |
| Spacing consistency | 2 | Vertical gaps are checked for unusually large unexplained spaces. |
| Bullet consistency | 2 | Extracted bullet markers are checked for consistency. |
| Text extractability | 1 | PDF contains a sufficient selectable text layer without obvious replacement characters. |
| **Format total** | **20** | |

These are deterministic PDF-text and geometry heuristics. They are not a pixel-perfect visual comparison or a test against a specific employer's ATS parser. Scanned PDFs are not supported in this version.

## How AI ratings become points

Gemini is asked to rate only the semantic criteria stated by the supplied template:

- `good`: 100% of that criterion's points
- `partial`: 50%
- `weak`: 25%
- `missing`: 0%

Python calculates the score. For positive AI ratings, the returned evidence quote must be a verbatim substring of the extracted resume text; otherwise no points are awarded for that AI criterion. Missing required template section headings cannot receive that section's content points.

## Optional job-description alignment

When the student supplies a job description, Gemini extracts distinct requirements and classifies the resume evidence as:

- `evidenced`
- `partial_evidence`
- `not_found`

Required requirements receive weight 2; preferred requirements receive weight 1. Evidence statuses contribute 100%, 50%, and 0% respectively. A positive evidence classification is retained only if the model provides an exact quote found in the resume text. If not, it is changed to `not_found`.

This alignment score is separate from template compliance. `not_found` means the evidence was not found in the submitted resume; it does not establish that the student lacks the skill.

## Fairness and limitations

- The reference includes Experience, Achievements, and Certifications. The strict section rubric can therefore deduct points from a fresher who has no corresponding entry. The system must not ask anyone to fabricate experience, awards, certificates, dates, or measurements.
- The reference PDF does not publish numerical weights. The app's point allocation is a product decision informed by the template structure.
- A good score means the document matches this reference rubric; it is not a universal ATS score, selection probability, or guarantee of an interview.
- A human should review the report and visually inspect the original PDF before relying on automated layout findings.
