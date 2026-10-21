import { useCallback, useEffect, useState, type CSSProperties } from 'react'
import { ArrowLeft, BookOpenCheck, FileSearch, LoaderCircle, RefreshCw, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { generateRankingExplanation, getRankingExplanation } from '../services/rankingService'
import type { Evidence, RankingExplanation, SkillClassification } from '../types/ranking'
import './JobPages.css'
import './Ranking.css'

const COMPONENT_LABELS: Record<string, string> = { semantic: 'Semantic match', skills: 'Skill match', experience: 'Experience match', education: 'Education match', projects: 'Project relevance' }

export default function CandidateExplanationPage() {
  const { jobId = '', resumeId = '' } = useParams()
  const [result, setResult] = useState<RankingExplanation | null>(null)
  const [busy, setBusy] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async (refresh = false) => {
    setError('')
    if (refresh) setRefreshing(true); else setBusy(true)
    try { setResult(refresh ? await generateRankingExplanation(jobId, resumeId) : await getRankingExplanation(jobId, resumeId)) }
    catch (err) { setError(err instanceof Error ? err.message : 'The explanation could not be loaded.') }
    finally { setBusy(false); setRefreshing(false) }
  }, [jobId, resumeId])
  useEffect(() => { void load() }, [load])

  return <main className="job-page"><header className="job-top"><Link to="/jobs" className="job-brand">Talent<span>IQ</span></Link><nav><Link to="/dashboard">Workspace</Link><span>/</span><Link to={`/jobs/${jobId}`}>Job posting</Link><span>/</span><Link to={`/jobs/${jobId}/matching`}>AI matching</Link><span>/</span><strong>Score explanation</strong></nav><span className="draft-label">TASK 7</span></header>
    <section className="job-content explanation-content"><Link className="job-back" to={`/jobs/${jobId}/matching`}><ArrowLeft size={15}/> Back to matching</Link>
      {busy ? <div className="job-empty"><LoaderCircle className="spin"/><p>Loading score explanation…</p></div> : error ? <div className="job-empty"><div className="job-empty-icon"><FileSearch/></div><h2>Explanation unavailable</h2><p>{error}</p><Link className="button button-dark" to={`/jobs/${jobId}/matching`}>Return to matching</Link></div> : result && <>
        <div className="explanation-heading"><div><div className="job-eyebrow"><Sparkles size={15}/> MATCH EXPLANATION</div><h1>Why this score?</h1><p>Resume {result.resume_id.slice(0, 8)} · generated from the saved Task 6 result and extracted profile fields.</p></div><button className="button button-dark" onClick={()=>void load(true)} disabled={refreshing}>{refreshing?<LoaderCircle className="spin" size={15}/>:<RefreshCw size={14}/>} Refresh explanation</button></div>
        <section className="explanation-hero"><div className="overall-score-ring" style={{'--score': `${result.overall_score}%`} as CSSProperties}><strong>{result.overall_score.toFixed(2)}<small>%</small></strong><span>Overall match</span></div><div className="explanation-summary"><h2>Score summary</h2><p>{result.explanation}</p><div className={`data-quality ${result.data_quality}`}><BookOpenCheck size={15}/><span><strong>{result.data_quality.replace('_',' ')}</strong> · {result.data_quality_note}</span></div></div></section>
        <section className="explanation-section"><div className="explanation-section-title"><h2>Score breakdown</h2><p>Stored Task 6 scores with the established component weights.</p></div><div className="breakdown-grid">{(['semantic','skills','experience','education','projects'] as const).map(key=>{const metric=result.score_breakdown[key];return <article className="breakdown-card" key={key}><div><strong>{COMPONENT_LABELS[key]}</strong><span>{(metric.weight*100).toFixed(0)}% weight</span></div><b>{metric.score.toFixed(2)}<small>/100</small></b><i><em style={{width:`${metric.score}%`}}/></i><p>{metric.weighted_contribution.toFixed(2)} points contributed</p></article>})}</div></section>
        <section className="explanation-columns"><article className="explanation-panel"><SectionTitle title="Matched skills" count={result.matched_skills.length}/><SkillList items={result.matched_skills} empty="No exact or normalized skill matches were identified." kind="matched"/></article><article className="explanation-panel"><SectionTitle title="Partial matches" count={result.partial_skills.length}/><SkillList items={result.partial_skills} empty="No curated related skill matches were identified." kind="partial"/></article><article className="explanation-panel"><SectionTitle title="Missing skills" count={result.missing_skills.length}/><SkillList items={result.missing_skills} empty="No listed job skills are missing from the extracted profile." kind="missing"/></article><article className="explanation-panel"><SectionTitle title="Strengths" count={result.strengths.length}/>{result.strengths.length ? <ul className="finding-list">{result.strengths.map((item,i)=><li key={`${item.title}-${i}`}><strong>{item.title}</strong><p>{item.description}</p><EvidenceList items={item.evidence}/></li>)}</ul>:<p className="empty-note">The saved result and extracted data do not support a specific strength statement.</p>}</article><article className="explanation-panel"><SectionTitle title="Gaps" count={result.gaps.length}/>{result.gaps.length ? <ul className="finding-list">{result.gaps.map((item,i)=><li key={`${item.title}-${i}`}><div className="finding-heading"><strong>{item.title}</strong><span>{item.severity}</span></div><p>{item.description}</p><EvidenceList items={item.evidence}/></li>)}</ul>:<p className="empty-note">No specific gap was identified in the available structured information.</p>}</article><article className="explanation-panel"><SectionTitle title="Experience and education"/><div className="fact-block"><strong>Experience</strong><p>{experienceText(result)}</p></div><div className="fact-block"><strong>Education</strong><p>{educationText(result)}</p></div></article></section>
        <section className="explanation-section"><div className="explanation-section-title"><h2>Relevant projects</h2><p>Only extracted projects listing a job-related technology are included.</p></div>{result.relevant_projects.length ? <div className="project-evidence-grid">{result.relevant_projects.map(project=><article className="project-evidence" key={project.project_name}><h3>{project.project_name}</h3><p>Technologies: {project.relevant_technologies.join(', ') || 'Not listed'}</p><p>Related job skills: {project.related_job_requirements.join(', ')}</p></article>)}</div>:<p className="empty-note">No extracted project with an explicitly related listed technology was identified.</p>}</section>
        <section className="explanation-section"><div className="explanation-section-title"><h2>Source evidence</h2><p>Short excerpts from structured resume and job fields.</p></div><div className="evidence-grid">{(['resume','job'] as const).map(source=><article className="evidence-card" key={source}><h3>{source==='resume'?'Resume':'Job requirements'}</h3>{result.evidence.filter(item=>item.source===source).length ? <ul>{result.evidence.filter(item=>item.source===source).map((item,i)=><li key={`${item.type}-${i}`}><span>{item.type}</span><p>{item.text}</p></li>)}</ul>:<p className="empty-note">No structured {source} evidence was available.</p>}</article>)}</div></section>
      </>}
    </section></main>
}

