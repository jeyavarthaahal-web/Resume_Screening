-- Task 5: persist extracted job description intelligence without changing Task 3 history.
alter table public.jobs
  add column if not exists cleaned_description text,
  add column if not exists summary text,
  add column if not exists responsibilities jsonb not null default '[]'::jsonb check (jsonb_typeof(responsibilities) = 'array'),
  add column if not exists education_json jsonb check (education_json is null or jsonb_typeof(education_json) = 'object'),
  add column if not exists certifications_json jsonb not null default '[]'::jsonb check (jsonb_typeof(certifications_json) = 'array'),
  add column if not exists benefits_json jsonb not null default '[]'::jsonb check (jsonb_typeof(benefits_json) = 'array'),
  add column if not exists work_mode text check (work_mode is null or work_mode in ('Remote', 'Hybrid', 'On-site')),
  add column if not exists analysis_status text not null default 'pending' check (analysis_status in ('pending', 'analyzed', 'failed'));

-- Job ownership and published-job visibility continue to be enforced by Task 3 RLS.
