-- Task 8: expose limited candidate identity fields to recruiters only after a
-- candidate has applied to one of their jobs. All access remains JWT/RLS scoped.
grant select (full_name, email, phone, location) on public.profiles to authenticated;
create policy profiles_read_applied_candidates on public.profiles for select to authenticated
  using (
    exists (
      select 1 from public.job_candidates jc
      join public.jobs j on j.id = jc.job_id
      where jc.candidate_id = profiles.id
        and j.recruiter_id = (select auth.uid())
        and (select public.current_account_type()) = 'recruiter'
    )
  );

create policy "Recruiters read resumes for applied candidates"
on storage.objects for select to authenticated
using (
  bucket_id = 'talentiq-resumes'
  and exists (
    select 1 from public.resumes r
    join public.job_candidates jc on jc.resume_id = r.id and jc.candidate_id = r.candidate_id
    join public.jobs j on j.id = jc.job_id
    where r.file_path = storage.objects.name
      and j.recruiter_id = (select auth.uid())
      and (select public.current_account_type()) = 'recruiter'
  )
);
