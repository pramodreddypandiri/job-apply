# Agents & AI Pipeline

All LLM calls go through `backend/llm/client.py`.
Use **claude-haiku-4-5** for extraction/classification tasks.
Use **claude-sonnet-4-5** for generation tasks (resume, cover letter, prep plan).

---

## LLM Client

```python
# backend/llm/client.py
import anthropic
from enum import Enum

class Model(str, Enum):
    HAIKU  = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-5"

client = anthropic.Anthropic()

def extract(prompt: str, system: str, max_tokens: int = 1000) -> dict:
    """Use Haiku for all extraction/classification. Returns parsed JSON."""
    response = client.messages.create(
        model=Model.HAIKU,
        max_tokens=max_tokens,
        system=system + "\n\nRespond ONLY with valid JSON. No preamble, no markdown.",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.content[0].text)

def generate(prompt: str, system: str, max_tokens: int = 4000) -> str:
    """Use Sonnet for all generation tasks. Returns plain text."""
    response = client.messages.create(
        model=Model.SONNET,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

---

## Agent 1: JD Parser

**File:** `backend/agents/jd_parser.py`
**Model:** Haiku
**Input:** Raw HTML or text from job URL
**Output:** Structured JD object

```python
SYSTEM = """
You are a job description parser. Extract structured information from job postings.
Be precise. If a field is not mentioned, use null.
"""

PROMPT_TEMPLATE = """
Parse this job description and return JSON with this exact structure:
{
  "company_name": str,
  "role_title": str,
  "role_title_normalised": str,   // lowercase, no seniority prefix
  "seniority": str,               // "junior"|"mid"|"senior"|"staff"|"principal"|"director"
  "location": str,                // "Remote"|"City, Country"|"Hybrid - City"
  "team": str | null,
  "ats_type": str | null,         // detected from URL or form fields
  "required_skills": [str],
  "nice_to_have_skills": [str],
  "required_experience_years": int | null,
  "about_company": str,           // 2-3 sentence summary
  "role_summary": str,            // 2-3 sentence summary of the role
  "key_responsibilities": [str],
  "keywords": [str],              // top 15 ATS keywords from the JD
  "salary_range": str | null,
  "visa_sponsorship": bool | null
}

Job description:
{{ jd_text }}
"""
```

**ATS detection from URL patterns:**
```python
ATS_PATTERNS = {
    "greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "myworkdayjobs.com": "workday",
    "icims.com": "icims",
    "ashbyhq.com": "ashby",
    "smartrecruiters.com": "smartrecruiters",
    "taleo.net": "taleo",
}
```

---

## Agent 2: Narrative Aligner

**File:** `backend/agents/narrative.py`
**Model:** Sonnet
**Input:** JD parsed object + user's master resume + skill graph
**Output:** Aligned resume text

```python
SYSTEM = """
You are an expert resume writer specialising in ATS optimisation and narrative alignment.
Your goal is to reframe the user's REAL experience to best match the job description.

RULES:
- Never fabricate experience, companies, dates, or achievements
- You may reframe how existing experience is described
- You may elevate side projects from the skill graph if depth >= 3 and interview_defensible = true
- When elevating a side project, frame it as personal/side project — never as professional employment
- Use strong action verbs and quantify where the original already has numbers
- Integrate keywords from the JD naturally — never keyword-stuff
- Keep total resume length appropriate for seniority (1 page junior, 1-2 pages senior+)
"""

PROMPT_TEMPLATE = """
Job Description (parsed):
{{ jd_parsed | tojson }}

User's master resume:
{{ master_resume }}

Skill graph entries eligible for elevation (depth >= 3, interview_defensible = true):
{{ eligible_skills | tojson }}

Instructions from user:
{{ user_instructions or "None" }}

Rewrite the resume to maximise fit for this role. Return the full resume text.
At the end, append a JSON block tagged <changes> with this structure:
{
  "changes": [
    {"type": "reframed"|"elevated"|"added"|"removed", "section": str, "original": str|null, "new": str, "reason": str}
  ],
  "pct_changed": float,
  "skills_elevated": [str],
  "projects_elevated": [str],
  "jd_overlap_score": float
}
"""
```

---

## Agent 3: Authenticity Guard

**File:** `backend/agents/auth_guard.py`
**Model:** Haiku
**Input:** Original master resume + proposed tailored resume
**Output:** Validation result — pass or flag with reasons

```python
SYSTEM = """
You are an authenticity checker for job application resumes.
Detect any fabricated or significantly embellished content.
"""

