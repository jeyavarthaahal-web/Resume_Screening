-- Task 8: Allow recruiters to read candidate profiles for applied/matched candidates,
-- and permit authenticated users to read profiles needed for collaboration and candidate pipelines.

drop policy if exists profiles_read_recruiter on public.profiles;

create policy profiles_read_recruiter on public.profiles for select to authenticated
using (
  id = (select auth.uid())
  or exists (
    select 1 from public.job_candidates jc
    join public.jobs j on j.id = jc.job_id
    where jc.candidate_id = profiles.id
      and j.recruiter_id = (select auth.uid())
      and (select public.current_account_type()) = 'recruiter'
  )
  or exists (
    select 1 from public.resume_profiles rp
    join public.resumes r on r.id = rp.resume_id
    where rp.candidate_id = profiles.id
      and (select public.current_account_type()) = 'recruiter'
  )
);
