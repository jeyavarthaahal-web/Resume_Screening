import { ArrowLeft, ArrowRight, BookOpenText, BriefcaseBusiness, CheckCircle2, Lightbulb, MessageSquareText, RefreshCcw, Sparkles, Target, TrendingUp, UserRoundSearch } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/common/Brand'
import { ProtectedRoute } from '../components/common/ProtectedRoute'
import { CareerAssistantChat } from '../components/career-assistant/CareerAssistantChat'
import { analyzeSkillGap, prepareInterview, reviewResume } from '../services/careerAssistantService'
import type { InterviewResult, ResumeReviewResult, SkillGapResult } from '../types/careerAssistant'
import './CareerAssistant.css'

const workflowCards = [
  { id: 'resume', label: 'Resume Improvement', icon: <Sparkles size={18} />, description: 'Refine your summary, strengths, and role fit.' },
  { id: 'skills', label: 'Skill Gap Analysis', icon: <Target size={18} />, description: 'Measure your current skills against a target role.' },
  { id: 'interview', label: 'Interview Preparation', icon: <BookOpenText size={18} />, description: 'Practice questions tailored to your experience and job.' },
  { id: 'guidance', label: 'Career Guidance', icon: <TrendingUp size={18} />, description: 'Map next milestones and learning areas.' },
] as const

