import { useEffect, useState } from 'react'
import { ArrowLeft, FileSearch, LoaderCircle, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getMatchingCandidates, getMatchingResults, matchCandidatesToJob } from '../services/matchingService'
import type { MatchingCandidate, MatchingFailure, MatchingResult } from '../types/matching'
import './JobPages.css'

export default function MatchingPage() {
  const { jobId = '' } = useParams()
  const [candidates, setCandidates] = useState<MatchingCandidate[]>([])
  const [results, setResults] = useState<MatchingResult[]>([])
  const [failures, setFailures] = useState<MatchingFailure[]>([])
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    void getMatchingCandidates(jobId).then(async rows => {
      if (!active) return
      setCandidates(rows)
      try { const saved = await getMatchingResults(jobId); if (active) setResults(saved) } catch { /* Scores can be calculated if none have been saved yet. */ }
    }).catch(err => { if (active) setError(err instanceof Error ? err.message : 'Applied resumes could not be loaded.') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [jobId])
  async function runMatching() {
    setBusy(true); setError(''); setFailures([])
    try { const response = await matchCandidatesToJob(jobId); setResults(response.results); setFailures(response.failures) }
    catch (err) { setError(err instanceof Error ? err.message : 'Matching failed. Please try again.') }
    finally { setBusy(false) }
  }
  const byResume = new Map(results.map(result => [result.resume_id, result]))
  return <main className="job-page"><header className="job-top"><Link to="/jobs" className="job-brand">Talent<span>IQ</span></Link><nav><Link to="/dashboard">Workspace</Link><span>/</span><Link to="/jobs">Job postings</Link><span>/</span><strong>AI matching</strong></nav><span className="draft-label">TASK 6</span></header><section className="job-content matching-content"><Link className="job-back" to={`/jobs/${jobId}`}><ArrowLeft size={15}/> Back to job</Link><div className="job-heading"><div><div className="job-eyebrow"><Sparkles size={15}/> NUMERICAL MATCHING</div><h1>Match applied resumes</h1><p>Calculate semantic, skill, experience, education, and project scores for resumes applicants shared with this job.</p></div><button className="button button-dark" onClick={()=>void runMatching()} disabled={busy || loading || candidates.length===0}>{busy?<><LoaderCircle className="spin" size={15}/> Calculating…</>:<><Sparkles size={15}/> Calculate matches</>}</button></div>
    {error && <div className="job-alert" role="alert">{error}</div>}{failures.map(item=><div className="job-alert" key={item.resume_id}>{item.message} · {item.resume_id.slice(0,8)}</div>)}
    {loading ? <div className="job-empty">Loading applied resumes…</div> : candidates.length===0 ? <div className="job-empty"><div className="job-empty-icon"><Sparkles/></div><h2>No applied resumes are associated with this job.</h2><p>Matching is available for processed resumes that candidates have explicitly associated with this published job.</p></div> : <div className="matching-list">{candidates.map(candidate=>{const result=byResume.get(candidate.resume_id);return <article className="matching-card" key={candidate.resume_id}><div className="matching-candidate"><div className="matching-avatar"><FileSearch size={16}/></div><div><strong>Applied resume</strong><small>Candidate {candidate.candidate_id.slice(0,8)} · Resume {candidate.resume_id.slice(0,8)}</small></div></div>{result?<div className="matching-result-panel"><ScoreMetrics result={result}/><Link className="explain-link" to={`/jobs/${jobId}/resumes/${candidate.resume_id}/explanation`}>Explain this score <ArrowLeft size={13}/></Link></div>:<span className="analysis-state"><i/>Not matched yet</span>}</article>})}</div>}
  </section></main>
}

function ScoreMetrics({result}:{result:MatchingResult}) {
  const metrics=[['Overall Match',result.overall_score],['Semantic Match',result.semantic_score],['Skill Match',result.skill_score],['Experience Match',result.experience_score],['Education Match',result.education_score],['Project Match',result.project_score]] as const
  return <div className="match-metrics">{metrics.map(([label,value],index)=><div className={index===0?'match-metric overall':'match-metric'} key={label}><span>{label}</span><strong>{value.toFixed(2)}<small>/100</small></strong><i><b style={{width:`${value}%`}}/></i></div>)}</div>
}
