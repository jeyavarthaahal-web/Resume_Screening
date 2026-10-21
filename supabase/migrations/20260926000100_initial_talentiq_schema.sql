-- TalentIQ Task 3: database foundation only. No parsing or scoring logic.
create type public.account_type as enum ('job_seeker', 'recruiter');
create type public.job_status as enum ('draft', 'published', 'closed');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  email text,
  account_type public.account_type not null,
  -- Internal one-time lock supports Task 2 OAuth metadata arriving after auth.users INSERT.
  account_type_locked boolean not null default true,
  company_name text,
  company_size text check (company_size is null or company_size in ('1-10', '11-50', '51-200', '201-500', '501-1000', '1000+')),
  avatar_url text,
  phone text,
  location text,
  bio text,
  terms_accepted boolean not null default false,
  gdpr_consent boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index profiles_email_idx on public.profiles (lower(email)) where email is not null;
create index profiles_account_type_idx on public.profiles (account_type);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  recruiter_id uuid not null references public.profiles(id) on delete cascade,
  title text not null check (length(btrim(title)) between 1 and 200),
  department text,
  description text not null default '',
  location text,
  employment_type text check (employment_type is null or employment_type in ('full_time', 'part_time', 'contract', 'temporary', 'internship', 'other')),
  experience_min numeric(5,2) check (experience_min is null or experience_min >= 0),
  experience_max numeric(5,2) check (experience_max is null or experience_max >= 0),
  education_requirement text,
  status public.job_status not null default 'draft',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (experience_min is null or experience_max is null or experience_min <= experience_max)
);
create index jobs_recruiter_id_idx on public.jobs (recruiter_id);
create index jobs_status_idx on public.jobs (status);
create index jobs_created_at_idx on public.jobs (created_at desc);

create table public.job_requirements (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  skill_name text not null check (length(btrim(skill_name)) between 1 and 160),
  skill_type text not null default 'required' check (skill_type in ('required', 'preferred', 'nice_to_have')),
  importance smallint not null default 3 check (importance between 1 and 5),
  created_at timestamptz not null default now(),
  unique (job_id, skill_name)
);
create index job_requirements_job_id_idx on public.job_requirements (job_id);

