-- Enable pgvector extension
create extension if not exists vector with schema extensions;

-- ══════════════════════════════════════════════════════════════
-- 1. users_profile
-- ══════════════════════════════════════════════════════════════
create table users_profile (
  id              uuid primary key references auth.users(id) on delete cascade,
  full_name       text,
  email           text,
  portfolio_url   text,
  linkedin_url    text,
  github_username text,
  target_roles    text[],
  target_locations text[],
  seniority_floor text,
  excluded_keywords text[],
  saved_addresses jsonb,
  resume_master   text,
  resume_pdf_url  text,
  gmail_connected boolean default false,
  github_connected boolean default false,
  onboarded_at    timestamptz,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ══════════════════════════════════════════════════════════════
-- 2. skill_graph
-- ══════════════════════════════════════════════════════════════
create table skill_graph (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade,
  skill_name      text not null,
  category        text,
  depth           smallint check (depth between 1 and 5),
  source          text[],
  ownership_level text,
  last_used_date  date,
  interview_defensible boolean default false,
  star_scaffold   text,
  embedding       vector(1536),
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  unique(user_id, skill_name)
);

-- ══════════════════════════════════════════════════════════════
-- 3. applications
-- ══════════════════════════════════════════════════════════════
create table applications (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid references users_profile(id) on delete cascade,
  company_name      text not null,
  role_title        text not null,
  role_title_normalised text,
  location          text,
  team              text,
  seniority         text,
  source_url        text not null,
  canonical_url     text,
  ats_type          text,
  apply_url         text,
  role_fingerprint  text,
  status            text not null default 'processing',
  jd_raw            text,
  jd_parsed         jsonb,
  instructions      text,
  referral_context  text,
  submitted_at      timestamptz,
  submission_screenshot_url text,
  form_fill_log     jsonb,
  jd_overlap_score  float,
  response_days     integer,
  is_duplicate      boolean default false,
  duplicate_of      uuid references applications(id),
  created_at        timestamptz default now(),
  updated_at        timestamptz default now()
);

create index on applications(user_id, status);
create index on applications(role_fingerprint);
create index on applications(user_id, created_at desc);

-- ══════════════════════════════════════════════════════════════
-- 4. resumes
-- ══════════════════════════════════════════════════════════════
create table resumes (
  id                uuid primary key default gen_random_uuid(),
  application_id    uuid references applications(id) on delete cascade,
  user_id           uuid references users_profile(id) on delete cascade,
  resume_text       text,
  resume_html       text,
  resume_pdf_url    text,
  cover_letter_text text,
  cover_letter_pdf_url text,
  changes_summary   jsonb,
  pct_changed       float,
  skills_elevated   text[],
  projects_elevated text[],
  status            text default 'draft',
  approved_at       timestamptz,
  trashed_at        timestamptz,
  resulted_in_interview boolean default false,
  interview_invite_days integer,
  created_at        timestamptz default now()
);

-- ══════════════════════════════════════════════════════════════
-- 5. tracker_events
-- ══════════════════════════════════════════════════════════════
create table tracker_events (
  id              uuid primary key default gen_random_uuid(),
  application_id  uuid references applications(id) on delete cascade,
  user_id         uuid references users_profile(id) on delete cascade,
  event_type      text not null,
  source          text,
  email_subject   text,
  email_snippet   text,
  metadata        jsonb,
  created_at      timestamptz default now()
);

create index on tracker_events(application_id, created_at desc);

-- ══════════════════════════════════════════════════════════════
-- 6. interview_prep
-- ══════════════════════════════════════════════════════════════
create table interview_prep (
  id                  uuid primary key default gen_random_uuid(),
  application_id      uuid references applications(id) on delete cascade,
  user_id             uuid references users_profile(id) on delete cascade,
  interview_type      text[],
  interview_date      timestamptz,
  detected_from       text,
  confidence          float,
  research_sources    jsonb,
  question_patterns   jsonb,
  process_summary     text,
  prep_plan           jsonb,
  star_stories        jsonb,
  gap_topics          text[],
  strength_topics     text[],
  resume_id           uuid references resumes(id),
  claims_to_defend    text[],
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

-- ══════════════════════════════════════════════════════════════
-- 7. prep_sessions
-- ══════════════════════════════════════════════════════════════
create table prep_sessions (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade,
  session_date    date not null,
  topic           text not null,
  category        text not null,
  depth_before    smallint,
  depth_after     smallint,
  created_at      timestamptz default now(),
  unique(user_id, session_date, topic)
);

-- ══════════════════════════════════════════════════════════════
-- 8. prep_items
-- ══════════════════════════════════════════════════════════════
create table prep_items (
  id              uuid primary key default gen_random_uuid(),
  session_id      uuid references prep_sessions(id) on delete cascade,
  user_id         uuid references users_profile(id) on delete cascade,
  question        text not null,
  model_answer    text,
  self_rating     text,
  next_review     date,
  review_count    integer default 0,
  created_at      timestamptz default now()
);

create index on prep_items(user_id, next_review);

-- ══════════════════════════════════════════════════════════════
-- 9. outreach
-- ══════════════════════════════════════════════════════════════
create table outreach (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade,
  application_id  uuid references applications(id),
  recipient_email text not null,
  recipient_name  text,
  recipient_role  text,
  company         text,
  linkedin_url    text,
  subject         text,
  body            text,
  scenario        text,
  status          text default 'draft',
  sent_at         timestamptz,
  replied_at      timestamptz,
  locked_until    timestamptz,
  created_at      timestamptz default now()
);

-- ══════════════════════════════════════════════════════════════
-- RLS Policies — users can only see their own data
-- ══════════════════════════════════════════════════════════════

alter table users_profile enable row level security;
create policy "Users see own profile" on users_profile for all using (auth.uid() = id);

alter table skill_graph enable row level security;
create policy "Users see own skills" on skill_graph for all using (auth.uid() = user_id);

alter table applications enable row level security;
create policy "Users see own applications" on applications for all using (auth.uid() = user_id);

alter table resumes enable row level security;
create policy "Users see own resumes" on resumes for all using (auth.uid() = user_id);

alter table tracker_events enable row level security;
create policy "Users see own events" on tracker_events for all using (auth.uid() = user_id);

alter table interview_prep enable row level security;
create policy "Users see own prep" on interview_prep for all using (auth.uid() = user_id);

alter table prep_sessions enable row level security;
create policy "Users see own sessions" on prep_sessions for all using (auth.uid() = user_id);

alter table prep_items enable row level security;
create policy "Users see own items" on prep_items for all using (auth.uid() = user_id);

alter table outreach enable row level security;
create policy "Users see own outreach" on outreach for all using (auth.uid() = user_id);

-- ══════════════════════════════════════════════════════════════
-- Enable Realtime on tracker_events
-- ══════════════════════════════════════════════════════════════
alter publication supabase_realtime add table tracker_events;

-- ══════════════════════════════════════════════════════════════
-- Storage bucket for resumes
-- ══════════════════════════════════════════════════════════════
insert into storage.buckets (id, name, public) values ('resumes', 'resumes', false);

-- Storage policy: users can read/write their own folder
create policy "Users manage own resumes" on storage.objects for all
  using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
