# Database Schema — Supabase (Postgres)

All tables use `uuid` primary keys with `gen_random_uuid()` defaults.
`user_id` on every table references `auth.users(id)` — Supabase handles this automatically.
Enable `pgvector` extension in Supabase dashboard before running migrations.

---

## Migration order

Run in this order to satisfy foreign key constraints:

1. `users_profile`
2. `skill_graph`
3. `applications`
4. `resumes`
5. `tracker_events`
6. `prep_sessions`
7. `prep_items`
8. `outreach`

---

## Tables

### `users_profile`

Extends Supabase auth.users with application-specific preferences.

```sql
create table users_profile (
  id              uuid primary key references auth.users(id) on delete cascade,
  full_name       text,
  email           text,
  portfolio_url   text,
  linkedin_url    text,
  github_username text,
  target_roles    text[],          -- e.g. ['Senior Backend Engineer', 'Staff Engineer']
  target_locations text[],         -- e.g. ['Remote', 'London', 'Berlin']
  seniority_floor text,            -- 'senior' | 'staff' | 'principal' | 'any'
  excluded_keywords text[],        -- e.g. ['frontend', 'mobile', 'data science']
  saved_addresses jsonb,           -- [{label: 'Home', ...address fields}]
  resume_master   text,            -- raw text of master resume
  resume_pdf_url  text,            -- Supabase storage URL
  gmail_connected boolean default false,
  github_connected boolean default false,
  onboarded_at    timestamptz,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
```

---

### `skill_graph`

One row per skill per user. Updated by profile analysis and Prepare page self-ratings.

```sql
create table skill_graph (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade,
  skill_name      text not null,
  category        text,            -- 'cs_fundamentals' | 'system_design' | 'stack' | 'behavioural'
  depth           smallint check (depth between 1 and 5),
  source          text[],          -- ['github', 'linkedin', 'portfolio', 'resume', 'prepare_page']
  ownership_level text,            -- 'author' | 'contributor' | 'user'
  last_used_date  date,
  interview_defensible boolean default false,
  star_scaffold   text,            -- auto-drafted STAR story
  embedding       vector(1536),    -- for semantic role matching
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  unique(user_id, skill_name)
);

create index on skill_graph using ivfflat (embedding vector_cosine_ops);
```

---

### `applications`

One row per job application. The central entity everything else links to.

```sql
create table applications (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid references users_profile(id) on delete cascade,

  -- role identity
  company_name      text not null,
  role_title        text not null,
  role_title_normalised text,      -- lowercased, for matching
  location          text,
  team              text,
  seniority         text,

  -- urls
  source_url        text not null, -- original URL pasted by user
  canonical_url     text,          -- normalised, tracking params stripped
  ats_type          text,          -- 'greenhouse' | 'lever' | 'workday' | 'ashby' | 'icims' | 'other'
  apply_url         text,          -- direct ATS application URL if different

  -- fingerprint for dedup
  role_fingerprint  text,          -- hash of company+title_normalised+location

  -- status
  status            text not null default 'processing',
  -- 'processing' | 'applied' | 'viewed' | 'screening' |
  -- 'interview' | 'offer' | 'rejected' | 'needs_action' | 'withdrawn'

  -- content
  jd_raw            text,          -- raw job description text
  jd_parsed         jsonb,         -- structured: {skills, requirements, nice_to_have, about_company}
  instructions      text,          -- user's optional instructions
  referral_context  text,          -- if came via network post

  -- submission
  submitted_at      timestamptz,
  submission_screenshot_url text,
  form_fill_log     jsonb,         -- {fields_filled, fields_skipped, errors}

  -- jd overlap score at submission
  jd_overlap_score  float,         -- 0.0 to 1.0

  -- response timing
  response_days     integer,       -- days from submitted_at to first response

  -- flags
  is_duplicate      boolean default false,
  duplicate_of      uuid references applications(id),

  created_at        timestamptz default now(),
  updated_at        timestamptz default now()
);

create index on applications(user_id, status);
create index on applications(role_fingerprint);
create index on applications(user_id, created_at desc);
```

---

### `resumes`

Tailored resume per application. Stored only for applications that received an interview or are active.
Rejected with no interview → deleted, metadata kept in `applications`.

```sql
create table resumes (
  id                uuid primary key default gen_random_uuid(),
  application_id    uuid references applications(id) on delete cascade,
  user_id           uuid references users_profile(id) on delete cascade,

  -- content
  resume_text       text,          -- plain text version
  resume_html       text,          -- HTML for WeasyPrint
  resume_pdf_url    text,          -- Supabase storage URL
  cover_letter_text text,
  cover_letter_pdf_url text,

  -- diff from master
  changes_summary   jsonb,         -- [{type: 'added'|'reframed'|'elevated', field, original, new}]
  pct_changed       float,         -- % of content changed from master resume

  -- skills surfaced from skill graph (not in master resume)
  skills_elevated   text[],        -- skill names pulled from side projects
  projects_elevated text[],        -- project names used professionally

  -- state
  status            text default 'draft',
  -- 'draft' | 'approved' | 'submitted' | 'active' (interview in progress) | 'archived' | 'trashed'

  approved_at       timestamptz,
  trashed_at        timestamptz,

  -- learning signal
  resulted_in_interview boolean default false,
  interview_invite_days integer,   -- days from submit to invite

  created_at        timestamptz default now()
);
```