create table public.resumes (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  file_name text not null check (length(btrim(file_name)) between 1 and 512),
  file_path text not null,
  file_type text,
  file_size bigint check (file_size is null or file_size > 0),
  raw_text text,
  status text not null default 'uploaded' check (status in ('uploaded', 'queued', 'processing', 'processed', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, candidate_id)
);
create index resumes_candidate_id_idx on public.resumes (candidate_id);
create index resumes_created_at_idx on public.resumes (created_at desc);

create table public.resume_profiles (
  id uuid primary key default gen_random_uuid(),
  resume_id uuid not null unique,
  candidate_id uuid not null,
  full_name text,
  email text,
  phone text,
  location text,
  summary text,
  years_experience numeric(5,2) check (years_experience is null or years_experience >= 0),
  education_json jsonb not null default '[]'::jsonb check (jsonb_typeof(education_json) = 'array'),
  experience_json jsonb not null default '[]'::jsonb check (jsonb_typeof(experience_json) = 'array'),
  skills_json jsonb not null default '{}'::jsonb check (jsonb_typeof(skills_json) in ('array', 'object')),
  certifications_json jsonb not null default '[]'::jsonb check (jsonb_typeof(certifications_json) = 'array'),
  projects_json jsonb not null default '[]'::jsonb check (jsonb_typeof(projects_json) = 'array'),
  languages_json jsonb not null default '[]'::jsonb check (jsonb_typeof(languages_json) = 'array'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (resume_id, candidate_id) references public.resumes(id, candidate_id) on delete cascade
);
create index resume_profiles_candidate_id_idx on public.resume_profiles (candidate_id);

create table public.screening_results (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  resume_id uuid not null references public.resumes(id) on delete cascade,
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  overall_score numeric(5,2) check (overall_score is null or overall_score between 0 and 100),
  semantic_score numeric(5,2) check (semantic_score is null or semantic_score between 0 and 100),
  skills_score numeric(5,2) check (skills_score is null or skills_score between 0 and 100),
  experience_score numeric(5,2) check (experience_score is null or experience_score between 0 and 100),
  education_score numeric(5,2) check (education_score is null or education_score between 0 and 100),
  projects_score numeric(5,2) check (projects_score is null or projects_score between 0 and 100),
  matched_skills text[] not null default '{}',
  partial_skills text[] not null default '{}',
  missing_skills text[] not null default '{}',
  strengths jsonb not null default '[]'::jsonb check (jsonb_typeof(strengths) = 'array'),
  gaps jsonb not null default '[]'::jsonb check (jsonb_typeof(gaps) = 'array'),
  evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence) = 'array'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (resume_id, candidate_id) references public.resumes(id, candidate_id) on delete cascade
);
create index screening_results_job_id_idx on public.screening_results (job_id);
create index screening_results_candidate_id_idx on public.screening_results (candidate_id);
create index screening_results_resume_id_idx on public.screening_results (resume_id);
create index screening_results_overall_score_idx on public.screening_results (overall_score desc) where overall_score is not null;

create table public.shortlists (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  recruiter_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'shortlisted' check (status in ('new', 'reviewing', 'shortlisted', 'rejected', 'hired')),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (job_id, candidate_id, recruiter_id)
);
create index shortlists_job_id_idx on public.shortlists (job_id);
create index shortlists_candidate_id_idx on public.shortlists (candidate_id);
create index shortlists_recruiter_id_idx on public.shortlists (recruiter_id);

create table public.candidate_notes (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  recruiter_id uuid not null references public.profiles(id) on delete cascade,
  note text not null check (length(btrim(note)) > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index candidate_notes_job_id_idx on public.candidate_notes (job_id);
create index candidate_notes_candidate_id_idx on public.candidate_notes (candidate_id);
create index candidate_notes_recruiter_id_idx on public.candidate_notes (recruiter_id);

create table public.candidate_comparisons (
  id uuid primary key default gen_random_uuid(),
  recruiter_id uuid not null references public.profiles(id) on delete cascade,
  job_id uuid not null references public.jobs(id) on delete cascade,
  candidate_ids uuid[] not null check (cardinality(candidate_ids) > 0),
  created_at timestamptz not null default now()
);
create index candidate_comparisons_recruiter_job_idx on public.candidate_comparisons (recruiter_id, job_id);
create index candidate_comparisons_candidate_ids_idx on public.candidate_comparisons using gin (candidate_ids);

create table public.career_assistant_sessions (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  title text check (title is null or length(title) <= 200),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index career_assistant_sessions_candidate_id_idx on public.career_assistant_sessions (candidate_id);

create table public.career_assistant_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.career_assistant_sessions(id) on delete cascade,
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null check (length(btrim(content)) > 0),
  created_at timestamptz not null default now()
);
create index career_assistant_messages_session_id_idx on public.career_assistant_messages (session_id, created_at);

create table public.ai_analysis_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  entity_type text not null check (length(btrim(entity_type)) between 1 and 80),
  entity_id uuid,
  analysis_type text not null check (length(btrim(analysis_type)) between 1 and 120),
  model_name text,
  input_metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(input_metadata) = 'object'),
  output_metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(output_metadata) = 'object'),
  created_at timestamptz not null default now()
);
create index ai_analysis_logs_user_id_idx on public.ai_analysis_logs (user_id);

-- Trigger functions use an empty search_path and fully qualified object names.
create function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();
create trigger jobs_set_updated_at before update on public.jobs
for each row execute function public.set_updated_at();
create trigger resumes_set_updated_at before update on public.resumes
for each row execute function public.set_updated_at();
create trigger resume_profiles_set_updated_at before update on public.resume_profiles
for each row execute function public.set_updated_at();
create trigger screening_results_set_updated_at before update on public.screening_results
for each row execute function public.set_updated_at();
create trigger shortlists_set_updated_at before update on public.shortlists
for each row execute function public.set_updated_at();
create trigger candidate_notes_set_updated_at before update on public.candidate_notes
for each row execute function public.set_updated_at();
create trigger career_assistant_sessions_set_updated_at before update on public.career_assistant_sessions
for each row execute function public.set_updated_at();

create function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  requested_type text := lower(btrim(coalesce(new.raw_user_meta_data ->> 'account_type', '')));
  valid_type boolean;
begin
  valid_type := requested_type in ('job_seeker', 'recruiter');
  insert into public.profiles (
    id, full_name, email, account_type, account_type_locked,
    company_name, company_size, terms_accepted, gdpr_consent
  ) values (
    new.id,
    coalesce(nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''), ''),
    new.email,
    case when valid_type then requested_type::public.account_type else 'job_seeker'::public.account_type end,
    valid_type,
    case when requested_type = 'recruiter' then nullif(btrim(new.raw_user_meta_data ->> 'company_name'), '') else null end,
    case when requested_type = 'recruiter' and new.raw_user_meta_data ->> 'company_size' in ('1-10', '11-50', '51-200', '201-500', '501-1000', '1000+') then new.raw_user_meta_data ->> 'company_size' else null end,
    lower(coalesce(new.raw_user_meta_data ->> 'terms_accepted', 'false')) = 'true',
    lower(coalesce(new.raw_user_meta_data ->> 'gdpr_consent', 'false')) = 'true'
  ) on conflict (id) do nothing;
  return new;
