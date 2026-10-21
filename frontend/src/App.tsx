import { BrowserRouter, Link, NavLink, Route, Routes, Navigate } from 'react-router-dom'
import { ArrowRight, Menu, X } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import { Brand } from './components/common/Brand'
import { GuestOnly, ProtectedRoute } from './components/common/ProtectedRoute'
import LandingPage from './pages/LandingExperience'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import CareerAssistantPage from './pages/CareerAssistantPage'
import NotFoundPage from './pages/NotFoundPage'
import { LoadingScreen } from './components/common/LoadingScreen'
import { RecruiterLayout, RecruiterDashboardPage, RecruiterJobsPage, RecruiterJobDetailPage, RecruiterCandidatesPage, CandidateDetailPage, ShortlistPage, CompareCandidatesPage, RecruiterAnalyticsPage, RecruiterSettingsPage } from './pages/recruiter/RecruiterWorkspace'
const JobsPage = lazy(() => import('./pages/JobsPage'))
const CreateJobPage = lazy(() => import('./pages/CreateJobPage'))
const MatchingPage = lazy(() => import('./pages/MatchingPage'))
const CandidateExplanationPage = lazy(() => import('./pages/CandidateExplanationPage'))

const ResumeUploadPage = lazy(() => import('./pages/ResumeUploadPage'))

function PublicNav() {
  const [open, setOpen] = useState(false)
  return <header className="site-header"><div className="nav-wrap"><Brand /><button className="menu-toggle" aria-label="Toggle navigation" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button><nav className={open ? 'public-links open' : 'public-links'}><a href="/#how-it-works" onClick={() => setOpen(false)}>How it works</a><a href="/#why-talentiq" onClick={() => setOpen(false)}>Why TalentIQ</a><NavLink to="/login" onClick={() => setOpen(false)}>Log in</NavLink><Link className="button button-dark nav-cta" to="/signup" onClick={() => setOpen(false)}>Get started <ArrowRight size={15} /></Link></nav></div></header>
}

export default function App() {
  return <BrowserRouter><Routes>
    <Route path="/" element={<><PublicNav /><LandingPage /></>} />
    <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
    <Route path="/signup" element={<GuestOnly><SignupPage /></GuestOnly>} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
    <Route path="/auth/callback" element={<AuthCallbackPage />} />
    <Route path="/dashboard" element={<ProtectedRoute requiredRole="recruiter"><Navigate to="/recruiter" replace /></ProtectedRoute>} />
    <Route path="/recruiter" element={<ProtectedRoute requiredRole="recruiter"><RecruiterLayout /></ProtectedRoute>}>
      <Route index element={<RecruiterDashboardPage />} />
      <Route path="jobs" element={<RecruiterJobsPage />} />
      <Route path="jobs/new" element={<Suspense fallback={<LoadingScreen label="Loading job editor…"/>}><CreateJobPage /></Suspense>} />
      <Route path="jobs/:jobId" element={<RecruiterJobDetailPage />} />
      <Route path="jobs/:jobId/candidates" element={<RecruiterCandidatesPage />} />
      <Route path="jobs/:jobId/candidates/:candidateId" element={<CandidateDetailPage />} />
      <Route path="shortlist" element={<ShortlistPage />} />
      <Route path="compare" element={<CompareCandidatesPage />} />
      <Route path="analytics" element={<RecruiterAnalyticsPage />} />
      <Route path="settings" element={<RecruiterSettingsPage />} />
    </Route>
    <Route path="/jobs" element={<ProtectedRoute requiredRole="recruiter"><Suspense fallback={<LoadingScreen label="Loading job postings…"/>}><JobsPage /></Suspense></ProtectedRoute>} />
    <Route path="/jobs/new" element={<ProtectedRoute requiredRole="recruiter"><Suspense fallback={<LoadingScreen label="Loading job editor…"/>}><CreateJobPage /></Suspense></ProtectedRoute>} />
    <Route path="/jobs/:jobId/matching" element={<ProtectedRoute requiredRole="recruiter"><Suspense fallback={<LoadingScreen label="Loading matching tools…"/>}><MatchingPage /></Suspense></ProtectedRoute>} />
    <Route path="/jobs/:jobId/resumes/:resumeId/explanation" element={<ProtectedRoute requiredRole="recruiter"><Suspense fallback={<LoadingScreen label="Loading score explanation…"/>}><CandidateExplanationPage /></Suspense></ProtectedRoute>} />
    <Route path="/jobs/:jobId" element={<ProtectedRoute requiredRole="recruiter"><Suspense fallback={<LoadingScreen label="Loading job details…"/>}><JobsPage /></Suspense></ProtectedRoute>} />
    <Route path="/career-assistant" element={<CareerAssistantPage />} />
    <Route path="/resumes/upload" element={<ProtectedRoute requiredRole="job_seeker"><Suspense fallback={<LoadingScreen label="Loading resume tools…"/>}><ResumeUploadPage /></Suspense></ProtectedRoute>} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes></BrowserRouter>
}
