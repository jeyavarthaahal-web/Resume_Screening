import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import CandidateExplanationPage from './CandidateExplanationPage'
import { generateRankingExplanation, getRankingExplanation } from '../services/rankingService'
import type { RankingExplanation } from '../types/ranking'

vi.mock('../services/rankingService', () => ({
  getRankingExplanation: vi.fn(),
  generateRankingExplanation: vi.fn(),
}))

const fixture: RankingExplanation = {
  job_id: 'job-1', resume_id: 'resume-1', candidate_id: 'candidate-1', overall_score: 84.98,
  score_breakdown: {
    semantic: { score: 86.2, weight: .4, weighted_contribution: 34.48 },
    skills: { score: 80, weight: .25, weighted_contribution: 20 },
    experience: { score: 90, weight: .15, weighted_contribution: 13.5 },
    education: { score: 100, weight: .1, weighted_contribution: 10 },
    projects: { score: 70, weight: .1, weighted_contribution: 7 },
  },
  matched_skills: [{ name: 'Python', importance: 'required', status: 'matched', resume_skill: 'Python' }],
  partial_skills: [{ name: 'React', importance: 'required', status: 'partial', resume_skill: 'Angular' }],
  missing_skills: [{ name: 'AWS', importance: 'preferred', status: 'missing' }],
  strengths: [{ title: 'Required skill alignment', description: 'Python appears in extracted skills.', evidence: [{ type: 'skill', source: 'resume', text: 'Python' }] }],
  gaps: [{ title: 'AWS not identified', description: 'AWS is preferred and was not identified.', severity: 'preferred', status: 'missing', evidence: [{ type: 'skill', source: 'job', text: 'AWS (preferred)' }] }],
  evidence: [
    { type: 'skill', source: 'resume', text: 'Python, Angular' },
    { type: 'skill', source: 'job', text: 'AWS (preferred)', related_requirement: 'AWS' },
  ],
  explanation: 'The persisted score is 84.98. Python is matched and AWS was not identified.',
  experience_context: { candidate_years: 4, minimum_years: 3, maximum_years: null, status: 'matched' },
  education_context: { candidate: ['B.Tech in AI'], requirement: ["Bachelor's in AI"], status: 'matched' },
  relevant_projects: [{ project_name: 'ML screening tool', relevant_technologies: ['Python'], related_job_requirements: ['Python'], evidence: { type: 'project', source: 'resume', text: 'ML screening tool — Python' } }],
  data_quality: 'complete', data_quality_note: '5 of 5 structured sections contain data.', generated_at: '2026-09-27T00:00:00Z',
}

function renderPage() {
  return render(<MemoryRouter initialEntries={['/jobs/job-1/resumes/resume-1/explanation']}><Routes><Route path="/jobs/:jobId/resumes/:resumeId/explanation" element={<CandidateExplanationPage/>}/></Routes></MemoryRouter>)
}

describe('CandidateExplanationPage', () => {
  afterEach(() => cleanup())
  beforeEach(() => { vi.clearAllMocks() })

  it('shows loading state while the explanation request is pending', () => {
    vi.mocked(getRankingExplanation).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading score explanation…')).toBeInTheDocument()
  })

  it('renders the persisted score breakdown, skill groups, findings, and source evidence', async () => {
    vi.mocked(getRankingExplanation).mockResolvedValue(fixture)
    renderPage()
    expect(await screen.findByText('84.98')).toBeInTheDocument()
    expect(screen.getByText('Score breakdown')).toBeInTheDocument()
    expect(screen.getAllByText('Python').length).toBeGreaterThan(0)
    expect(screen.getByText('Resume lists Angular')).toBeInTheDocument()
    expect(screen.getByText('AWS')).toBeInTheDocument()
    expect(screen.getByText('Required skill alignment')).toBeInTheDocument()
    expect(screen.getByText('AWS not identified')).toBeInTheDocument()
    expect(screen.getByText('ML screening tool')).toBeInTheDocument()
    expect(screen.getByText('Source evidence')).toBeInTheDocument()
  })

  it('refreshes the explanation from the saved match and updates the displayed score', async () => {
    vi.mocked(getRankingExplanation).mockResolvedValue(fixture)
    vi.mocked(generateRankingExplanation).mockResolvedValue({ ...fixture, overall_score: 85.12 })
    renderPage()
    await screen.findByText('84.98')
    fireEvent.click(screen.getByRole('button', { name: /refresh explanation/i }))
    expect(await screen.findByText('85.12')).toBeInTheDocument()
    expect(generateRankingExplanation).toHaveBeenCalledWith('job-1', 'resume-1')
  })

  it('shows a clear API error state', async () => {
    vi.mocked(getRankingExplanation).mockRejectedValue(new Error('No Task 6 matching result exists.'))
    renderPage()
    expect(await screen.findByText('Explanation unavailable')).toBeInTheDocument()
    expect(screen.getByText('No Task 6 matching result exists.')).toBeInTheDocument()
  })

  it('renders empty states for unsupported findings and source evidence', async () => {
    vi.mocked(getRankingExplanation).mockResolvedValue({
      ...fixture, matched_skills: [], partial_skills: [], missing_skills: [], strengths: [], gaps: [], evidence: [], relevant_projects: [],
      experience_context: { candidate_years: null, minimum_years: null, maximum_years: null, status: 'not_identified' },
      education_context: { candidate: [], requirement: [], status: 'not_identified' }, data_quality: 'limited',
    })
    renderPage()
    expect(await screen.findByText('No exact or normalized skill matches were identified.')).toBeInTheDocument()
    expect(screen.getByText('No specific gap was identified in the available structured information.')).toBeInTheDocument()
    expect(screen.getByText('No structured resume evidence was available.')).toBeInTheDocument()
  })
})
