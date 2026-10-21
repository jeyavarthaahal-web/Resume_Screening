-- Task 6: application consent is the authorization link between a job and resume.
create table public.job_candidates (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs(id) on delete cascade,
  candidate_id uuid not null references public.profiles(id) on delete cascade,
  resume_id uuid not null,
  created_at timestamptz not null default now(),
  unique (job_id, candidate_id),
  unique (job_id, resume_id),
  foreign key (resume_id, candidate_id) references public.resumes(id, candidate_id) on delete cascade
);
create index job_candidates_candidate_idx on public.job_candidates(candidate_id, created_at desc);
create index job_candidates_resume_idx on public.job_candidates(resume_id);

alter table public.job_candidates enable row level security;
revoke all on public.job_candidates from anon, authenticated;
grant select, insert, delete on public.job_candidates to authenticated;

-- A candidate creates this row only for their own processed resume and a published job.
create policy job_candidates_read_candidate_or_recruiter on public.job_candidates for select to authenticated
  using (
    candidate_id = (select auth.uid())
    or exists (select 1 from public.jobs j where j.id = job_id and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter')
  );
create policy job_candidates_apply_self_to_published_job on public.job_candidates for insert to authenticated
  with check (
    candidate_id = (select auth.uid())
    and (select public.current_account_type()) = 'job_seeker'
    and exists (select 1 from public.jobs j where j.id = job_id and j.status = 'published')
    and exists (select 1 from public.resumes r where r.id = resume_id and r.candidate_id = (select auth.uid()) and r.status = 'processed')
  );
create policy job_candidates_withdraw_self on public.job_candidates for delete to authenticated
  using (candidate_id = (select auth.uid()) and (select public.current_account_type()) = 'job_seeker');

-- Recruiter access to private resume data is granted only after the candidate applies.
create policy resumes_read_for_applied_job on public.resumes for select to authenticated
  using (exists (
    select 1 from public.job_candidates jc
    join public.jobs j on j.id = jc.job_id
    where jc.resume_id = resumes.id and jc.candidate_id = resumes.candidate_id
      and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter'
  ));
create policy resume_profiles_read_for_applied_job on public.resume_profiles for select to authenticated
  using (exists (
    select 1 from public.job_candidates jc
    join public.jobs j on j.id = jc.job_id
    where jc.resume_id = resume_profiles.resume_id and jc.candidate_id = resume_profiles.candidate_id
      and j.recruiter_id = (select auth.uid()) and (select public.current_account_type()) = 'recruiter'
  ));

-- Recruiters can read/insert/update a result only for a candidate who applied to their job.
drop policy if exists screening_results_read_candidate_or_job_recruiter on public.screening_results;
create policy screening_results_read_authorized_parties on public.screening_results for select to authenticated
  using (
    candidate_id = (select auth.uid())
    or exists (select 1 from public.job_candidates jc join public.jobs j on j.id = jc.job_id
      where jc.job_id = screening_results.job_id and jc.resume_id = screening_results.resume_id
        and jc.candidate_id = screening_results.candidate_id and j.recruiter_id = (select auth.uid())
        and (select public.current_account_type()) = 'recruiter')
  );
grant insert, update on public.screening_results to authenticated;
create policy screening_results_insert_applied_candidate on public.screening_results for insert to authenticated
  with check (
    exists (select 1 from public.job_candidates jc join public.jobs j on j.id = jc.job_id
      where jc.job_id = screening_results.job_id and jc.resume_id = screening_results.resume_id
        and jc.candidate_id = screening_results.candidate_id and j.recruiter_id = (select auth.uid())
        and (select public.current_account_type()) = 'recruiter')
  );
create policy screening_results_update_applied_candidate on public.screening_results for update to authenticated
  using (
    exists (select 1 from public.job_candidates jc join public.jobs j on j.id = jc.job_id
      where jc.job_id = screening_results.job_id and jc.resume_id = screening_results.resume_id
        and jc.candidate_id = screening_results.candidate_id and j.recruiter_id = (select auth.uid())
        and (select public.current_account_type()) = 'recruiter')
  ) with check (
    exists (select 1 from public.job_candidates jc join public.jobs j on j.id = jc.job_id
      where jc.job_id = screening_results.job_id and jc.resume_id = screening_results.resume_id
        and jc.candidate_id = screening_results.candidate_id and j.recruiter_id = (select auth.uid())
        and (select public.current_account_type()) = 'recruiter')
  );
create index screening_results_job_resume_created_idx on public.screening_results(job_id, resume_id, created_at desc);
