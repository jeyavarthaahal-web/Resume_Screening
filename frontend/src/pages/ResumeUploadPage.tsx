import { ArrowLeft, ArrowRight, Award, BriefcaseBusiness, Check, CheckCircle2, CloudUpload, FileText, Languages, LoaderCircle, MapPin, Phone, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AuthError } from '../components/common/AuthError'
import { Brand } from '../components/common/Brand'
import { uploadResume } from '../services/resumeService'
import type { PublishedJobSummary } from '../types/matching'
import type { ResumeProfile, ResumeUploadResponse } from '../types/resume'
import './ResumeUploadPage.css'
import './ResumeReviewPolish.css'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const stages = ['Uploading', 'Extracting', 'Analyzing', 'Saving']

function validateSelection(file: File): string | null {
  const extension = file.name.toLowerCase().split('.').pop()
  if (extension !== 'pdf' && extension !== 'docx') return 'Choose a PDF or DOCX resume.'
  if (!file.size) return 'The selected file is empty.'
  if (file.size > MAX_FILE_SIZE) return 'This file is too large. The maximum size is 10 MB.'
  return null
}

function formatFileSize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function ResumeSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="resume-result-section"><h3>{title}</h3>{children}</section>
}

function ResumePreview({ result }: { result: ResumeUploadResponse }) {
  const profile: ResumeProfile = result.profile
  const allSkills = [...new Set(Object.values(profile.skills).flat())]
  const contact = [profile.email, profile.phone, profile.location].filter(Boolean)
  const missingInformation = [
    !profile.full_name && 'Full name',
    !profile.email && 'Email address',
    !profile.phone && 'Phone number',
    !profile.location && 'Location',
    !profile.summary && 'Professional summary',
    !allSkills.length && 'Recognizable skills',
    !profile.experience.length && 'Work experience',
    !profile.education.length && 'Education',
    !profile.projects.length && 'Projects',
  ].filter((item): item is string => Boolean(item))
  return <div className="resume-preview">
    <div className="resume-preview-heading"><div><span className="resume-kicker">RESUME INTELLIGENCE</span><h2>{profile.full_name || result.resume.file_name}</h2><p>{result.resume.file_name} <span>·</span> {formatFileSize(result.resume.file_size)} <span>·</span> Processed</p></div><span className="resume-complete"><CheckCircle2 size={16}/> Complete</span></div>
    {contact.length > 0 && <div className="resume-contact-row">{profile.email && <span>{profile.email}</span>}{profile.phone && <span><Phone size={14}/>{profile.phone}</span>}{profile.location && <span><MapPin size={14}/>{profile.location}</span>}</div>}
    <div className="resume-result-grid">
      <ResumeSection title="Summary">{profile.summary ? <p className="resume-copy">{profile.summary}</p> : <p className="resume-empty-copy">No summary section was detected.</p>}</ResumeSection>
      <ResumeSection title={`Skills${allSkills.length ? ` · ${allSkills.length}` : ''}`}>{allSkills.length ? <div className="resume-skill-list">{allSkills.map(skill => <span className="resume-skill" key={skill}>{skill}</span>)}</div> : <p className="resume-empty-copy">No recognizable skills found.</p>}</ResumeSection>
      <ResumeSection title="Experience">{profile.experience.length ? <div className="resume-entry-list">{profile.experience.map((item, index) => <article className="resume-entry" key={`${item.job_title}-${item.company}-${index}`}><div className="resume-entry-title"><strong>{item.job_title || 'Experience'}</strong><span>{[item.start_date, item.end_date].filter(Boolean).join(' – ')}</span></div><p>{[item.company, item.location].filter(Boolean).join(' · ')}</p>{item.description && <p className="resume-copy">{item.description}</p>}</article>)}</div> : <p className="resume-empty-copy">No dated experience entry was detected.</p>}</ResumeSection>
      <ResumeSection title="Education">{profile.education.length ? <div className="resume-entry-list">{profile.education.map((item, index) => <article className="resume-entry" key={`${item.institution}-${index}`}><div className="resume-entry-title"><strong>{item.degree || item.field_of_study || 'Education'}</strong><span>{[item.start_date, item.end_date].filter(Boolean).join(' – ')}</span></div><p>{[item.institution, item.location].filter(Boolean).join(' · ')}</p></article>)}</div> : <p className="resume-empty-copy">No education entry was detected.</p>}</ResumeSection>
      <ResumeSection title="Projects">{profile.projects.length ? <div className="resume-entry-list">{profile.projects.map((item, index) => <article className="resume-entry" key={`${item.project_name}-${index}`}><strong>{item.project_name || 'Project'}</strong>{item.description && <p className="resume-copy">{item.description}</p>}{item.technologies.length > 0 && <p>{item.technologies.join(' · ')}</p>}</article>)}</div> : <p className="resume-empty-copy">No project section was detected.</p>}</ResumeSection>
      <ResumeSection title="Certifications">{profile.certifications.length ? <ul className="resume-simple-list">{profile.certifications.map((item, index) => <li key={`${item.certification_name}-${index}`}><Award size={15}/><span><strong>{item.certification_name}</strong>{item.issuer && <small>{item.issuer}</small>}</span></li>)}</ul> : <p className="resume-empty-copy">No certifications detected.</p>}</ResumeSection>
      <ResumeSection title="Languages">{profile.languages.length ? <div className="resume-language-list">{profile.languages.map(item => <span key={item.name}><Languages size={14}/>{item.name}{item.proficiency && <small>{item.proficiency}</small>}</span>)}</div> : <p className="resume-empty-copy">No spoken languages detected.</p>}</ResumeSection>
      <ResumeSection title="Achievements">{profile.achievements.length ? <ul className="resume-simple-list">{profile.achievements.map((item, index) => <li key={`${item.title}-${index}`}><Check size={15}/><span>{item.title}</span></li>)}</ul> : <p className="resume-empty-copy">No achievement section was detected.</p>}</ResumeSection>
    </div>
    <ResumeSection title="Information to review">{missingInformation.length ? <ul className="resume-missing-list">{missingInformation.map(item => <li key={item}>{item}</li>)}</ul> : <p className="resume-empty-copy">The main profile fields were identified. Review each extracted detail for accuracy.</p>}</ResumeSection>
    {profile.years_experience !== null && <div className="resume-experience-note"><BriefcaseBusiness size={15}/><span>Approx. {profile.years_experience} years of experience based on dated work history</span></div>}
    <PublishedJobApplications resumeId={result.resume.id}/>
  </div>
}