PROMPT_TEMPLATE = """
Compare the original resume against the tailored version.
Flag any content in the tailored version that:
1. Claims experience at companies not in the original
2. Claims dates of employment not in the original
3. Claims achievements with numbers significantly higher than original (>50% inflation)
4. Claims skills at professional level that only appear as side projects in original
5. Removes significant gaps or career changes from the original

Return JSON:
{
  "passes": bool,
  "flags": [
    {"type": str, "original": str, "proposed": str, "severity": "block"|"warn"}
  ]
}

Original: {{ original }}
Tailored: {{ tailored }}
"""
```

---

## Agent 4: Form Fill Agent

**File:** `backend/agents/form_fill.py`
**Technology:** Playwright (Python)
**Input:** Application URL + approved resume + user profile
**Output:** Submission confirmation + screenshot

```python
# High-level flow
async def fill_form(application_id: str, apply_url: str, resume: Resume, profile: UserProfile):

    # 1. Connect to user's running Chrome
    browser = await playwright.chromium.connect_over_cdp(
        f"http://localhost:{settings.CHROME_DEBUG_PORT}"
    )
    page = await browser.new_page()

    # 2. Navigate to application URL
    await page.goto(apply_url)
    await page.wait_for_load_state("networkidle")

    # 3. Detect ATS type from DOM
    ats_type = await detect_ats(page)

    # 4. Route to ATS-specific fill strategy
    match ats_type:
        case "greenhouse":  await fill_greenhouse(page, resume, profile)
        case "lever":       await fill_lever(page, resume, profile)
        case "workday":     await fill_workday(page, resume, profile)
        case "ashby":       await fill_ashby(page, resume, profile)
        case _:             await fill_generic(page, resume, profile)

    # 5. Upload resume PDF
    await upload_resume_pdf(page, resume.pdf_url, ats_type)

    # 6. Take pre-submit screenshot
    screenshot = await page.screenshot(full_page=True)

    # 7. Submit
    await click_submit(page)

    # 8. Take post-submit screenshot
    confirmation_screenshot = await page.screenshot()

    return {
        "submitted": True,
        "screenshot_url": await store_screenshot(confirmation_screenshot, application_id)
    }
```

**Human escalation cases (don't fail silently — update status to `needs_action`):**
```python
ESCALATION_TRIGGERS = [
    "captcha detected",
    "login required",
    "SSO required",
    "assessment required",
    "cover letter manual entry required",
    "salary expectation required",        # if not in profile
    "custom essay question detected",
]
```

---

## Agent 5: Gmail Monitor

**File:** `backend/agents/gmail_monitor.py`
**Model:** Haiku
**Runs via:** Celery Beat every 5 minutes

```python
EMAIL_CLASSIFIER_SYSTEM = """
Classify this email in the context of a job application.
Return JSON only.
"""

EMAIL_CLASSIFIER_PROMPT = """
Email subject: {{ subject }}
Email from: {{ sender }}
Email body (first 500 chars): {{ body_snippet }}

Known applications (company names and roles): {{ applications_context }}

Classify and return:
{
  "classification": "confirmed"|"viewed"|"interview_invite"|"rejection"|"offer"|"unrelated",
  "company_name": str | null,
  "role_title": str | null,
  "confidence": float,
  "interview_date": str | null,     // ISO date if detectable
  "interview_type_hints": [str],    // e.g. ["technical", "with engineering manager"]
  "action_required": bool,
  "summary": str                    // one sentence
}
"""
```

**Polling logic:**
```python
@celery_app.task
def poll_gmail():
    users = get_users_with_gmail_connected()
    for user in users:
        messages = fetch_unread_application_emails(user)
        for msg in messages:
            result = classify_email(msg, user.applications)
            if result.classification != "unrelated":
                update_application_status(result, user)
                create_tracker_event(result, user)
                if result.classification == "interview_invite":
                    trigger_interview_prep.delay(result.application_id)
```

---

## Agent 6: Interview Prep Generator

**File:** `backend/agents/interview_prep.py`
**Model:** Sonnet
**Triggered by:** Gmail classification = `interview_invite`

```python
# Step 1: Detect interview type from email + calendar
# Step 2: Research the company's interview process
# Step 3: Generate personalised prep plan

RESEARCH_QUERY_TEMPLATES = [
    "{company} {role} interview process",
    "{company} engineering interview questions site:glassdoor.com",
    "{company} interview experience site:reddit.com",
    "{company} {role} interview leetcode questions",
    "{company} engineering blog",
]

PREP_PLAN_SYSTEM = """
You are an expert interview coach. Create a personalised, day-by-day interview prep plan.
Base the plan on:
1. The actual interview process at this company (from research)
2. The user's skill gaps vs what the role requires
3. The specific claims made in the user's tailored resume (they must be able to defend these)
4. The time available before the interview
"""

