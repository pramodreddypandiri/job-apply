-- ══════════════════════════════════════════════════════════════
-- master_resume — structured, editable resume (one per user)
-- ══════════════════════════════════════════════════════════════
create table master_resume (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references users_profile(id) on delete cascade unique,
  personal_details jsonb default '{}'::jsonb,
  -- { full_name, email, phone, location, linkedin_url, github_url, portfolio_url }
  summary         text default '',
  experience      jsonb default '[]'::jsonb,
  -- [{ company, role, location, start_date, end_date, current, bullets: [] }]
  education       jsonb default '[]'::jsonb,
  -- [{ institution, degree, field, start_date, end_date, gpa, highlights: [] }]
  projects        jsonb default '[]'::jsonb,
  -- [{ name, description, tech_stack: [], url, bullets: [] }]
  skills          jsonb default '[]'::jsonb,
  -- [{ category, items: [] }]
  certifications  jsonb default '[]'::jsonb,
  -- [{ name, issuer, date, url }]
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- RLS
alter table master_resume enable row level security;
create policy "Users see own resume" on master_resume for all using (auth.uid() = user_id);
