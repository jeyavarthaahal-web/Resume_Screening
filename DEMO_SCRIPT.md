# TalentIQ Demo Script (5–10 minutes)

## Introduction (about 45 seconds)

“Resume screening can be slow and inconsistent when reviewers have to manually compare every resume with every job description. TalentIQ organizes that information and makes the evidence easier to inspect. It supports human review; it does not make hiring decisions.”

## Solution (about 45 seconds)

“TalentIQ connects resume extraction, job analysis, match scoring, explainable evidence, recruiter workflow tools, and job-seeker career guidance. I’ll use separate recruiter and job-seeker test accounts and fictional resume information.”

## Resume Intelligence (about 1 minute)

Sign in as the job seeker. Upload a fictional PDF or DOCX resume and review the extracted contact/profile fields, skills, experience, education, projects, certifications, languages, and any fields marked for review. Explain that extraction is deterministic and has no OCR, so the user should verify the result.

## Job Intelligence (about 1 minute)

Switch to the recruiter test account. Create a Frontend Developer job with React, TypeScript, JavaScript, REST APIs, and Git. Analyze the description, review the extracted required/preferred skills and role fields, then choose **Published** so a job seeker can apply. Explain that publishing remains recruiter-owned and authenticated.

## AI Matching (about 1 minute)

Return to the job-seeker account and apply to the published role using the processed resume. Switch back to the recruiter and open that job's candidate list. Run matching and show the overall score with semantic similarity, skills, experience, education, and project components. State the existing weights: 40%, 25%, 15%, 10%, and 10% respectively.

## Explainability (about 1 minute)

Open the candidate's explanation. Point out matched, partial, and missing skills; strengths and gaps; source evidence; score contributions; and the written explanation. Emphasize that these are factual screening signals, not a hire/reject recommendation or a guarantee of fit.

## Recruiter Workspace (about 1 minute)

Add the candidate to the shortlist, write a short job-related note, and compare the candidate with another applied candidate if one is available. Show dashboard counts and the job's department, location, employment type, skills, experience, and education requirements. Do not invent a second profile merely to populate a comparison.

## Career Assistant (about 1 minute)

Sign in as the job seeker and open `/career-assistant`. Show resume review categories, skill-gap matched/missing/partial skills and learning areas, interview question groups, then send a chat message and show its response in the current conversation. Be transparent: these outputs currently use deterministic rules and templates, not a generative AI model. Assistant chat replies are not persisted as assistant-role database messages.

## Conclusion (about 30 seconds)

“TalentIQ turns documents into structured context, applies a consistent score, and exposes the evidence behind that score. Recruiters retain ownership of decisions, while job seekers get a profile and practical improvement guidance.”