PREP_PLAN_PROMPT = """
Interview details:
- Company: {{ company }}
- Role: {{ role }}
- Interview type: {{ interview_type }}
- Date: {{ interview_date }}
- Days available: {{ days_available }}

Research findings:
{{ research_summary }}

User's tailored resume claims to defend:
{{ claims_to_defend | join('\n') }}

User's skill gaps for this role:
{{ gap_topics | join(', ') }}

User's STAR-eligible projects:
{{ star_projects | tojson }}

Generate a day-by-day prep plan. Return JSON:
{
  "process_summary": str,
  "question_patterns": [{topic, frequency, example_questions}],
  "prep_plan": {
    "days": [{
      "day": int,
      "focus": str,
      "tasks": [str],
      "resources": [{title, url}],
      "time_estimate_mins": int
    }]
  },
  "star_stories": [{
    "theme": str,
    "project": str,
    "situation": str,
    "task": str,
    "action": str,
    "result": str
  }],
  "gap_topics": [str],
  "strength_topics": [str]
}
"""
```

---

## Agent 7: Profile Analyser

**File:** `backend/agents/profile_analyser.py`
**Model:** Haiku (extraction) + Sonnet (STAR scaffold generation)
**Triggered by:** Onboarding, weekly refresh

```python
# GitHub analysis — use official API, no scraping
async def analyse_github(username: str) -> list[SkillSignal]:
    repos = await github_api.get_repos(username)
    for repo in repos:
        signals = {
            "ownership_score": calculate_ownership(repo),   # commits by user / total commits
            "longevity_score": (repo.last_push - repo.created_at).days,
            "articulacy_score": len(repo.readme or "") / 1000,   # normalised README length
            "recency_score": days_since(repo.last_push),
            "tech_stack": extract_languages(repo),
            "has_live_demo": bool(repo.homepage),
            "external_validation": repo.stargazers_count + repo.forks_count,
        }
        depth = calculate_depth_score(signals)    # 1-5 composite
        yield SkillSignal(repo=repo, depth=depth, signals=signals)

# Depth scoring
def calculate_depth_score(signals: dict) -> int:
    score = 0
    if signals["ownership_score"] > 0.8:      score += 2
    elif signals["ownership_score"] > 0.5:    score += 1
    if signals["longevity_score"] > 90:        score += 1
    if signals["articulacy_score"] > 0.5:     score += 1
    if signals["external_validation"] > 10:   score += 1
    return min(5, max(1, score))
```

---

## Agent 8: Deduplicator

**File:** `backend/agents/deduplicator.py`
**Model:** Haiku (only for ambiguous fingerprint matches)

```python
def normalise_url(url: str) -> str:
    """Strip tracking params, resolve redirects, return canonical URL."""
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean)

def build_fingerprint(company: str, title: str, location: str) -> str:
    """Build a stable identity hash for deduplication."""
    normalised_title = normalise_title(title)    # remove seniority, lowercase
    key = f"{company.lower()}|{normalised_title}|{location.lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

async def check_duplicate(url: str, jd_parsed: dict, user_id: str) -> DuplicateResult:
    canonical = normalise_url(url)
    fingerprint = build_fingerprint(
        jd_parsed["company_name"],
        jd_parsed["role_title"],
        jd_parsed["location"] or ""
    )

    # Check exact URL first
    exact = await db.find_application_by_url(user_id, canonical)
    if exact:
        return DuplicateResult(is_duplicate=True, application=exact, match_type="url")

    # Check fingerprint
    fp_match = await db.find_application_by_fingerprint(user_id, fingerprint)
    if fp_match:
        return DuplicateResult(is_duplicate=True, application=fp_match, match_type="fingerprint")

    return DuplicateResult(is_duplicate=False)
```

---

## Celery Task Chain — Application Pipeline

```python
# backend/tasks/application.py
from celery import chain

def start_application_pipeline(application_id: str):
    """
    Full pipeline as a Celery chain.
    Each task receives the result of the previous one.
    If any task fails, the chain stops and status is set to needs_action.
    """
    return chain(
        parse_jd.s(application_id),
        align_narrative.s(),
        run_auth_guard.s(),
        generate_resume_pdf.s(),
        # PAUSE HERE — wait for user approval via /applications/:id/approve
        # form_fill is triggered separately after approval
    ).apply_async()

@celery_app.task(bind=True, max_retries=2)
def parse_jd(self, application_id: str):
    # fetch URL, extract text, call JD parser agent
    ...

@celery_app.task(bind=True, max_retries=1)
def align_narrative(self, jd_result: dict, application_id: str):
    # call narrative aligner + auth guard
    ...

@celery_app.task(bind=True, max_retries=3)
def fill_form(self, application_id: str):
    # called after user approval
    # Playwright form fill
    ...
```

---

## Prompt templates location

```
backend/llm/prompts/
├── jd_parser.j2
├── narrative_aligner.j2
├── auth_guard.j2
├── email_classifier.j2
├── interview_type_detector.j2
├── prep_plan_generator.j2
├── star_scaffold.j2
├── concept_brief.j2           # Prepare page topic brief
└── practice_questions.j2      # Prepare page Q&A generation
```

Load with Jinja2:
```python
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("backend/llm/prompts"))

def render_prompt(template_name: str, **kwargs) -> str:
    return env.get_template(f"{template_name}.j2").render(**kwargs)
```