function PublishedJobApplications({ resumeId }: { resumeId: string }) {
  const [jobs, setJobs] = useState<PublishedJobSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [applyingJobId, setApplyingJobId] = useState<string | null>(null)
  const [appliedJobIds, setAppliedJobIds] = useState<string[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    void import('../services/matchingService').then(({ getPublishedJobs }) => getPublishedJobs()).then(setJobs).catch(() => setError('Published jobs could not be loaded. Please try again.')).finally(() => setLoading(false))
  }, [])

  async function apply(jobId: string) {
    setApplyingJobId(jobId)
    setError('')
    try {
      const { applyResumeToJob } = await import('../services/matchingService')
      await applyResumeToJob(jobId, resumeId)
      setAppliedJobIds(current => [...current, jobId])
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : 'Your application could not be submitted.')
    } finally {
      setApplyingJobId(null)
    }
  }

  return <ResumeSection title="Apply to a published job">
    <p className="resume-copy">Your profile is shared only with the recruiter who owns a job you apply to.</p>
    {loading && <p className="resume-empty-copy">Loading published jobs…</p>}
    {error && <p className="resume-missing-list" role="alert">{error}</p>}
    {!loading && !error && jobs.length === 0 && <p className="resume-empty-copy">No published jobs are available right now.</p>}
    {!loading && jobs.map(job => <article className="resume-entry" key={job.id}>
      <div className="resume-entry-title"><strong>{job.title}</strong><span>{[job.department, job.location, job.employment_type?.replace('_', ' ')].filter(Boolean).join(' · ')}</span></div>
      <button className="button button-dark" type="button" disabled={applyingJobId !== null || appliedJobIds.includes(job.id)} onClick={() => void apply(job.id)}>
        {appliedJobIds.includes(job.id) ? 'Application submitted' : applyingJobId === job.id ? 'Submitting…' : 'Apply with this resume'}
      </button>
    </article>)}
  </ResumeSection>
}

