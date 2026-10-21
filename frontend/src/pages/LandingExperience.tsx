import { ArrowRight, BriefcaseBusiness, Check, CirclePlay, FileSearch, MessageSquareText, ScanSearch, ShieldCheck, Sparkles, Users, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/common/Brand'
import './LandingPage.css'

const features = [
  { title: 'Resume Intelligence', description: 'Turn PDF and DOCX resumes into structured profiles with skills, experience, and education.', icon: <FileSearch size={21} />, tone: 'peach' },
  { title: 'Job Intelligence', description: 'Organize job descriptions into role details, responsibilities, and required or preferred skills.', icon: <BriefcaseBusiness size={21} />, tone: 'sage' },
  { title: 'AI Matching', description: 'Compare an applicant’s profile with a role across consistent, clearly defined score components.', icon: <Zap size={21} />, tone: 'yellow' },
  { title: 'Explainable Results', description: 'Review the evidence behind match scores, including skills, strengths, gaps, and source details.', icon: <ScanSearch size={21} />, tone: 'blue' },
  { title: 'Recruiter Workspace', description: 'Review applicants, manage shortlists, add notes, and compare candidates for a role.', icon: <Users size={21} />, tone: 'mint' },
  { title: 'AI Career Assistant', description: 'Explore resume suggestions, skill gaps, career guidance, and interview preparation.', icon: <MessageSquareText size={21} />, tone: 'coral' },
]

export default function LandingExperience() {
  return <main>
    <section className="hero-section">
      <div className="hero-grid">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> RESUME SCREENING &amp; CAREER INTELLIGENCE</div>
          <h1>TalentIQ<span>AI-Powered Resume Screening &amp; Career Intelligence</span></h1>
          <p className="hero-lede">Bring resume insights, role requirements, explainable matching, and career guidance into one clear workflow.</p>
          <div className="hero-actions">
            <Link to="/signup" className="button button-dark">Get started <ArrowRight size={17} /></Link>
            <Link to="/login" className="watch-link"><span><CirclePlay size={18} /></span> Log in</Link>
          </div>
          <div className="trust-row"><ShieldCheck size={19} /><span>Clear signals for human review. No automated hiring decisions.</span></div>
        </div>
        <div className="hero-visual" aria-label="TalentIQ product workflow preview">
          <div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="visual-glow"/>
          <div className="mini-card card-top"><span className="mini-icon"><Zap size={15} /></span><div><strong>AI Matching</strong><small>Role and profile signals</small></div><span className="green-check"><Check size={13} /></span></div>
          <div className="product-window">
            <div className="window-head"><div className="window-brand"><span className="window-dot"><Sparkles size={11} /></span> talentiq</div><div className="window-controls"><i/><i/><i/></div></div>
            <div className="window-body">
              <div className="window-title"><div><small>CONNECTED WORKFLOW</small><h3>Hiring and career tools</h3></div><span className="period">Explore</span></div>
              <div className="metric-row"><div className="metric"><small>Resume Intelligence</small><strong>PDF · DOCX</strong><span>Structured profiles</span></div><div className="metric"><small>Job Intelligence</small><strong>Role insights</strong><span>Required and preferred skills</span></div></div>
              <div className="candidate-head"><strong>Explore TalentIQ</strong><span>Six connected tools</span></div>
              {features.slice(2).map((feature) => <div className="candidate-row" key={feature.title}><div className="candidate-avatar"><span>{feature.icon}</span></div><div className="candidate-info"><strong>{feature.title}</strong><small>{feature.description.split('.')[0]}</small></div></div>)}
            </div>
          </div>
          <div className="mini-card card-bottom"><span className="scan-icon"><ShieldCheck size={17}/></span><div><strong>Decision support</strong><small>Reviewable evidence, human judgment</small></div></div>
          <div className="float-spark"><Sparkles size={19}/></div>
        </div>
      </div>
    </section>
    <section id="how-it-works" className="benefits-section">
      <div className="section-intro"><div className="eyebrow">ONE WORKSPACE, TWO CAREER PATHS</div><h2>Useful context for every next step.</h2><p>Recruiters can review role-aligned applicant evidence. Job seekers can understand their resume profile and plan what to improve.</p></div>
      <div id="why-talentiq" className="feature-grid">{features.map((feature, index) => <article className={`feature-card ${feature.tone}`} key={feature.title}><span className="feature-icon">{feature.icon}</span><small>{String(index + 1).padStart(2, '0')} — TALENTIQ</small><h3>{feature.title}</h3><p>{feature.description}</p></article>)}</div>
    </section>
    <section className="bottom-cta"><div><div className="eyebrow"><span className="eyebrow-dot"/> START WITH YOUR NEXT STEP</div><h2>Make space for clearer decisions.</h2><p>Choose the workflow that fits you: review applicants or build a stronger career profile.</p><div className="hero-actions"><Link to="/signup" className="button button-light">Get started <ArrowRight size={17}/></Link><Link to="/login" className="bottom-login">Log in</Link></div></div><div className="cta-stamp"><Sparkles size={29}/><span>PEOPLE FIRST.<br/>INSIGHTS IN CONTEXT.</span></div></section>
    <footer className="site-footer"><Brand/><span>TalentIQ · Resume Screening &amp; Career Intelligence</span><div><a href="/#why-talentiq">Our approach</a><Link to="/login">Log in</Link></div></footer>
  </main>
}