export default function CareerAssistantPage() {
  const [activeWorkflow, setActiveWorkflow] = useState<'resume' | 'skills' | 'interview' | 'guidance'>('resume')
  const [review, setReview] = useState<ResumeReviewResult | null>(null)
  const [skillGap, setSkillGap] = useState<SkillGapResult | null>(null)
  const [interview, setInterview] = useState<InterviewResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (activeWorkflow === 'resume') void loadResumeReview()
    if (activeWorkflow === 'skills') void loadSkillGap()
    if (activeWorkflow === 'interview') void loadInterview()
  }, [activeWorkflow])

  async function loadResumeReview() {
    setLoading(true)
    setError(null)
    try {
      setReview(await reviewResume())
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'We could not load your resume review.')
    } finally {
      setLoading(false)
    }
  }

  async function loadSkillGap() {
    setLoading(true)
    setError(null)
    try {
      setSkillGap(await analyzeSkillGap({ job_description: 'Python, SQL, FastAPI, cloud engineering, backend systems, and stakeholder communication', target_role: 'Backend Engineer' }))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'We could not assess the skill gap.')
    } finally {
      setLoading(false)
    }
  }

  async function loadInterview() {
    setLoading(true)
    setError(null)
    try {
      setInterview(await prepareInterview({ interview_type: 'general', job_description: 'Backend engineer role focused on Python, SQL, and APIs.', target_role: 'Backend Engineer' }))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'We could not prepare interview questions.')
    } finally {
      setLoading(false)
    }
  }

  const emptyState = useMemo(() => !review && !skillGap && !interview && !loading, [review, skillGap, interview, loading])

  return <ProtectedRoute requiredRole="job_seeker"><main className="career-assistant-page"><header className="career-assistant-header"><div className="career-assistant-brand-row"><Brand/><Link to="/resumes/upload" className="career-back-link"><ArrowLeft size={15}/> Resume upload</Link></div><div className="career-assistant-copy"><span className="resume-kicker">JOB SEEKER WORKSPACE</span><h1>AI Career Assistant</h1><p>Improve your resume, identify skill gaps, and prepare for your next interview.</p></div></header>

    <section className="career-workflow-grid">
      {workflowCards.map((card) => (
        <button key={card.id} type="button" className={activeWorkflow === card.id ? 'career-workflow-card active' : 'career-workflow-card'} onClick={() => setActiveWorkflow(card.id)}>
          <span className="career-card-icon">{card.icon}</span>
          <div>
            <strong>{card.label}</strong>
            <small>{card.description}</small>
          </div>
          <ArrowRight size={16} />
        </button>
      ))}
    </section>

    <section className="career-assistant-content">
      <div className="career-main-column">
        {loading && <div className="career-state-card loading"><RefreshCcw size={16} className="career-spin" /> Generating your AI guidance…</div>}
        {error && <div className="career-state-card error"><MessageSquareText size={16} /> {error}</div>}
        {!loading && !error && activeWorkflow === 'resume' && review && (
          <div className="career-result-stack">
            <div className="career-section-card"><div className="career-section-heading"><Sparkles size={16}/> <h3>Resume Overview</h3></div><div className="career-mini-overview"><div><span>Name</span><strong>Candidate profile</strong></div><div><span>Summary</span><strong>{review.summary_improvements.length > 0 ? 'Available for improvement' : 'Strong summary detected'}</strong></div><div><span>Skills</span><strong>Technical and soft skills available</strong></div><div><span>Education</span><strong>Education entries should be reviewed</strong></div><div><span>Experience</span><strong>Experience entries available for targeted impact bullets</strong></div><div><span>Projects</span><strong>Project detail can be strengthened</strong></div></div></div>
            <div className="career-section-card"><div className="career-section-heading"><Lightbulb size={16}/> <h3>Summary Improvements</h3></div>{review.summary_improvements.length ? <ul className="career-bullets">{review.summary_improvements.map((item, index) => <li key={index}><strong>Current issue</strong><p>{item.current_issue}</p><strong>Suggested improvement</strong><p>{item.suggested_improvement}</p>{item.example_wording && <><strong>Example wording</strong><p>{item.example_wording}</p></>}</li>)}</ul> : <p className="career-empty-copy">No summary adjustments needed based on current profile data.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><BriefcaseBusiness size={16}/> <h3>Experience Improvements</h3></div>{review.experience_improvements.length ? <ul className="career-bullets">{review.experience_improvements.map((item, index) => <li key={index}><strong>Current issue</strong><p>{item.current_issue}</p><strong>Suggested improvement</strong><p>{item.suggested_improvement}</p>{item.example_wording && <><strong>Example wording</strong><p>{item.example_wording}</p></>}</li>)}</ul> : <p className="career-empty-copy">No experience gaps detected.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><Target size={16}/> <h3>Skills Improvements</h3></div>{review.skills_improvements.length ? <ul className="career-bullets">{review.skills_improvements.map((item, index) => <li key={index}><strong>Current issue</strong><p>{item.current_issue}</p><strong>Suggested improvement</strong><p>{item.suggested_improvement}</p>{item.example_wording && <><strong>Example wording</strong><p>{item.example_wording}</p></>}</li>)}</ul> : <p className="career-empty-copy">Skills section looks complete.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><CheckCircle2 size={16}/> <h3>Project Improvements</h3></div>{review.project_improvements.length ? <ul className="career-bullets">{review.project_improvements.map((item, index) => <li key={index}><strong>Current issue</strong><p>{item.current_issue}</p><strong>Suggested improvement</strong><p>{item.suggested_improvement}</p>{item.example_wording && <><strong>Example wording</strong><p>{item.example_wording}</p></>}</li>)}</ul> : <p className="career-empty-copy">Projects already show a clear description.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><UserRoundSearch size={16}/> <h3>Formatting Suggestions</h3></div><ul className="career-check-list">{review.formatting_suggestions.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
            <div className="career-section-card"><div className="career-section-heading"><MessageSquareText size={16}/> <h3>Missing Information</h3></div><ul className="career-check-list">{review.missing_information.length ? review.missing_information.map((item, index) => <li key={index}>{item}</li>) : <li>Resume information is complete.</li>}</ul></div>
          </div>
        )}

        {!loading && !error && activeWorkflow === 'skills' && skillGap && (
          <div className="career-result-stack">
            <div className="career-section-card"><div className="career-section-heading"><Target size={16}/> <h3>Matched Skills</h3></div>{skillGap.matched_skills.length ? <div className="career-pill-group">{skillGap.matched_skills.map((skill) => <span className="career-pill success" key={skill}>{skill}</span>)}</div> : <p className="career-empty-copy">No direct matches were detected.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><MessageSquareText size={16}/> <h3>Missing Skills</h3></div>{skillGap.missing_skills.length ? <div className="career-pill-group">{skillGap.missing_skills.map((skill) => <span className="career-pill warning" key={skill}>{skill}</span>)}</div> : <p className="career-empty-copy">No missing skills were identified from the provided role criteria.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><BookOpenText size={16}/> <h3>Partial Skills</h3></div>{skillGap.partial_skills.length ? <div className="career-pill-group">{skillGap.partial_skills.map((skill) => <span className="career-pill neutral" key={skill}>{skill}</span>)}</div> : <p className="career-empty-copy">No partial matches were detected.</p>}</div>
            <div className="career-section-card"><div className="career-section-heading"><TrendingUp size={16}/> <h3>Suggested Learning Areas</h3></div><ul className="career-check-list">{skillGap.suggested_learning_areas.map((area) => <li key={area}>{area}</li>)}</ul></div>
          </div>
        )}

        {!loading && !error && activeWorkflow === 'interview' && interview && (
          <div className="career-result-stack">
            <div className="career-section-card"><div className="career-section-heading"><BookOpenText size={16}/> <h3>Technical Questions</h3></div><ul className="career-check-list">{interview.technical_questions.map((question, index) => <li key={index}>{question}</li>)}</ul></div>
            <div className="career-section-card"><div className="career-section-heading"><Lightbulb size={16}/> <h3>Behavioral Questions</h3></div><ul className="career-check-list">{interview.behavioral_questions.map((question, index) => <li key={index}>{question}</li>)}</ul></div>
            <div className="career-section-card"><div className="career-section-heading"><BriefcaseBusiness size={16}/> <h3>Project Questions</h3></div><ul className="career-check-list">{interview.project_questions.length ? interview.project_questions.map((question, index) => <li key={index}>{question}</li>) : <li>No project entries were found for this profile.</li>}</ul></div>
            <div className="career-section-card"><div className="career-section-heading"><Target size={16}/> <h3>Follow-up Questions</h3></div><ul className="career-check-list">{interview.follow_up_questions.map((question, index) => <li key={index}>{question}</li>)}</ul></div>
          </div>
        )}

        {!loading && !error && activeWorkflow === 'guidance' && (
          <div className="career-result-stack">
            <div className="career-section-card"><div className="career-section-heading"><TrendingUp size={16}/> <h3>Career Guidance</h3></div><ul className="career-check-list"><li>Review your most relevant recent experience and tie it directly to your target role.</li><li>Prioritize 1–2 skill gaps at a time and focus on high-impact learning rather than broad, unfocused study.</li><li>Practice concise explanations for your strengths, trade-offs, and projects using the STAR framework.</li><li>Apply to roles that match your current profile while continuing to close the most important gaps.</li></ul></div>
          </div>
        )}

        {emptyState && !loading && !error && <div className="career-state-card empty"><Sparkles size={16} /> Upload a resume to unlock personalized career assistance.</div>}
      </div>

      <aside className="career-sidebar"><CareerAssistantChat /></aside>
    </section>
  </main></ProtectedRoute>
}