end;
$$;
revoke all on function public.handle_new_auth_user() from public, anon, authenticated;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_auth_user();

-- Backfill Task 2 accounts that existed before this migration was applied.
insert into public.profiles (
  id, full_name, email, account_type, account_type_locked,
  company_name, company_size, terms_accepted, gdpr_consent
)
select
  u.id,
  coalesce(nullif(btrim(u.raw_user_meta_data ->> 'full_name'), ''), ''),
  u.email,
  case when lower(btrim(coalesce(u.raw_user_meta_data ->> 'account_type', ''))) in ('job_seeker', 'recruiter')
    then lower(btrim(u.raw_user_meta_data ->> 'account_type'))::public.account_type
    else 'job_seeker'::public.account_type end,
  lower(btrim(coalesce(u.raw_user_meta_data ->> 'account_type', ''))) in ('job_seeker', 'recruiter'),
  case when lower(btrim(coalesce(u.raw_user_meta_data ->> 'account_type', ''))) = 'recruiter' then nullif(btrim(u.raw_user_meta_data ->> 'company_name'), '') else null end,
  case when lower(btrim(coalesce(u.raw_user_meta_data ->> 'account_type', ''))) = 'recruiter' and u.raw_user_meta_data ->> 'company_size' in ('1-10', '11-50', '51-200', '201-500', '501-1000', '1000+') then u.raw_user_meta_data ->> 'company_size' else null end,
  lower(coalesce(u.raw_user_meta_data ->> 'terms_accepted', 'false')) = 'true',
  lower(coalesce(u.raw_user_meta_data ->> 'gdpr_consent', 'false')) = 'true'
from auth.users u
on conflict (id) do nothing;

-- Task 2 OAuth stores signup metadata after the provider inserts auth.users. Apply
-- that first valid role only when the insert had no valid role; later edits cannot change it.
create function public.sync_pending_auth_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  requested_type text := lower(btrim(coalesce(new.raw_user_meta_data ->> 'account_type', '')));
begin
  if requested_type in ('job_seeker', 'recruiter') then
    update public.profiles p
    set account_type = requested_type::public.account_type,
        account_type_locked = true,
        full_name = coalesce(nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''), p.full_name),
        email = new.email,
        company_name = case when requested_type = 'recruiter' then nullif(btrim(new.raw_user_meta_data ->> 'company_name'), '') else null end,
        company_size = case when requested_type = 'recruiter' and new.raw_user_meta_data ->> 'company_size' in ('1-10', '11-50', '51-200', '201-500', '501-1000', '1000+') then new.raw_user_meta_data ->> 'company_size' else null end,
        terms_accepted = lower(coalesce(new.raw_user_meta_data ->> 'terms_accepted', 'false')) = 'true',
        gdpr_consent = lower(coalesce(new.raw_user_meta_data ->> 'gdpr_consent', 'false')) = 'true'
    where p.id = new.id and p.account_type_locked = false;
  elsif new.email is distinct from old.email then
    update public.profiles set email = new.email where id = new.id;
  end if;
  return new;
end;
$$;
revoke all on function public.sync_pending_auth_profile() from public, anon, authenticated;
create trigger on_auth_user_updated after update of raw_user_meta_data, email on auth.users
for each row execute function public.sync_pending_auth_profile();

-- RLS policies use the database profile role (not editable user_metadata).
create function public.current_account_type()
returns public.account_type
language sql
stable
security definer
set search_path = ''
as $$
  select p.account_type from public.profiles p where p.id = (select auth.uid())
$$;
revoke all on function public.current_account_type() from public, anon;
grant execute on function public.current_account_type() to authenticated;

alter table public.profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.job_requirements enable row level security;
alter table public.resumes enable row level security;
alter table public.resume_profiles enable row level security;
alter table public.screening_results enable row level security;
alter table public.shortlists enable row level security;
alter table public.candidate_notes enable row level security;
alter table public.candidate_comparisons enable row level security;
alter table public.career_assistant_sessions enable row level security;
alter table public.career_assistant_messages enable row level security;
alter table public.ai_analysis_logs enable row level security;

-- Explicit grants keep identity/role columns outside client updates. Policies still
-- constrain every granted operation to the authenticated owner/related recruiter.
revoke all on public.profiles, public.jobs, public.job_requirements, public.resumes,
  public.resume_profiles, public.screening_results, public.shortlists, public.candidate_notes,
  public.candidate_comparisons, public.career_assistant_sessions,
  public.career_assistant_messages, public.ai_analysis_logs from anon, authenticated;

