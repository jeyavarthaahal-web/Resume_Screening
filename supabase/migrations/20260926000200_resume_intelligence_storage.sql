-- Task 4 storage support. Use a private bucket and the caller's JWT so Storage and
-- Postgres continue to enforce the Task 3 ownership policies.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'talentiq-resumes',
  'talentiq-resumes',
  false,
  10485760,
  array['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']::text[]
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create policy "Candidates upload own TalentIQ resumes"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'talentiq-resumes'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and (select public.current_account_type()) = 'job_seeker'
);

create policy "Candidates read own TalentIQ resumes"
on storage.objects for select to authenticated
using (
  bucket_id = 'talentiq-resumes'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and (select public.current_account_type()) = 'job_seeker'
);

create policy "Candidates delete own TalentIQ resumes"
on storage.objects for delete to authenticated
using (
  bucket_id = 'talentiq-resumes'
  and (storage.foldername(name))[1] = (select auth.uid())::text
  and (select public.current_account_type()) = 'job_seeker'
);

-- The frontend groups skill values for display while keeping the Task 3 column.
alter table public.resume_profiles
  drop constraint if exists resume_profiles_skills_json_check;
alter table public.resume_profiles
  add constraint resume_profiles_skills_json_check
  check (jsonb_typeof(skills_json) in ('array', 'object'));
alter table public.resume_profiles
  add column if not exists achievements_json jsonb not null default '[]'::jsonb
  check (jsonb_typeof(achievements_json) = 'array');

grant insert on public.resume_profiles to authenticated;
create policy resume_profiles_insert_self on public.resume_profiles for insert to authenticated
with check (
  candidate_id = (select auth.uid())
  and exists (
    select 1 from public.resumes r
    where r.id = resume_id and r.candidate_id = (select auth.uid())
  )
);
