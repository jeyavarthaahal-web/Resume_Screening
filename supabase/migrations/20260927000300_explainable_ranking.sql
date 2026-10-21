-- Task 7: structured, traceable explanations attached to the Task 6 result.
alter table public.screening_results
  alter column matched_skills drop default,
  alter column partial_skills drop default,
  alter column missing_skills drop default;

alter table public.screening_results
  alter column matched_skills type jsonb using to_jsonb(matched_skills),
  alter column partial_skills type jsonb using to_jsonb(partial_skills),
  alter column missing_skills type jsonb using to_jsonb(missing_skills),
  alter column matched_skills set default '[]'::jsonb,
  alter column partial_skills set default '[]'::jsonb,
  alter column missing_skills set default '[]'::jsonb,
  add column score_breakdown jsonb not null default '{}'::jsonb check (jsonb_typeof(score_breakdown) = 'object'),
  add column explanation text,
  add column ranking_details jsonb not null default '{}'::jsonb check (jsonb_typeof(ranking_details) = 'object');

alter table public.screening_results
  add constraint screening_results_matched_skills_array check (jsonb_typeof(matched_skills) = 'array'),
  add constraint screening_results_partial_skills_array check (jsonb_typeof(partial_skills) = 'array'),
  add constraint screening_results_missing_skills_array check (jsonb_typeof(missing_skills) = 'array');