---

### `tracker_events`

Append-only log of all status changes. Drives the timeline view in the tracker UI.

```sql
create table tracker_events (
  id              uuid primary key default gen_random_uuid(),
  application_id  uuid references applications(id) on delete cascade,
  user_id         uuid references users_profile(id) on delete cascade,

  event_type      text not null,
  -- 'applied' | 'email_confirmed' | 'email_viewed' | 'email_interview_invite'
  -- 'email_rejection' | 'email_offer' | 'status_changed' | 'prep_plan_generated'
  -- 'needs_action' | 'user_actioned' | 'auto_expired'

  source          text,            -- 'gmail' | 'user' | 'agent' | 'system'
  email_subject   text,            -- if triggered by email
  email_snippet   text,            -- first 200 chars of email body
  metadata        jsonb,           -- event-specific data
  created_at      timestamptz default now()
);

create index on tracker_events(application_id, created_at desc);
```

---

### `interview_prep`

One row per application that reached interview stage.

```sql
create table interview_prep (
  id                  uuid primary key default gen_random_uuid(),
  application_id      uuid references applications(id) on delete cascade,
  user_id             uuid references users_profile(id) on delete cascade,

  -- detection
  interview_type      text[],      -- ['coding', 'system_design', 'behavioural', 'panel']
  interview_date      timestamptz,
  detected_from       text,        -- 'email' | 'calendar_invite' | 'manual'
  confidence          float,       -- how confident the type detection was

  -- research
  research_sources    jsonb,       -- [{source: 'glassdoor', url, summary}]
  question_patterns   jsonb,       -- [{topic, frequency, example_questions[]}]
  process_summary     text,        -- what the interview process looks like at this company

  -- plan
  prep_plan           jsonb,       -- {days: [{day, focus, tasks[], resources[]}]}
  star_stories        jsonb,       -- [{theme, project, situation, task, action, result}]
  gap_topics          text[],      -- topics in interview reports not in user skill graph
  strength_topics     text[],      -- topics to highlight, user has depth >= 3

  -- resume reference
  resume_id           uuid references resumes(id),
  claims_to_defend    text[],      -- bullets from tailored resume to prep answers for

  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);
```

---

### `prep_sessions`

Daily Prepare page sessions. One row per day per user.

```sql
create table prep_sessions (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade,
  session_date    date not null,
  topic           text not null,
  category        text not null,   -- 'cs_fundamentals' | 'system_design' | 'stack' | 'behavioural'
  depth_before    smallint,        -- skill depth at session start
  depth_after     smallint,        -- skill depth after self-rating
  created_at      timestamptz default now(),
  unique(user_id, session_date, topic)
);
```

---

### `prep_items`

Individual Q&A items within a prep session.

```sql
create table prep_items (
  id              uuid primary key default gen_random_uuid(),
  session_id      uuid references prep_sessions(id) on delete cascade,
  user_id         uuid references users_profile(id) on delete cascade,
  question        text not null,
  model_answer    text,            -- Claude-generated reference answer
  self_rating     text,            -- 'got_it' | 'unsure' | 'missed'
  next_review     date,            -- spaced repetition next date
  review_count    integer default 0,
  created_at      timestamptz default now()
);

create index on prep_items(user_id, next_review);
```

---

### `outreach`

Tracks all outreach emails sent (network agent path).

```sql
create table outreach (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade,
  application_id  uuid references applications(id), -- null if no application yet

  recipient_email text not null,
  recipient_name  text,
  recipient_role  text,
  company         text,
  linkedin_url    text,

  subject         text,
  body            text,
  scenario        text,            -- 'A' | 'B' | 'C' (dual signal scenarios)

  status          text default 'draft',
  -- 'draft' | 'approved' | 'sent' | 'replied' | 'declined' | 'cold'

  sent_at         timestamptz,
  replied_at      timestamptz,
  locked_until    timestamptz,     -- 30-day no-repeat lock

  created_at      timestamptz default now()
);
```

---

## Row Level Security (RLS)

Enable on all tables. Users can only see their own data.

```sql
-- Example for applications (repeat pattern for all tables)
alter table applications enable row level security;

create policy "Users see own applications"
  on applications for all
  using (auth.uid() = user_id);
```

---

## Spaced repetition interval logic

```
self_rating = 'got_it'  → next_review = today + 7 days  (then 14, 30)
self_rating = 'unsure'  → next_review = today + 2 days  (then 5, 10)
self_rating = 'missed'  → next_review = today + 1 day   (then 3, 7)
```

Implemented in the `prep_items` insert/update handler.

---

## Useful queries

```sql
-- All active applications for a user
select * from applications
where user_id = $1
  and status not in ('rejected', 'withdrawn')
order by created_at desc;

-- Resumes to keep (interview or active)
select * from resumes
where user_id = $1
  and status in ('active', 'archived');

-- Today's prep items due for review
select * from prep_items
where user_id = $1
  and next_review <= current_date
order by next_review asc
limit 5;

-- Skill graph gap vs target role embedding
select skill_name, depth, 1 - (embedding <=> $role_embedding) as similarity
from skill_graph
where user_id = $1
  and depth < 3
order by similarity desc
limit 10;
```