grant select (id, full_name, email, account_type, company_name, company_size, avatar_url, phone, location, bio, terms_accepted, gdpr_consent, created_at, updated_at) on public.profiles to authenticated;
grant update (full_name, company_name, company_size, avatar_url, phone, location, bio, terms_accepted, gdpr_consent) on public.profiles to authenticated;

grant select on public.jobs to anon, authenticated;
grant insert, update, delete on public.jobs to authenticated;
grant select on public.job_requirements to anon, authenticated;
grant insert, update, delete on public.job_requirements to authenticated;
grant select, insert, update, delete on public.resumes to authenticated;
grant select on public.resume_profiles, public.screening_results to authenticated;
grant select, insert, update, delete on public.shortlists, public.candidate_notes, public.candidate_comparisons to authenticated;
grant select, insert, update, delete on public.career_assistant_sessions to authenticated;
grant select, insert on public.career_assistant_messages to authenticated;
grant select on public.ai_analysis_logs to authenticated;

create policy profiles_read_self on public.profiles for select to authenticated
  using (id = (select auth.uid()));
create policy profiles_update_self on public.profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy jobs_read_published_or_owned on public.jobs for select to anon, authenticated
  using (status = 'published' or recruiter_id = (select auth.uid()));
create policy jobs_insert_recruiter_own on public.jobs for insert to authenticated
  with check (recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter');
create policy jobs_update_recruiter_own on public.jobs for update to authenticated
  using (recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter')
  with check (recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter');
create policy jobs_delete_recruiter_own on public.jobs for delete to authenticated
  using (recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter');

create policy job_requirements_read_visible_job on public.job_requirements for select to anon, authenticated
  using (exists (select 1 from public.jobs j where j.id = job_id and (j.status = 'published' or j.recruiter_id = (select auth.uid()))));
create policy job_requirements_insert_owned_job on public.job_requirements for insert to authenticated
  with check (exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter'));
create policy job_requirements_update_owned_job on public.job_requirements for update to authenticated
  using (exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter'))
  with check (exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter'));
create policy job_requirements_delete_owned_job on public.job_requirements for delete to authenticated
  using (exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter'));

create policy resumes_manage_self on public.resumes for all to authenticated
  using (candidate_id = (select auth.uid())) with check (candidate_id = (select auth.uid()) and (select public.current_account_type()) = 'job_seeker');
create policy resume_profiles_read_self on public.resume_profiles for select to authenticated
  using (candidate_id = (select auth.uid()) and exists (select 1 from public.resumes r where r.id = resume_id and r.candidate_id = (select auth.uid())));

create policy screening_results_read_candidate_or_job_recruiter on public.screening_results for select to authenticated
  using (
    candidate_id = (select auth.uid())
    or exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter')
  );

create policy shortlists_manage_recruiter_job on public.shortlists for all to authenticated
  using (recruiter_id = (select auth.uid()) and exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid())) and (select public.current_account_type()) = 'recruiter')
  with check (recruiter_id = (select auth.uid()) and exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid())) and (select public.current_account_type()) = 'recruiter');
create policy candidate_notes_manage_recruiter_job on public.candidate_notes for all to authenticated
  using (recruiter_id = (select auth.uid()) and exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid())) and (select public.current_account_type()) = 'recruiter')
  with check (recruiter_id = (select auth.uid()) and exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid())) and (select public.current_account_type()) = 'recruiter');
create policy candidate_comparisons_manage_self on public.candidate_comparisons for all to authenticated
  using (recruiter_id = (select auth.uid()) and exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid())) and (select public.current_account_type()) = 'recruiter')
  with check (recruiter_id = (select auth.uid()) and exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid())) and (select public.current_account_type()) = 'recruiter');

create policy career_sessions_manage_self on public.career_assistant_sessions for all to authenticated
  using (candidate_id = (select auth.uid())) with check (candidate_id = (select auth.uid()) and (select public.current_account_type()) = 'job_seeker');
create policy career_messages_read_self_parent on public.career_assistant_messages for select to authenticated
  using (candidate_id = (select auth.uid()) and exists (select 1 from public.career_assistant_sessions s where s.id = session_id and s.candidate_id = (select auth.uid())));
create policy career_messages_insert_user_self_parent on public.career_assistant_messages for insert to authenticated
  with check (role = 'user' and candidate_id = (select auth.uid()) and exists (select 1 from public.career_assistant_sessions s where s.id = session_id and s.candidate_id = (select auth.uid())));

create policy ai_analysis_logs_read_self on public.ai_analysis_logs for select to authenticated
  using (user_id = (select auth.uid()));