export default function ResumeUploadPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ResumeUploadResponse | null>(null)

  function chooseFile(next: File | undefined) {
    if (!next || busy) return
    setResult(null)
    setError(validateSelection(next))
    setFile(next)
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragActive(false)
    if (event.dataTransfer.files.length !== 1) {
      setError('Choose exactly one resume file.')
      return
    }
    chooseFile(event.dataTransfer.files[0])
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      inputRef.current?.click()
    }
  }

  async function submit() {
    if (!file || busy) return
    const issue = validateSelection(file)
    if (issue) { setError(issue); return }
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await uploadResume(file))
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'We could not process this resume. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return <main className="resume-page">
    <header className="resume-topbar"><Brand/><Link to="/career-assistant" className="resume-back-link"><ArrowLeft size={16}/> Job seeker workspace</Link></header>
    <div className="resume-content">
      <div className="resume-page-intro"><div className="resume-intro-icon"><Sparkles size={19}/></div><span className="resume-kicker">YOUR CAREER PROFILE</span><h1>Make your resume easier to understand.</h1><p>Upload a PDF or DOCX and we’ll organize the text into a clear profile you can review.</p></div>

      {!result && <section className="resume-upload-card" aria-labelledby="resume-upload-title">
        <div className="resume-card-heading"><div><h2 id="resume-upload-title">Upload your resume</h2><p>Your file stays private to your account.</p></div><span className="resume-secure-label"><CheckCircle2 size={14}/> Private upload</span></div>
        <div className={dragActive ? 'resume-dropzone active' : 'resume-dropzone'} role="button" tabIndex={0} aria-label="Choose or drop one PDF or DOCX resume" onClick={event => { if (!(event.target as HTMLElement).closest('button')) inputRef.current?.click() }} onDragEnter={event => { event.preventDefault(); setDragActive(true) }} onDragOver={event => event.preventDefault()} onDragLeave={event => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragActive(false) }} onDrop={onDrop} onKeyDown={onKeyDown}>
          <input ref={inputRef} className="resume-file-input" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => chooseFile(event.target.files?.[0])}/>
          <div className="resume-upload-icon"><CloudUpload size={25}/></div><strong>Drop your resume here</strong><span>or browse from your device</span><button className="resume-browse-button" type="button" onClick={event => { event.stopPropagation(); inputRef.current?.click() }}>Browse files</button><small>PDF or DOCX · Up to 10 MB</small>
        </div>
        {file && <div className="resume-selected-file"><span className="resume-file-icon"><FileText size={18}/></span><span className="resume-selected-name"><strong>{file.name}</strong><small>{formatFileSize(file.size)} · {file.name.toLowerCase().endsWith('.pdf') ? 'PDF document' : 'DOCX document'}</small></span><button type="button" aria-label="Remove selected file" disabled={busy} onClick={() => { setFile(null); setError(null); if (inputRef.current) inputRef.current.value = '' }}><X size={17}/></button></div>}
        {error && <AuthError message={error}/>}
        <button className="button button-dark resume-submit" type="button" disabled={!file || busy || Boolean(file && validateSelection(file))} onClick={() => void submit()}>{busy ? <><LoaderCircle className="resume-spin" size={17}/> Processing resume…</> : <>Upload and review <ArrowRight className="resume-submit-arrow" size={16}/></>}</button>
        {busy && <div className="resume-progress" role="status" aria-live="polite"><div className="resume-progress-heading"><LoaderCircle className="resume-spin" size={16}/><span>Working through your resume</span></div><ol>{stages.map((stage, index) => <li className={index === 0 ? 'current' : ''} key={stage}><span>{index === 0 ? <LoaderCircle className="resume-spin" size={15}/> : <span className="resume-stage-dot"/>}</span>{stage}</li>)}</ol><small>Processing runs as one secure request; individual stage timing is not reported.</small></div>}
      </section>}

      {result && <><div className="resume-success-banner"><CheckCircle2 size={19}/><span><strong>Your resume is ready to review.</strong><small>We extracted the text and saved your structured profile.</small></span><Link className="resume-assistant-link" to="/career-assistant">Open Career Assistant <ArrowRight size={15}/></Link></div><ResumePreview result={result}/><button className="resume-upload-another" type="button" onClick={() => { setResult(null); setFile(null); if (inputRef.current) inputRef.current.value = '' }}>Upload another resume</button></>}
      <p className="resume-privacy-note">Your uploaded file is stored in a private bucket. Extraction is deterministic and does not use OCR or an AI model.</p>
    </div>
  </main>
}