function SectionTitle({title,count}:{title:string;count?:number}) { return <div className="explanation-panel-title"><h2>{title}</h2>{count!==undefined&&<span>{count}</span>}</div> }
function SkillList({items,empty,kind}:{items:SkillClassification[];empty:string;kind:string}) { return items.length ? <ul className={`skill-explanation-list ${kind}`}>{items.map((item,i)=><li key={`${item.name}-${i}`}><div><strong>{item.name}</strong>{item.resume_skill&&item.resume_skill!==item.name&&<small>Resume lists {item.resume_skill}</small>}</div><span>{item.importance}</span></li>)}</ul>:<p className="empty-note">{empty}</p> }
function EvidenceList({items}:{items:Evidence[]}) { return items.length ? <ul className="inline-evidence">{items.map((item,i)=><li key={`${item.source}-${i}`}>{item.source}: {item.text}</li>)}</ul>:null }
function experienceText(result:RankingExplanation) {
  const item=result.experience_context
  if(item.status==='not_identified') return 'Experience information was not clearly identified in the resume.'
  if(item.status==='not_specified') return item.candidate_years==null?'No experience requirement was specified; candidate experience was not identified.':`Task 4 extracted ${item.candidate_years} years; no experience requirement was specified.`
  if(item.status==='maximum_only') return `Task 4 extracted ${item.candidate_years} years. The job lists a maximum of ${item.maximum_years} years and no minimum.`
  const max=item.maximum_years==null?'':` Listed maximum: ${item.maximum_years} years.`
  return `Candidate experience: ${item.candidate_years} years. Minimum: ${item.minimum_years} years.${max}`
}
function educationText(result:RankingExplanation) {
  const item=result.education_context
  if(item.status==='not_specified') return item.candidate.length?`Candidate: ${item.candidate.join('; ')}. No education requirement was specified.`:'No education information or requirement was identified.'
  if(item.status==='not_identified') return `Candidate education was not identified. Requirement: ${item.requirement.join('; ')}.`
  return `Candidate: ${item.candidate.join('; ')}. Requirement: ${item.requirement.join('; ')}. Comparison: ${item.status}.`
}
