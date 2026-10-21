import { useEffect, useState } from 'react'
import { BriefcaseBusiness, Plus, MapPin, Clock3, ArrowUpRight, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getJob, getJobs } from '../services/jobService'
import type { JobRecord } from '../types/job'
import './JobPages.css'

const employment: Record<string, string> = { full_time: 'Full-time', part_time: 'Part-time', contract: 'Contract', temporary: 'Temporary', internship: 'Internship', other: 'Other' }
export default function JobsPage() {
  const { jobId } = useParams()
  const [jobs, setJobs] = useState<JobRecord[]>([])
  const [selected, setSelected] = useState<JobRecord | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    setBusy(true); setError('')
    if (jobId) {
      void getJob(jobId).then(job => { if (active) setSelected(job) }).catch(err => { if (active) setError(err instanceof Error ? err.message : 'Job could not be loaded.') }).finally(() => { if (active) setBusy(false) })
    } else {
      void getJobs().then(list => { if (active) setJobs(list) }).catch(err => { if (active) setError(err instanceof Error ? err.message : 'Jobs could not be loaded.') }).finally(() => { if (active) setBusy(false) })
    }
    return () => { active = false }
  }, [jobId])
  if (jobId && selected) return <JobDetail job={selected} />
  return <main className="job-page"><header className="job-top"><Link to="/dashboard" className="job-brand">Talent<span>IQ</span></Link><nav><Link to="/dashboard">Workspace</Link><span>/</span><strong>Job postings</strong></nav><Link className="button button-dark" to="/jobs/new"><Plus size={16}/> New job</Link></header>
    <section className="job-content"><div className="job-heading"><div><div className="job-eyebrow"><BriefcaseBusiness size={15}/> RECRUITER WORKSPACE</div><h1>Your job postings</h1><p>Build clear role profiles from a job description and manage them in one place.</p></div><Link className="button button-dark" to="/jobs/new"><Plus size={16}/> Create a job</Link></div>
      {error && <div className="job-alert">{error}</div>}{busy ? <div className="job-empty">Loading your jobs…</div> : jobs.length === 0 ? <div className="job-empty"><div className="job-empty-icon"><Sparkles/></div><h2>Your next great hire starts with a clear role.</h2><p>Add a job description and let TalentIQ organize the role details, responsibilities, and requirements.</p><Link className="button button-dark" to="/jobs/new"><Plus size={16}/> Create your first job</Link></div> : <div className="job-grid">{jobs.map(job => <Link to={`/jobs/${job.id}`} className="job-card" key={job.id}><div className="job-card-top"><div className="job-card-icon"><BriefcaseBusiness size={19}/></div><span className={`job-status ${job.status}`}>{job.status}</span></div><h2>{job.title}</h2><p>{job.department || 'Team not specified'}</p><div className="job-card-meta">{job.location && <span><MapPin size={14}/>{job.location}</span>}{job.employment_type && <span><Clock3 size={14}/>{employment[job.employment_type] || job.employment_type}</span>}</div><div className="job-card-bottom"><span className={`analysis-state ${job.analysis_status}`}><i/>{job.analysis_status === 'analyzed' ? 'Description analyzed' : 'Analysis pending'}</span><ArrowUpRight size={17}/></div></Link>)}</div>}</section>
  </main>
}

function JobDetail({ job }: { job: JobRecord }) {
  const req = job.requirements.filter(x => x.importance === 'required'), pref = job.requirements.filter(x => x.importance === 'preferred')
  return <main className="job-page"><header className="job-top"><Link to="/jobs" className="job-brand">Talent<span>IQ</span></Link><nav><Link to="/dashboard">Workspace</Link><span>/</span><Link to="/jobs">Job postings</Link><span>/</span><strong>{job.title}</strong></nav><Link className="button button-dark" to="/jobs/new"><Plus size={16}/> New job</Link></header><section className="job-content detail-content"><Link className="job-back" to="/jobs">← All jobs</Link><div className="detail-hero"><div><div className="job-eyebrow">JOB INTELLIGENCE · {job.status.toUpperCase()}</div><h1>{job.title}</h1><div className="job-card-meta">{job.location && <span><MapPin size={14}/>{job.location}</span>}{job.employment_type && <span><Clock3 size={14}/>{employment[job.employment_type] || job.employment_type}</span>}{job.work_mode && <span>{job.work_mode}</span>}</div></div><span className={`analysis-state ${job.analysis_status}`}><i/>{job.analysis_status === 'analyzed' ? 'Analyzed' : 'Analysis pending'}</span></div><div className="detail-actions"><Link className="button button-dark" to={`/jobs/${job.id}/matching`}>Match applied resumes</Link></div><div className="result-columns"><article className="result-card wide"><h2>Job summary</h2><p>{job.summary || job.description}</p></article><article className="result-card"><h2>Experience</h2><p>{job.experience_min == null ? 'Not specified' : `${job.experience_min}+ years`}{job.experience_max != null ? ` · up to ${job.experience_max} years` : ''}</p></article><article className="result-card"><h2>Education</h2><p>{job.education_requirement || 'Not specified'}</p></article><article className="result-card wide"><h2>Responsibilities</h2>{job.responsibilities.length ? <ul>{job.responsibilities.map((x,i)=><li key={i}>{x}</li>)}</ul> : <p>No responsibilities were detected.</p>}</article><article className="result-card"><h2><span className="required-dot"/>Required skills</h2><SkillChips items={req}/></article><article className="result-card"><h2><span className="preferred-dot"/>Preferred skills</h2><SkillChips items={pref}/></article><SavedSkillCategories items={job.requirements}/><article className="result-card"><h2>Certifications</h2><SkillChips items={job.certifications_json.map(x=>({name:x.name,importance:x.importance}))}/></article><article className="result-card"><h2>Benefits</h2><SkillChips items={job.benefits_json.map(name=>({name,importance:'preferred' as const}))}/></article></div></section></main>
}
function SkillChips({ items }: { items: Array<{ name: string }> }) { return items.length ? <div className="skill-chips">{items.map((x,i)=><span key={`${x.name}-${i}`}>{x.name}</span>)}</div> : <p>None identified</p> }
function SavedSkillCategories({items}: {items: JobRecord['requirements']}) {
  const labels: Record<string,string> = { technical: 'Technical skills', soft_skill: 'Soft skills', tool: 'Tools', framework: 'Frameworks', programming_language: 'Programming languages', database: 'Databases', cloud_platform: 'Cloud platforms' }
  const grouped = new Map<string,string[]>()
  items.forEach(item => { if (!item.category) return; const current = grouped.get(item.category) || []; if (!current.includes(item.name)) current.push(item.name); grouped.set(item.category,current) })
  if (!grouped.size) return null
  return <article className="result-card wide"><h2>Skills by category</h2><div className="category-list">{[...grouped.entries()].map(([category,names])=><div className="category-row" key={category}><strong>{labels[category] || category}</strong><SkillChips items={names.map(name=>({name}))}/></div>)}</div></article>
}
