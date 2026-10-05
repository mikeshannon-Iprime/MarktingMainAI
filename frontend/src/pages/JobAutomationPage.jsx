import { startTransition, useDeferredValue, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Bookmark,
  BookmarkCheck,
  Briefcase,
  Calendar,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Copy,
  Cpu,
  Download,
  ExternalLink,
  Eye,
  FileSearch,
  FileText,
  Globe,
  Linkedin,
  LoaderCircle,
  MessageSquare,
  Save,
  Search,
  Send,
  Trash2,
  TrendingUp,
  Upload,
  UserCircle2,
  WandSparkles,
  X,
} from 'lucide-react'

import {
  activateUserResume,
  addCarrierItem,
  addPortalItem,
  analyzeJob,
  applyLinkedInJob,
  applyToJobs,
  deleteCarrierItem,
  deletePortalItem,
  deleteUserResume,
  getJobApplicationStatus,
  getTailoredResume,
  importCarrierItems,
  importPortalItems,
  listJobApplications,
  parseResumeFile,
  previewApplicationAutofill,
  refreshJobDescription,
  runAutoApply,
  runJobSearch,
  saveAutomationSettings,
  saveJobItem,
  saveJobProfile,
  saveSearchConfig,
  saveTailoredResume,
  scheduleJobApplicationFollowUp,
  searchLinkedInJobs,
  tailorResumeForJob,
  updateJobApplication,
} from '../api/client'
import {
  downloadTextFile,
  getCompanyInitials,
  getPortalInitials,
  LINKEDIN_DATE_POSTED,
  LINKEDIN_EXPERIENCE_LEVELS,
  LINKEDIN_SORT_OPTIONS,
  mapYearsToExperienceText,
  PROFILE_EMPLOYMENT_OPTIONS,
  PROFILE_VISA_OPTIONS,
  PROFILE_WORK_MODE_OPTIONS,
  readImportFile,
  SEARCH_EXPERIENCE_OPTIONS,
  SEARCH_RADIUS_OPTIONS,
  SEARCH_REPEAT_OPTIONS,
  sortLinkedInJobs,
  US_TIMEZONES,
  countSearchConfigItems,
  formatMatchSource,
  formatPipelineMatchSource,
  MATCH_POLICY,
} from '../utils/jobAutomationHelpers'
import { isEmail, isHttpUrl, isNonEmpty, isPhone } from '../utils/validators'
import { getErrorMessage } from '../utils/logger'

const panelTabs = [
  { key: 'profile', label: 'My Profile', shortLabel: 'Profile', hint: 'Resume & details', icon: UserCircle2, accent: 'cobalt' },
  { key: 'search', label: 'Job Search', shortLabel: 'Search', hint: 'Keywords & filters', icon: Search, accent: 'teal' },
  { key: 'portals', label: 'Portals', shortLabel: 'Portals', hint: 'Board connections', icon: Globe, accent: 'amber' },
  { key: 'results', label: 'Results', shortLabel: 'Results', hint: 'Matched roles', icon: Briefcase, accent: 'green' },
  { key: 'analyzer', label: 'CV Analyzer', shortLabel: 'Analyzer', hint: 'Fit & tailoring', icon: Cpu, accent: 'violet' },
  { key: 'linkedin', label: 'LinkedIn', shortLabel: 'LinkedIn', hint: 'Live job feed', icon: Linkedin, accent: 'blue' },
  { key: 'tracker', label: 'Tracker', shortLabel: 'Tracker', hint: 'Applications', icon: FileSearch, accent: 'rose' },
]

const wizardTabKeys = ['profile', 'search', 'portals', 'results', 'analyzer', 'linkedin', 'tracker']

const trackerTabConfig = [
  { key: 'all', label: 'All Applications', icon: FileSearch },
  { key: 'interviews', label: 'Interviews', icon: Calendar },
  { key: 'actionNeeded', label: 'Action Needed', icon: AlertCircle },
  { key: 'stats', label: 'Statistics', icon: TrendingUp },
]

const EMPTY_APPLICATIONS = {
  all: [],
  interviews: [],
  actionNeeded: [],
  stats: {
    applied: 0,
    interviews: 0,
    actionNeeded: 0,
    conversion: 0,
    responseRate: 0,
    avgMatchScore: 0,
    avgResponseTime: '—',
    bestPlatform: '—',
    underReview: 0,
    totalTracked: 0,
  },
}

const TRACKER_STATUS_OPTIONS = [
  'Applying',
  'Applied',
  'Action Needed',
  'Interview',
  'Offer',
  'Tailoring',
  'Rejected',
  'Failed',
]

function isInterviewStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  return normalized === 'interview' || normalized === 'offer'
}

function isActionNeededStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  return normalized === 'action needed' || normalized === 'tailoring' || normalized === 'failed'
}

function isSubmittedStatus(status) {
  const normalized = String(status || '').trim().toLowerCase()
  return ['applied', 'interview', 'offer', 'applying'].includes(normalized)
}

function computeApplicationStats(rows = []) {
  const interviews = rows.filter((item) => isInterviewStatus(item.status))
  const actionNeeded = rows.filter((item) => isActionNeededStatus(item.status))
  const submitted = rows.filter((item) => isSubmittedStatus(item.status))
  const underReview = rows.filter((item) => String(item.status || '').toLowerCase() === 'applied')
  const matchValues = rows.map((item) => item.match).filter((value) => value != null && Number.isFinite(Number(value)))
  const avgMatchScore = matchValues.length
    ? Math.round(matchValues.reduce((sum, value) => sum + Number(value), 0) / matchValues.length)
    : 0
  const portalCounts = {}
  rows.forEach((item) => {
    const portal = item.portal || 'Direct'
    portalCounts[portal] = (portalCounts[portal] || 0) + 1
  })
  const bestPlatform = Object.keys(portalCounts).length
    ? Object.entries(portalCounts).sort((a, b) => b[1] - a[1])[0][0]
    : '—'
  const responseRate = submitted.length ? Math.round((interviews.length / submitted.length) * 100) : 0
  return {
    applied: submitted.length || rows.length,
    underReview: underReview.length,
    interviews: interviews.length,
    actionNeeded: actionNeeded.length,
    conversion: responseRate,
    responseRate,
    avgMatchScore,
    avgResponseTime: '—',
    bestPlatform,
    totalTracked: rows.length,
  }
}

function rebuildApplicationsFromRows(rows = []) {
  const all = Array.isArray(rows) ? rows : []
  return {
    all,
    interviews: all.filter((item) => isInterviewStatus(item.status)),
    actionNeeded: all.filter((item) => isActionNeededStatus(item.status)),
    stats: computeApplicationStats(all),
  }
}

const EMPTY_PROFILE = {
  name: '',
  email: '',
  phone: '',
  location: '',
  linkedin: '',
  portfolio: '',
  visaStatus: '',
  yearsExperience: '',
  workMode: '',
  employmentType: '',
  salaryMin: '',
  salaryMax: '',
  resumeFileName: '',
  resumeSummary: '',
  resumeSkills: [],
  jobTitles: [],
}

const EMPTY_SEARCH_CONFIG = {
  titles: [],
  skills: [],
  locations: [],
  radius: '25',
  experienceLevel: '',
  salaryMin: '',
  salaryMax: '',
  postedWithin: '',
  employmentType: 'all',
  workMode: '',
  excludeKeywords: [],
  sortBy: 'match',
}

const CUSTOM_SEARCH_SCHEDULE_OPTION = '__custom__'
const DEFAULT_CUSTOM_SCHEDULE_MINUTES = 180

const EMPTY_AUTOMATION = {
  autoApplyEnabled: false,
  discoverIntervalHours: 3,
  maxApplications: 20,
  onlyEasyApply: false,
  sendDailyDigest: false,
  matchThreshold: MATCH_POLICY.applyMin,
  tailorCv: true,
  alerts: false,
}

const EMPTY_ANALYSIS_RESULT = {
  selectedJobId: null,
  score: null,
  summary: '',
  hits: [],
  misses: [],
  missingKeywords: [],
  strengths: [],
  gaps: [],
  skillGaps: [],
  recommendations: [],
  suggestions: [],
  jobDescription: '',
  experienceMatch: '',
  titleMatch: '',
  tailoredScore: null,
  matchSource: null,
  platform: null,
  sourceUrl: null,
}

const ADJUSTMENTS_MARKER = '=== ROLE-ALIGNED ADJUSTMENTS'
let toastSequence = 0

function appendSuggestionToTailoredDraft(content, suggestion) {
  const text = String(suggestion || '').trim()
  if (!text) {
    return String(content || '')
  }
  const body = String(content || '').trimEnd()
  const bullet = `- ${text}`
  if (body.includes(bullet) || body.includes(text)) {
    return body.endsWith('\n') ? body : `${body}\n`
  }
  if (body.includes(ADJUSTMENTS_MARKER)) {
    return `${body}\n${bullet}\n`
  }
  if (!body) {
    return `${ADJUSTMENTS_MARKER} ===\n${bullet}\n`
  }
  return `${body}\n\n${ADJUSTMENTS_MARKER} ===\n${bullet}\n`
}

function getCustomScheduleMinutes(repeatEveryValue) {
  const match = String(repeatEveryValue ?? '').match(/^custom:\s*(\d+)\s*(minute|minutes|hour|hours|hr|hrs|h|m)?$/i)
  if (!match) {
    return null
  }
  const amount = Number(match[1])
  if (!Number.isFinite(amount) || amount <= 0) {
    return null
  }
  const unit = String(match[2] ?? 'minutes').toLowerCase()
  if (unit.startsWith('h') || unit.startsWith('hr')) {
    return amount * 60
  }
  return amount
}

function parseScheduleIntervalMs(repeatEveryValue) {
  const customMinutes = getCustomScheduleMinutes(repeatEveryValue)
  if (customMinutes != null) {
    return customMinutes * 60 * 1000
  }

  const normalized = String(repeatEveryValue ?? '').trim().toLowerCase()
  if (!normalized) {
    return null
  }
  if (normalized.includes('once daily') || normalized.includes('daily')) {
    return 24 * 60 * 60 * 1000
  }
  if (normalized.includes('every hour')) {
    return 60 * 60 * 1000
  }
  const hoursMatch = normalized.match(/every\s+(\d+)\s*hours?/)
  if (hoursMatch) {
    return Number(hoursMatch[1]) * 60 * 60 * 1000
  }
  const minutesMatch = normalized.match(/every\s+(\d+)\s*minutes?/)
  if (minutesMatch) {
    return Number(minutesMatch[1]) * 60 * 1000
  }
  return null
}

function normalizeApplications(applications) {
  const source = applications ?? {}
  const rows = Array.isArray(source.all)
    ? source.all
    : (Array.isArray(source) ? source : [])
  const rebuilt = rebuildApplicationsFromRows(rows)
  if (source.stats && typeof source.stats === 'object') {
    rebuilt.stats = {
      ...rebuilt.stats,
      avgResponseTime: source.stats.avgResponseTime || rebuilt.stats.avgResponseTime,
      bestPlatform: source.stats.bestPlatform || rebuilt.stats.bestPlatform,
    }
  }
  return rebuilt
}

function normalizeProfile(profile) {
  return {
    ...EMPTY_PROFILE,
    ...(profile ?? {}),
    resumeSkills: Array.isArray(profile?.resumeSkills) ? profile.resumeSkills : [],
    jobTitles: Array.isArray(profile?.jobTitles) ? profile.jobTitles : [],
  }
}

function normalizeSearchConfig(searchConfig) {
  return {
    ...EMPTY_SEARCH_CONFIG,
    ...(searchConfig ?? {}),
    titles: Array.isArray(searchConfig?.titles) ? searchConfig.titles : [],
    skills: Array.isArray(searchConfig?.skills) ? searchConfig.skills : [],
    locations: Array.isArray(searchConfig?.locations) ? searchConfig.locations : [],
    excludeKeywords: Array.isArray(searchConfig?.excludeKeywords) ? searchConfig.excludeKeywords : [],
  }
}

function normalizeAutomation(automation) {
  return {
    ...EMPTY_AUTOMATION,
    ...(automation ?? {}),
  }
}

function normalizeAnalysisResult(analysis) {
  const hits = Array.isArray(analysis?.hits) ? analysis.hits : []
  const misses = Array.isArray(analysis?.misses)
    ? analysis.misses
    : (Array.isArray(analysis?.missingKeywords) ? analysis.missingKeywords : [])
  const recommendations = Array.isArray(analysis?.recommendations) ? analysis.recommendations : []
  const suggestions = Array.isArray(analysis?.suggestions) ? analysis.suggestions : recommendations
  return {
    ...EMPTY_ANALYSIS_RESULT,
    ...(analysis ?? {}),
    hits,
    misses,
    missingKeywords: Array.isArray(analysis?.missingKeywords) ? analysis.missingKeywords : misses,
    skillGaps: Array.isArray(analysis?.skillGaps) ? analysis.skillGaps : [],
    strengths: Array.isArray(analysis?.strengths) ? analysis.strengths : [],
    gaps: Array.isArray(analysis?.gaps) ? analysis.gaps : [],
    recommendations: recommendations.length ? recommendations : suggestions,
    suggestions: suggestions.length ? suggestions : recommendations,
  }
}

function getTrackerStatusTone(status = '') {
  const normalized = status.toLowerCase()
  if (normalized.includes('interview') || normalized.includes('offer')) return 'interview'
  if (normalized.includes('reject') || normalized.includes('fail')) return 'rejected'
  if (normalized.includes('tailor')) return 'review'
  if (normalized.includes('review')) return 'review'
  if (normalized.includes('action')) return 'action'
  if (normalized.includes('applying')) return 'applying'
  if (normalized.includes('applied')) return 'applied'
  return 'default'
}

function isAppliedApplicationRow(row) {
  if (!row) return false
  if (row.status === 'Applied') return true
  return ['applied', 'demo'].includes(row.attemptStatus)
}

function getResultApplyState(applications, job) {
  const rows = applications?.all ?? []
  if (!job?.id || !rows.length) {
    return null
  }

  const matches = rows.filter((row) => {
    if (row.jobResultId != null && Number(row.jobResultId) === Number(job.id)) {
      return true
    }
    return (
      row.role === job.role
      && row.company === job.company
      && (!row.portal || !job.portalName || row.portal === job.portalName)
    )
  })
  if (!matches.length) {
    return null
  }

  if (matches.some(isAppliedApplicationRow)) {
    return { label: 'Applied', tone: 'applied', applied: true, busy: false }
  }
  if (matches.some((row) => row.status === 'Rejected' || row.attemptStatus === 'rejected')) {
    return { label: 'Rejected', tone: 'rejected', applied: false, busy: false }
  }
  if (matches.some((row) => row.status === 'Tailoring' || row.attemptStatus === 'tailored')) {
    return { label: 'Tailored CV', tone: 'review', applied: false, busy: false }
  }
  if (matches.some((row) => row.status === 'Failed' || row.attemptStatus === 'failed')) {
    return { label: 'Failed', tone: 'rejected', applied: false, busy: false }
  }
  if (matches.some((row) => row.status === 'Action Needed' || row.attemptStatus === 'needs_attention')) {
    return { label: 'Action Needed', tone: 'action', applied: false, busy: false }
  }
  if (matches.some((row) => (
    row.status === 'Applying'
    || ['queued', 'filling', 'awaiting_submit'].includes(row.attemptStatus)
  ))) {
    return { label: 'Applying', tone: 'applying', applied: false, busy: true }
  }

  const latest = matches[0]
  return {
    label: latest.status || 'Tracked',
    tone: getTrackerStatusTone(latest.status),
    applied: false,
    busy: false,
  }
}

const presetTitles = ['Java Developer', 'Python Developer', 'Data Engineer', 'Full Stack Developer']

function normalizeLabel(value) {
  return value.trim().toLowerCase()
}

function collectResultKeywords(profile, searchConfig, jobs = [], parsedMatches = []) {
  const candidates = [
    ...parsedMatches,
    ...(searchConfig?.requiredSkills ?? []),
    ...(searchConfig?.optionalSkills ?? []),
    ...(profile?.resumeSkills ?? []),
    ...jobs.flatMap((job) => job.skills ?? []),
  ]
  const seen = new Set()
  return candidates
    .map((keyword) => String(keyword ?? '').trim())
    .filter((keyword) => {
      const normalized = keyword.toLowerCase()
      if (!normalized || seen.has(normalized)) {
        return false
      }
      seen.add(normalized)
      return true
    })
    .slice(0, 30)
}

function formatTitle(value) {
  return value
    .split(' ')
    .filter(Boolean)
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ')
}

function TagEditor({ label, items, placeholder, onAdd, onRemove }) {
  const [draft, setDraft] = useState('')

  const commit = () => {
    if (!draft.trim()) {
      return
    }
    onAdd(draft)
    setDraft('')
  }

  return (
    <div className="page-stack dense">
      <label>{label}</label>
      <div className="tag-editor-shell">
        <div className="chip-wrap inset">
          {items.map((item) => (
            <span key={item} className="chip-button tag-chip">
              {item}
              <button type="button" className="chip-dismiss" onClick={() => onRemove(item)} aria-label={`Remove ${item}`}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
        <div className="tag-editor-row">
          <input
            value={draft}
            placeholder={placeholder}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ',') {
                event.preventDefault()
                commit()
              }
            }}
          />
          <button className="secondary-button" type="button" onClick={commit}>Add</button>
        </div>
      </div>
    </div>
  )
}

function AutomationToggle({ label, hint, enabled, onToggle }) {
  return (
    <button
      type="button"
      className="toggle-row toggle-button ja-automation-toggle"
      role="switch"
      aria-checked={enabled}
      onClick={onToggle}
    >
      <div className="toggle-copy">
        <strong>{label}</strong>
        <p>{hint}</p>
      </div>
      <span className={`toggle-switch${enabled ? ' on' : ''}`} aria-hidden="true">
        <span className="toggle-knob" />
      </span>
    </button>
  )
}

function getEffectiveSearchTitles(profile, searchConfig) {
  const searchTitles = searchConfig?.titles ?? []
  if (searchTitles.length) {
    return searchTitles
  }
  return profile?.jobTitles ?? []
}

function serializeMaxApplications(value, fallback = 20) {
  if (value === '' || value === null || value === undefined) {
    return fallback
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : fallback
}

function normalizeAutomationForSave(settings) {
  return {
    ...settings,
    maxApplications: serializeMaxApplications(settings.maxApplications),
  }
}


function AutomationSettingsPanel({
  automation,
  busyAction,
  updateAutomation,
  ensureCanModify,
  saveAutomationSettings,
  pushNotice,
  handleAutoApplyToggle,
  runAutoApplyAction,
}) {
  const persistAutomationField = async (nextAutomation) => {
    if (!ensureCanModify('Automation settings')) {
      return
    }
    try {
      const saved = await saveAutomationSettings(normalizeAutomationForSave(nextAutomation))
      if (saved.automation) {
        return saved.automation
      }
    } catch {
      pushNotice('Failed to save automation settings.', 'error')
    }
    return null
  }

  return (
    <article className="glass-card ja-automation-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Automation</p>
          <h4>Auto-apply settings</h4>
        </div>
      </div>

      <div className="ja-automation-toggles">
        <AutomationToggle
          label="Auto-Apply to Matching Jobs"
          hint={`Scrapes all portals (24h + 48h). ≥${MATCH_POLICY.applyMin}% apply · ${MATCH_POLICY.tailorMin}–${MATCH_POLICY.applyMin - 1}% tailor CV · <${MATCH_POLICY.rejectBelow}% reject`}
          enabled={automation.autoApply}
          onToggle={handleAutoApplyToggle}
        />
      </div>

      <div className="ja-match-policy-card" style={{ marginBottom: 12, fontSize: 13, lineHeight: 1.45 }}>
        <strong>Match routing policy</strong>
        <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          <li><strong>≥ {MATCH_POLICY.applyMin}%</strong> — auto-apply in background</li>
          <li><strong>{MATCH_POLICY.tailorMin}–{MATCH_POLICY.applyMin - 1}%</strong> — tailor CV to JD</li>
          <li><strong>&lt; {MATCH_POLICY.rejectBelow}%</strong> — reject application</li>
          <li>Portal scrape windows: <strong>24 hours</strong> and <strong>48 hours</strong></li>
        </ul>
      </div>

      <label className="ja-automation-field">
        Minimum match score for auto-apply (floor {MATCH_POLICY.applyMin}%)
        <input
          type="range"
          className="match-threshold-slider"
          min={MATCH_POLICY.applyMin}
          max="95"
          value={Math.max(MATCH_POLICY.applyMin, automation.matchThreshold ?? MATCH_POLICY.applyMin)}
          onChange={async (event) => {
            const value = Number(event.target.value)
            const nextAutomation = { ...automation, matchThreshold: value }
            updateAutomation('matchThreshold', value)
            await persistAutomationField(nextAutomation)
          }}
        />
        <div className="match-threshold-value">{Math.max(MATCH_POLICY.applyMin, automation.matchThreshold ?? MATCH_POLICY.applyMin)}%</div>
      </label>

      <label className="ja-automation-field">
        Max applications per day
        <input
          type="number"
          min="1"
          max="100"
          value={automation.maxApplications === '' ? '' : automation.maxApplications}
          onChange={(event) => {
            const raw = event.target.value
            if (raw === '') {
              updateAutomation('maxApplications', '')
              return
            }
            const value = Number(raw)
            if (Number.isFinite(value)) {
              updateAutomation('maxApplications', value)
            }
          }}
          onBlur={async () => {
            await persistAutomationField(automation)
          }}
        />
      </label>

      <div className="ja-automation-toggles">
        <AutomationToggle
          label="Send Application Alerts"
          hint="Email & SMS notifications"
          enabled={automation.alerts}
          onToggle={() => updateAutomation('alerts', !automation.alerts)}
        />
        <AutomationToggle
          label="Tailor CV Automatically"
          hint="AI rewrites resume for each job"
          enabled={automation.tailorCv}
          onToggle={() => updateAutomation('tailorCv', !automation.tailorCv)}
        />
        <AutomationToggle
          label="Scheduled Discovery"
          hint="Run recurring searches through the day"
          enabled={automation.scheduleEnabled}
          onToggle={() => updateAutomation('scheduleEnabled', !automation.scheduleEnabled)}
        />
      </div>

      <div className="ja-automation-schedule form-grid two-columns">
        <label className="ja-automation-field">
          Scheduled time
          <input
            type="time"
            value={automation.scheduleTime ?? '09:00'}
            onChange={(event) => updateAutomation('scheduleTime', event.target.value)}
          />
        </label>
        <label className="ja-automation-field">
          Time zone
          <select
            value={automation.scheduleTimezone ?? 'America/New_York'}
            onChange={(event) => updateAutomation('scheduleTimezone', event.target.value)}
          >
            {US_TIMEZONES.map((zone) => (
              <option key={zone.value} value={zone.value}>{zone.label}</option>
            ))}
          </select>
        </label>
        <label className="ja-automation-field full-width">
          Search schedule
          <input
            value={automation.scheduleLabel ?? 'Every 2 hours between 08:00 and 18:00'}
            onChange={(event) => updateAutomation('scheduleLabel', event.target.value)}
          />
        </label>
      </div>

      <button className="secondary-button" type="button" disabled={busyAction === 'autoApply'} onClick={runAutoApplyAction}>
        Run auto apply now
      </button>
    </article>
  )
}

function getPostedDays(postedLabel) {
  const numeric = Number.parseInt(postedLabel, 10)

  if (Number.isFinite(numeric)) {
    return numeric
  }

  return 999
}

function sortJobsByOption(rows, sortKey) {
  const sorted = [...rows]
  if (sortKey === 'match') {
    sorted.sort((left, right) => right.match - left.match)
  } else if (sortKey === 'recent') {
    sorted.sort((left, right) => getPostedDays(left.posted) - getPostedDays(right.posted))
  } else if (sortKey === 'company') {
    sorted.sort((left, right) => left.company.localeCompare(right.company))
  } else if (sortKey === 'rate') {
    sorted.sort((left, right) => {
      const extractRate = (r) => {
        const m = String(r?.rate ?? '').match(/\d[\d,]+/)
        return m ? Number(m[0].replace(/,/g, '')) : 0
      }
      return extractRate(right) - extractRate(left)
    })
  }
  return sorted
}

function isGenericEmploymentType(value) {
  const selected = String(value ?? '').trim().toLowerCase()
  return !selected || selected === 'both' || selected === 'all' || selected === 'any' || selected.includes('both')
}

function normalizeEmploymentCategory(value) {
  const raw = String(value ?? '').trim().toLowerCase()
  if (isGenericEmploymentType(raw)) {
    return 'both'
  }
  if (raw.includes('c2h') || raw.includes('contract to hire') || raw.includes('contract-to-hire') || raw.includes('contracttohire')) {
    return 'c2h'
  }
  if (raw.includes('c2c') || raw.includes('corp to corp') || raw.includes('corp-to-corp')) {
    return 'c2c'
  }
  if (raw.includes('w2') || raw.includes('w-2')) {
    return 'w2'
  }
  if (raw.includes('full') && (raw.includes('time') || raw.includes('full-time') || raw === 'full time' || raw === 'fulltime')) {
    return 'full_time'
  }
  if (raw === 'full' || raw === 'fulltime' || raw === 'full-time') {
    return 'full_time'
  }
  if (raw.includes('contract')) {
    return 'contract'
  }
  return raw
}

function formatEmploymentTypeLabel(jobType) {
  const category = normalizeEmploymentCategory(jobType)
  const labels = {
    both: 'Both Contract & Full Time',
    c2h: 'Contract to Hire',
    c2c: 'Contract (C2C)',
    w2: 'Contract (W2)',
    full_time: 'Full Time',
    contract: 'Contract',
  }
  return labels[category] || String(jobType || 'Unknown').trim() || 'Unknown'
}

function resolveEmploymentType(searchConfig, profile) {
  const searchType = String(searchConfig?.employmentType ?? '').trim()
  const profileType = String(profile?.employmentType ?? '').trim()
  if (!isGenericEmploymentType(profileType) && isGenericEmploymentType(searchType)) {
    return profileType
  }
  if (!isGenericEmploymentType(searchType)) {
    return searchType
  }
  return profileType || searchType || 'Both Contract & Full Time'
}

function matchesEmploymentType(selectedType, jobType) {
  const selected = normalizeEmploymentCategory(selectedType)
  const job = normalizeEmploymentCategory(jobType)
  if (selected === 'both') {
    return true
  }
  // Generic "Contract" accepts any contract-family posting.
  if (selected === 'contract') {
    return job === 'contract' || job === 'c2c' || job === 'w2' || job === 'c2h'
  }
  // Strict: Contract to Hire ↔ C2H only; Full Time ↔ full time only; etc.
  return selected === job
}

function formatPostedAgeLabel(postedLabel) {
  const label = String(postedLabel ?? '').trim()
  if (!label) {
    return 'Unknown age'
  }
  if (/ago|hour|hr|day|\bh\b|\bd\b/i.test(label)) {
    return label.toLowerCase().includes('ago') ? label : `${label} ago`
  }
  const value = Number.parseInt(label, 10)
  if (!Number.isFinite(value)) {
    return label
  }
  // Backend stores plain numbers as days (0/1/2…).
  if (value <= 0) {
    return 'Just now'
  }
  if (value === 1) {
    return '1d ago'
  }
  return `${value}d ago`
}

function getMatchRouteBand(matchScore) {
  const score = Number(matchScore) || 0
  if (score >= MATCH_POLICY.applyMin) {
    return 'apply'
  }
  if (score >= MATCH_POLICY.tailorMin) {
    return 'tailor'
  }
  return 'reject'
}

function getMatchRouteLabel(band) {
  if (band === 'apply') {
    return `≥${MATCH_POLICY.applyMin}% auto-apply`
  }
  if (band === 'tailor') {
    return `${MATCH_POLICY.tailorMin}–${MATCH_POLICY.applyMin - 1}% tailor CV`
  }
  return `<${MATCH_POLICY.rejectBelow}% reject`
}

function getFilteredJobs(results, filters, employmentType, { maxPostedHours = 48 } = {}) {
  const queryTerms = String(filters.query ?? '')
    .split(/[,\n]+/)
    .map(normalizeLabel)
    .filter(Boolean)

  const rows = results.filter((job) => {
    const searchText = [job.role, job.company, job.location, ...(job.skills ?? [])].join(' ').toLowerCase()
    const matchesQuery = !queryTerms.length || queryTerms.some((query) => searchText.includes(query))
    const matchesType = matchesEmploymentType(employmentType, job.type)
    const matchesFreshness = isPostedWithinRecentWindow(job.posted, maxPostedHours)
    const excludeHit = (filters.excludeKeywords ?? []).some((kw) =>
      kw.trim() && searchText.includes(kw.trim().toLowerCase())
    )
    return matchesQuery && matchesType && matchesFreshness && !excludeHit
  })

  return sortJobsByOption(rows, filters.sort)
}

function isPostedWithinRecentWindow(postedLabel, maxHours = 48) {
  const label = String(postedLabel ?? '').trim().toLowerCase()
  if (!label) {
    return false
  }
  const match = label.match(/(\d+)/)
  if (!match) {
    return false
  }
  const value = Number(match[1])
  if (!Number.isFinite(value)) {
    return false
  }
  if (label.includes('hour') || label.includes('hr') || /h\s*ago/.test(label) || /\d+h\b/.test(label)) {
    return value <= maxHours
  }
  if (label.includes('day') || /d\s*ago/.test(label) || /\d+d\b/.test(label)) {
    return value * 24 <= maxHours
  }
  // Plain numeric values from scrapers/seed data are days (0/1/2…).
  return value * 24 <= maxHours
}

function isPostedWithin24Hours(postedLabel) {
  return isPostedWithinRecentWindow(postedLabel, 48)
}

function bumpApplicationsState(applications, jobIds, fallbackJobs, apiRows = []) {
  const safeApplications = normalizeApplications(applications)
  const createdRows = apiRows.length
    ? apiRows.map((row) => ({
        id: row.id,
        jobResultId: row.jobResultId ?? null,
        role: row.role,
        company: row.company,
        status: row.status || 'Applying',
        stage: row.stage || 'Queued for portal apply',
        updated: row.updated || 'Just now',
        date: row.date || new Date().toISOString().slice(0, 10),
        action: row.action || 'Watch portal browser',
        portal: row.portal ?? 'Direct',
        match: row.match ?? null,
        postingUrl: row.postingUrl ?? '',
        attemptStatus: row.attemptStatus || 'queued',
        attemptDetail: row.attemptDetail || '',
        confirmationUrl: row.confirmationUrl || null,
      }))
    : fallbackJobs
        .filter((job) => jobIds.includes(job.id))
        .map((job) => ({
          jobResultId: job.id,
          role: job.role,
          company: job.company,
          status: 'Applying',
          stage: 'Queued for portal apply',
          updated: 'Just now',
          date: new Date().toISOString().slice(0, 10),
          action: 'Watch portal browser',
          portal: job.portalName ?? 'Direct',
          match: job.match ?? null,
          postingUrl: job.sourceUrl ?? job.portalUrl ?? '',
          attemptStatus: 'queued',
          attemptDetail: '',
        }))

  return rebuildApplicationsFromRows([...createdRows, ...safeApplications.all])
}

function mergeApplicationStatus(applications, statusRow) {
  const safeApplications = normalizeApplications(applications)
  if (!statusRow?.id && !(statusRow?.role && statusRow?.company)) {
    return safeApplications
  }
  const nextAll = safeApplications.all.map((row) => {
    if (row.id !== statusRow.id && !(row.role === statusRow.role && row.company === statusRow.company && !row.id)) {
      return row
    }
    return {
      ...row,
      id: statusRow.id ?? row.id,
      jobResultId: statusRow.jobResultId ?? row.jobResultId ?? null,
      status: statusRow.status ?? row.status,
      stage: statusRow.stage ?? row.stage,
      updated: statusRow.updated ?? row.updated,
      action: statusRow.action ?? row.action,
      attemptStatus: statusRow.attemptStatus ?? row.attemptStatus,
      attemptDetail: statusRow.attemptDetail ?? row.attemptDetail,
      postingUrl: statusRow.postingUrl || row.postingUrl,
      confirmationUrl: statusRow.confirmationUrl ?? row.confirmationUrl,
      portal: statusRow.portal || row.portal,
      match: statusRow.match ?? row.match,
      date: statusRow.date || row.date,
    }
  })
  return rebuildApplicationsFromRows(nextAll)
}

function ToastStack({ toasts }) {
  if (!toasts.length) {
    return null
  }

  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast show ${toast.tone}`}>
          {toast.message}
        </div>
      ))}
    </div>
  )
}

export function JobAutomationPage({ workspace, currentUser }) {
  const [activeTab, setActiveTab] = useState('profile')
  const [trackerTab, setTrackerTab] = useState('all')
  const [trackerSearch, setTrackerSearch] = useState('')
  const [trackerStatusFilter, setTrackerStatusFilter] = useState('all')
  const [trackerPortalFilter, setTrackerPortalFilter] = useState('all')
  const [profile, setProfile] = useState(EMPTY_PROFILE)
  const [searchConfig, setSearchConfig] = useState(EMPTY_SEARCH_CONFIG)
  const [automation, setAutomation] = useState(EMPTY_AUTOMATION)
  const [results, setResults] = useState([])
  const [applications, setApplications] = useState(EMPTY_APPLICATIONS)
  const [analysisJobId, setAnalysisJobId] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(EMPTY_ANALYSIS_RESULT)
  const [portals, setPortals] = useState([])
  const [carriers, setCarriers] = useState([])
  const [portalDraft, setPortalDraft] = useState({ name: '', url: '' })
  const [carrierDraft, setCarrierDraft] = useState({ name: '', url: '' })
  const [portalUploadName, setPortalUploadName] = useState('')
  const [carrierUploadName, setCarrierUploadName] = useState('')
  const [portalImportPreview, setPortalImportPreview] = useState([])
  const [carrierImportPreview, setCarrierImportPreview] = useState([])
  const [resumeFile, setResumeFile] = useState(null)
  const [resumeFileName, setResumeFileName] = useState('')
  const [resumeQueue, setResumeQueue] = useState([])
  const [parseProgress, setParseProgress] = useState(null)
  const [resumeParseResult, setResumeParseResult] = useState(null)
  const [resumes, setResumes] = useState([])
  const [jobDescriptionText, setJobDescriptionText] = useState('')
  const [tailoredResume, setTailoredResume] = useState({ content: '', jobId: null, score: null })
  const [selectedJobs, setSelectedJobs] = useState([])
  const [savedJobs, setSavedJobs] = useState([])
  const [appliedToday, setAppliedToday] = useState(0)
  const [resultsFilter, setResultsFilter] = useState({ query: '', sort: 'match', excludeKeywords: [] })
  const [tailoredJobIds, setTailoredJobIds] = useState([])
  const [excludeKeywordsDraft, setExcludeKeywordsDraft] = useState('')
  const [analyzerDraft, setAnalyzerDraft] = useState('')
  const [linkedinFilters, setLinkedinFilters] = useState({
    query: '',
    experienceLevel: 'all',
    employmentType: 'all',
    company: '',
    under10Applicants: false,
    datePosted: 'all',
    easyApplyOnly: false,
  })
  const [linkedinSort, setLinkedinSort] = useState('relevance')
  const [linkedinRows, setLinkedinRows] = useState([])
  const [toasts, setToasts] = useState([])
  const [hasAnalyzed, setHasAnalyzed] = useState(false)
  const [showTailoredPreview, setShowTailoredPreview] = useState(false)
  const [searchProgress, setSearchProgress] = useState(null)
  const [matchingPipeline, setMatchingPipeline] = useState(null)
  const [appliedSuggestions, setAppliedSuggestions] = useState([])
  const [autofillPreview, setAutofillPreview] = useState(null)
  const [approvedAutofillKeys, setApprovedAutofillKeys] = useState([])
  const [busyAction, setBusyAction] = useState('')

  useEffect(() => {
    if (!workspace) {
      return
    }

    startTransition(() => {
      setProfile(normalizeProfile(workspace.profile))
    setSearchConfig(normalizeSearchConfig(workspace.search))
    setExcludeKeywordsDraft((workspace.search?.excludeKeywords ?? []).join(', '))
    setAutomation(normalizeAutomation(workspace.automation))
    setResults(workspace.results ?? [])
    setResultsFilter({
      query: collectResultKeywords(
        workspace.profile,
        workspace.search,
        workspace.results,
      ).join(', '),
      sort: 'match',
      excludeKeywords: [],
    })
    setTailoredJobIds(
      (workspace.applications?.all ?? [])
        .filter((row) => row.attemptStatus === 'tailored' && row.jobResultId != null)
        .map((row) => Number(row.jobResultId))
        .filter((id) => Number.isFinite(id)),
    )
    setApplications(normalizeApplications(workspace.applications))
    setAnalysisJobId(workspace.analysis?.selectedJobId ?? null)
    setAnalysisResult(normalizeAnalysisResult(workspace.analysis))
    setPortals(workspace.portals ?? [])
    setCarriers(workspace.carriers ?? [])
    setLinkedinRows(workspace.linkedin ?? [])
    setAnalyzerDraft(workspace.analysis?.jobDescription ?? workspace.analysis?.summary ?? '')
    setJobDescriptionText(workspace.analysis?.jobDescription ?? '')
    setSavedJobs(workspace.savedJobs ?? [])
    setResumes(workspace.resumes ?? [])
    setAppliedToday(workspace.stats?.appliedToday ?? 0)
    setResumeFile(null)
    setResumeQueue([])
    setParseProgress(null)
    setResumeParseResult(null)
    setResumeFileName(workspace.profile?.resumeFileName ?? '')
    setSelectedJobs([])
    setToasts([])
    setHasAnalyzed(false)
    setShowTailoredPreview(false)
    setSearchProgress(null)
    setMatchingPipeline(null)
    setAppliedSuggestions([])
    setAutofillPreview(null)
    setApprovedAutofillKeys([])
    setBusyAction('')
      setTailoredResume({ content: '', jobId: null, score: null })
    })
  }, [workspace])

  useEffect(() => {
    if (activeTab === 'linkedin' && linkedinRows.length === 0 && workspace?.linkedin?.length) {
      searchLinkedInJobs(linkedinFilters)
        .then((response) => setLinkedinRows(response.results ?? []))
        .catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  useEffect(() => {
    if (!showTailoredPreview) {
      return undefined
    }
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setShowTailoredPreview(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [showTailoredPreview])

  const deferredResultsFilter = useDeferredValue(resultsFilter)

  const effectiveEmploymentType = resolveEmploymentType(searchConfig, profile)
  const filteredResults = useMemo(
    () => getFilteredJobs(results, deferredResultsFilter, effectiveEmploymentType, {
      maxPostedHours: 48,
    }),
    [results, deferredResultsFilter, effectiveEmploymentType],
  )

  const filteredLinkedin = useMemo(
    () => sortLinkedInJobs(linkedinRows, linkedinSort),
    [linkedinRows, linkedinSort],
  )

  const avgMatchScore = useMemo(() => {
    if (!results.length) {
      return workspace?.stats?.avgMatchScore ?? 0
    }
    return Math.round(results.reduce((sum, job) => sum + job.match, 0) / results.length)
  }, [results, workspace?.stats?.avgMatchScore])

  const tabBadges = useMemo(() => ({
    search: countSearchConfigItems(searchConfig),
    results: results.length,
    linkedin: linkedinRows.length,
    tracker: applications?.stats?.actionNeeded ?? 0,
  }), [searchConfig, results.length, linkedinRows.length, applications?.stats?.actionNeeded])
  const repeatEveryValue = String(searchConfig?.repeatEvery ?? 'Once daily')
  const customScheduleMinutes = getCustomScheduleMinutes(repeatEveryValue)
  const scheduleSelectValue = customScheduleMinutes != null
    ? CUSTOM_SEARCH_SCHEDULE_OPTION
    : (SEARCH_REPEAT_OPTIONS.includes(repeatEveryValue) ? repeatEveryValue : 'Once daily')

  const wizardTabs = useMemo(
    () => panelTabs.filter((tab) => wizardTabKeys.includes(tab.key)),
    [],
  )
  const activeWizardIndex = Math.max(0, wizardTabs.findIndex((tab) => tab.key === activeTab))
  const activeWizardTab = wizardTabs[activeWizardIndex] ?? wizardTabs[0]
  const wizardProgress = wizardTabs.length > 1
    ? Math.round((activeWizardIndex / (wizardTabs.length - 1)) * 100)
    : 100

  const goWizardStep = (direction) => {
    const nextIndex = direction === 'next'
      ? Math.min(activeWizardIndex + 1, wizardTabs.length - 1)
      : Math.max(activeWizardIndex - 1, 0)
    const nextTab = wizardTabs[nextIndex]
    if (nextTab) {
      setActiveTab(nextTab.key)
    }
  }

  const selectedJob = analysisJobId ? results.find((job) => job.id === analysisJobId) : null
  const trackerPortalOptions = useMemo(() => {
    const portals = Array.from(new Set((applications.all || []).map((row) => row.portal || 'Direct').filter(Boolean)))
    return portals.sort((a, b) => a.localeCompare(b))
  }, [applications.all])

  const filteredTrackerRows = useMemo(() => {
    const base =
      trackerTab === 'interviews'
        ? (applications?.interviews ?? [])
        : trackerTab === 'actionNeeded'
          ? (applications?.actionNeeded ?? [])
          : (applications?.all ?? [])
    const query = trackerSearch.trim().toLowerCase()
    return base.filter((item) => {
      if (trackerStatusFilter !== 'all' && item.status !== trackerStatusFilter) {
        return false
      }
      if (trackerPortalFilter !== 'all' && (item.portal || 'Direct') !== trackerPortalFilter) {
        return false
      }
      if (!query) {
        return true
      }
      const haystack = [item.role, item.company, item.portal, item.status, item.stage, item.action]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    })
  }, [
    applications,
    trackerTab,
    trackerSearch,
    trackerStatusFilter,
    trackerPortalFilter,
  ])

  const currentTrackerRows = filteredTrackerRows

  const pushNotice = (message, tone = 'success') => {
    const id = ++toastSequence
    setToasts((current) => [...current, { id, message, tone }])
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id))
    }, 3200)
  }

  const isReadOnly = currentUser?.role === 'user'

  const ensureCanModify = (actionLabel, { profileScope = false } = {}) => {
    if (!isReadOnly || profileScope) {
      return true
    }
    pushNotice(`You have view-only access. ${actionLabel} requires admin access.`, 'error')
    return false
  }

  const validateProfile = () => {
    if (!isNonEmpty(profile.name, 2)) {
      pushNotice('Full name must be at least 2 characters.', 'error')
      return false
    }
    if (!isEmail(profile.email)) {
      pushNotice('Profile email must be valid.', 'error')
      return false
    }
    if (!isPhone(profile.phone)) {
      pushNotice('Enter a valid phone number (6+ digits).', 'error')
      return false
    }
    if (!isNonEmpty(profile.location, 2)) {
      pushNotice('Location is required.', 'error')
      return false
    }
    if (!isHttpUrl(profile.linkedin)) {
      pushNotice('LinkedIn must be a valid http/https URL.', 'error')
      return false
    }
    return true
  }

  const validateSearchConfig = () => {
    if (!getEffectiveSearchTitles(profile, searchConfig).length) {
      pushNotice('Add at least one job title before search.', 'error')
      return false
    }
    if (!isNonEmpty(searchConfig.location, 2)) {
      pushNotice('Search location is required.', 'error')
      return false
    }
    return true
  }

  const updateProfile = (field, value) => {
    setProfile((current) => ({ ...current, [field]: value }))
  }

  const updateAutomation = (field, value) => {
    setAutomation((current) => ({ ...current, [field]: value }))
  }

  const updateSearchConfig = (field, value) => {
    setSearchConfig((current) => ({ ...current, [field]: value }))
  }

  const persistSearchConfig = async (nextConfig, successMessage) => {
    if (!ensureCanModify('Search configuration', { profileScope: true })) {
      return false
    }

    try {
      const response = await saveSearchConfig(nextConfig)
      if (response.search) {
        setSearchConfig(normalizeSearchConfig(response.search))
      }
      if (successMessage) {
        pushNotice(successMessage)
      }
      return true
    } catch (error) {
      pushNotice(error.message ?? 'Failed to save search configuration.', 'error')
      return false
    }
  }

  const addTag = async (field, draft) => {
    const normalized = formatTitle(draft.trim())

    if (!normalized) {
      return
    }

    const currentItems = searchConfig[field] ?? []
    if (currentItems.some((item) => normalizeLabel(item) === normalizeLabel(normalized))) {
      pushNotice(`"${normalized}" is already in the list.`, 'warning')
      return
    }

    const nextConfig = { ...searchConfig, [field]: [...currentItems, normalized] }
    setSearchConfig(nextConfig)
    await persistSearchConfig(nextConfig, `Added "${normalized}".`)
  }

  const removeTag = async (field, value) => {
    const nextConfig = {
      ...searchConfig,
      [field]: (searchConfig[field] ?? []).filter((item) => item !== value),
    }
    setSearchConfig(nextConfig)
    await persistSearchConfig(nextConfig, `Removed "${value}".`)
  }

  const saveSearchConfigAction = async () => {
    if (!validateSearchConfig()) {
      return
    }
    setBusyAction('saveSearch')
    try {
      await persistSearchConfig(searchConfig, 'Search configuration saved.')
    } finally {
      setBusyAction('')
    }
  }

  const addPresetSearchTitles = async () => {
    const merged = [...searchConfig.titles]

    presetTitles.forEach((title) => {
      if (!merged.some((item) => normalizeLabel(item) === normalizeLabel(title))) {
        merged.push(title)
      }
    })

    const nextConfig = { ...searchConfig, titles: merged }
    setSearchConfig(nextConfig)
    await persistSearchConfig(nextConfig, 'Preset job titles added to the search builder.')
  }

  const togglePortalStatus = (portal) => {
    if (!ensureCanModify('Portal status')) {
      return
    }

    setPortals((current) => current.map((item) => {
      if (item.name === portal.name && item.url === portal.url) {
        const nextStatus = (item.status ?? 'Active') === 'Active' ? 'Paused' : 'Active'
        pushNotice(`${portal.name} is now ${nextStatus}.`, nextStatus === 'Active' ? 'success' : 'warning')
        return { ...item, status: nextStatus }
      }
      return item
    }))
  }

  const applySuggestionToDraft = (suggestion) => {
    if (!String(suggestion || '').trim()) {
      return
    }
    setTailoredResume((current) => ({
      ...current,
      jobId: current.jobId || analysisJobId,
      content: appendSuggestionToTailoredDraft(current.content, suggestion),
    }))
    setAppliedSuggestions((current) => (
      current.includes(suggestion) ? current : [...current, suggestion]
    ))
    setShowTailoredPreview(false)
    pushNotice('Suggestion added to role-aligned adjustments (base resume preserved).')
  }

  const applyAllSuggestions = () => {
    const suggestions = analysisResult.recommendations ?? analysisResult.suggestions ?? []
    if (!suggestions.length) {
      pushNotice('No suggestions to apply yet.', 'error')
      return
    }
    setTailoredResume((current) => {
      let nextContent = current.content || ''
      suggestions.forEach((item) => {
        nextContent = appendSuggestionToTailoredDraft(nextContent, item)
      })
      return {
        ...current,
        jobId: current.jobId || analysisJobId,
        content: nextContent,
      }
    })
    setAppliedSuggestions(suggestions)
    pushNotice(`Applied ${suggestions.length} role-aligned adjustments without rewriting your history.`)
  }

  const loadAutofillPreviewAction = async (approvedKeys = approvedAutofillKeys) => {
    if (!ensureCanModify('Application autofill')) {
      return
    }
    setBusyAction('autofill')
    try {
      const response = await previewApplicationAutofill(analysisJobId || undefined, approvedKeys)
      setAutofillPreview(response)
      pushNotice(response.message ?? 'Autofill preview ready for review.')
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not build autofill preview.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const toggleAutofillApproval = async (fieldKey) => {
    const nextKeys = approvedAutofillKeys.includes(fieldKey)
      ? approvedAutofillKeys.filter((key) => key !== fieldKey)
      : [...approvedAutofillKeys, fieldKey]
    setApprovedAutofillKeys(nextKeys)
    await loadAutofillPreviewAction(nextKeys)
  }

  const followUpAction = async (item) => {
    if (!item?.id) {
      pushNotice('This application is missing an id — refresh the tracker and try again.', 'error')
      return
    }
    if (!ensureCanModify('Follow-up scheduling')) {
      return
    }
    setBusyAction(`followup-${item.id}`)
    try {
      const response = await scheduleJobApplicationFollowUp(
        item.id,
        `Follow up with ${item.company} about ${item.role}`,
      )
      if (response.application) {
        setApplications((current) => mergeApplicationStatus(current, response.application))
      }
      pushNotice(response.message ?? `Follow-up scheduled for ${item.company} — ${item.role}.`)
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not schedule follow-up.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const updateTrackerStatusAction = async (item, nextStatus) => {
    if (!item?.id) {
      pushNotice('Refresh the tracker before changing status.', 'error')
      return
    }
    if (!ensureCanModify('Application status update')) {
      return
    }
    if (!nextStatus || nextStatus === item.status) {
      return
    }
    setBusyAction(`status-${item.id}`)
    try {
      const response = await updateJobApplication(item.id, { status: nextStatus })
      if (response.application) {
        setApplications((current) => mergeApplicationStatus(current, response.application))
      }
      pushNotice(response.message ?? `Moved ${item.role} to ${nextStatus}.`)
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not update application status.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const refreshTrackerAction = async () => {
    setBusyAction('refreshTracker')
    try {
      const response = await listJobApplications(100)
      if (response.tracker) {
        setApplications(normalizeApplications(response.tracker))
      } else {
        setApplications(rebuildApplicationsFromRows(response.applications || []))
      }
      pushNotice(`Tracker refreshed — ${response.applications?.length ?? 0} applications loaded.`)
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not refresh tracker.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const viewPostingAction = (item) => {
    if (item.postingUrl) {
      window.open(item.postingUrl, '_blank', 'noopener,noreferrer')
      return
    }
    pushNotice(`No posting URL on file for ${item.role} at ${item.company}.`, 'warning')
  }

  const openConfirmationAction = (item) => {
    if (item.confirmationUrl) {
      window.open(item.confirmationUrl, '_blank', 'noopener,noreferrer')
      return
    }
    pushNotice('No confirmation URL is available for this application yet.', 'warning')
  }

  const toggleJob = (jobId) => {
    setSelectedJobs((current) => (
      current.includes(jobId)
        ? current.filter((item) => item !== jobId)
        : [...current, jobId]
    ))
  }

  const saveProfileAction = async () => {
    if (!ensureCanModify('Profile update', { profileScope: true })) {
      return
    }

    if (!validateProfile()) {
      return
    }

    setBusyAction('saveProfile')

    try {
      const profileResponse = await saveJobProfile(profile)
      await saveAutomationSettings(normalizeAutomationForSave(automation))
      if (profileResponse.profile) {
        setProfile(normalizeProfile(profileResponse.profile))
      }
      if (profileResponse.search) {
        setSearchConfig(normalizeSearchConfig(profileResponse.search))
      }
      if (profileResponse.resumes?.length) {
        setResumes(profileResponse.resumes)
      }
      pushNotice(profileResponse.message ?? 'Active CV profile saved (isolated from other CVs).')
    } catch {
      pushNotice('Profile save failed. Check the backend connection.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const applyParseResponse = (response) => {
    const parsed = response.parsedProfile ?? {}
    const titles = parsed.jobTitles?.length ? parsed.jobTitles : (response.profile?.jobTitles ?? searchConfig?.titles ?? [])
    const skills = parsed.skills ?? response.profile?.resumeSkills ?? []
    const experienceText = mapYearsToExperienceText(parsed.yearsExperience)

    const profileFromApi = response.profile ? normalizeProfile(response.profile) : null
    const nextProfile = normalizeProfile({
      ...(profileFromApi ?? profile),
      name: parsed.fullName || profileFromApi?.name || profile.name,
      email: parsed.email || profileFromApi?.email || profile.email,
      phone: parsed.phone || profileFromApi?.phone || profile.phone,
      location: parsed.location || profileFromApi?.location || profile.location,
      linkedin: parsed.linkedin || profileFromApi?.linkedin || profile.linkedin,
      experience: experienceText || profileFromApi?.experience || profile.experience,
      jobTitles: titles,
      resumeFileName: response.filename || profileFromApi?.resumeFileName || profile.resumeFileName,
      resumeSummary: parsed.summary || profileFromApi?.resumeSummary || profile.resumeSummary,
      resumeSkills: skills,
    })

    const nextSearch = normalizeSearchConfig(response.search ?? {
      ...searchConfig,
      titles,
      requiredSkills: skills,
    })

    setProfile(nextProfile)
    setSearchConfig(nextSearch)
    setResultsFilter((current) => ({
      ...current,
      query: collectResultKeywords(
        nextProfile,
        nextSearch,
        results,
        response.mlAssessment?.matchedSkills ?? [],
      ).join(', '),
    }))
    setResumeParseResult({
      mlScore: response.mlAssessment?.matchScore,
      matchedSkills: response.mlAssessment?.matchedSkills ?? [],
      missingSkills: response.mlAssessment?.missingSkills ?? [],
      insights: response.llmAssessment?.insights ?? '',
      preview: response.extractedTextPreview ?? '',
      agentUsed: response.agentTrace?.used,
    })
    if (response.resumes?.length) {
      setResumes(response.resumes)
    }
    if (response.filename || nextProfile.resumeFileName) {
      setResumeFileName(response.filename || nextProfile.resumeFileName)
    }
    return { titles, skills, nextProfile }
  }

  const parseResumeAction = async () => {
    const filesToParse = resumeQueue.length
      ? resumeQueue
      : (resumeFile ? [resumeFile] : [])

    if (!filesToParse.length) {
      pushNotice('Upload one or more resume files before parsing.', 'error')
      return
    }

    setBusyAction('parseResume')
    setParseProgress({ current: 0, total: filesToParse.length, fileName: filesToParse[0]?.name ?? '' })

    const targetRole = searchConfig?.titles?.[0] ?? profile?.jobTitles?.[0] ?? 'Software Engineer'
    const requiredSkills = (searchConfig?.requiredSkills ?? []).join(',') || 'Java,Spring Boot,Python,AWS'
    let lastResult = null
    let successCount = 0
    const failures = []

    try {
      for (let index = 0; index < filesToParse.length; index += 1) {
        const file = filesToParse[index]
        setParseProgress({ current: index + 1, total: filesToParse.length, fileName: file.name })
        try {
          const response = await parseResumeFile(file, targetRole, requiredSkills)
          lastResult = applyParseResponse(response)
          successCount += 1
        } catch (error) {
          failures.push(`${file.name}: ${error.message ?? 'parse failed'}`)
        }
      }

      setResumeQueue([])
      setResumeFile(null)

      if (successCount > 0) {
        const titles = lastResult?.titles?.length ?? 0
        const skills = lastResult?.skills?.length ?? 0
        const contactName = lastResult?.nextProfile?.name || 'Active CV'
        pushNotice(
          failures.length
            ? `Parsed & saved ${successCount}/${filesToParse.length} CV(s). Active CV contact updated for ${contactName}. ${failures[0]}`
            : `Parsed & saved ${successCount} CV(s) — contact details filled for ${contactName} (${titles} title(s), ${skills} skill(s)).`,
        )
        setActiveTab('profile')
      } else {
        pushNotice(failures[0] ?? 'Resume parsing failed. Check file format and backend status.', 'error')
      }
    } finally {
      setParseProgress(null)
      setBusyAction('')
    }
  }

  const handleResumeFileSelect = (fileList) => {
    const files = Array.from(fileList ?? []).filter(Boolean)
    if (!files.length) {
      setResumeFile(null)
      setResumeFileName('')
      setResumeQueue([])
      return
    }
    setResumeQueue(files)
    setResumeFile(files[0])
    setResumeFileName(files.length === 1 ? files[0].name : `${files.length} files selected`)
  }

  const removeQueuedResume = (index) => {
    setResumeQueue((current) => {
      const next = current.filter((_, itemIndex) => itemIndex !== index)
      setResumeFile(next[0] ?? null)
      setResumeFileName(next.length === 1 ? next[0].name : (next.length ? `${next.length} files selected` : ''))
      return next
    })
  }

  const activateResumeAction = async (resumeId) => {
    setBusyAction(`activateResume-${resumeId}`)
    try {
      const response = await activateUserResume(resumeId)
      setResumes(response.resumes ?? [])
      if (response.profile) {
        const normalizedProfile = normalizeProfile(response.profile)
        setProfile(normalizedProfile)
        setResumeFileName(normalizedProfile.resumeFileName ?? '')
      }
      if (response.search) {
        setSearchConfig(normalizeSearchConfig(response.search))
      }
      setResumeParseResult(null)
      pushNotice(response.message ?? 'Active CV switched — profile reloaded from that CV’s snapshot.')
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not switch the active CV.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const deleteResumeAction = async (resumeId) => {
    setBusyAction(`deleteResume-${resumeId}`)
    try {
      const response = await deleteUserResume(resumeId)
      setResumes(response.resumes ?? [])
      if (response.profile) {
        const normalizedProfile = normalizeProfile(response.profile)
        setProfile(normalizedProfile)
        setResumeFileName(normalizedProfile.resumeFileName ?? '')
      }
      if (response.search) {
        setSearchConfig(normalizeSearchConfig(response.search))
      }
      pushNotice(response.message ?? 'CV removed from your library.')
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not delete this CV.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const previewResumeAction = () => {
    if (resumeFile) {
      const url = URL.createObjectURL(resumeFile)
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(url), 60000)
      pushNotice(`Opened preview for ${resumeFile.name}.`)
      return
    }

    if (resumeParseResult?.preview) {
      const previewWindow = window.open('', '_blank', 'noopener,noreferrer')
      if (previewWindow) {
        previewWindow.document.write(`<pre style="font-family:system-ui;padding:16px;white-space:pre-wrap;">${resumeParseResult.preview}</pre>`)
        previewWindow.document.close()
      }
      return
    }

    if (profile.resumeFileName || profile.resumeSummary) {
      pushNotice(`Active resume: ${profile.resumeFileName || 'parsed profile on file'}.`)
      return
    }

    pushNotice('Upload a resume before previewing.', 'error')
  }

  const runAutoApplyAction = async () => {
    if (!ensureCanModify('Auto apply', { profileScope: true })) {
      return
    }

    const effectiveTitles = getEffectiveSearchTitles(profile, searchConfig)
    if (!effectiveTitles.length) {
      pushNotice('Configure at least one job title in Job Search or add target titles to your profile.', 'error')
      return
    }

    if (!searchConfig?.titles?.length && effectiveTitles.length) {
      const nextConfig = { ...searchConfig, titles: effectiveTitles }
      setSearchConfig(nextConfig)
      await persistSearchConfig(nextConfig)
    }

    setBusyAction('autoApply')
    setSearchProgress({
      active: true,
      message: `Scraping ${portals.length || 3} portal(s) for 24h + 48h postings…`,
      pct: 10,
    })
    const progressTimer = window.setInterval(() => {
      setSearchProgress((current) => (
        current?.active
          ? { ...current, pct: Math.min((current.pct ?? 0) + 10, 90) }
          : current
      ))
    }, 400)

    try {
      await persistSearchConfig(searchConfig)
      const applyFloor = Math.max(MATCH_POLICY.applyMin, Number(automation.matchThreshold) || MATCH_POLICY.applyMin)
      await saveAutomationSettings(normalizeAutomationForSave({
        ...automation,
        matchThreshold: applyFloor,
      }))
      const response = await runAutoApply(applyFloor)
      const applyResults = sortJobsByOption(response.results ?? [], resultsFilter.sort)
      const tailoredCount = response.tailored ?? 0
      const rejectedCount = response.rejected ?? 0
      const appliedCount = response.applied ?? (response.jobIds?.length ?? 0)

      setSearchProgress({
        active: true,
        message: `Routed ${appliedCount} apply · ${tailoredCount} tailor · ${rejectedCount} reject.`,
        pct: 100,
      })

      startTransition(() => {
        setResults(applyResults)
        setResultsFilter((current) => ({
          ...current,
          query: collectResultKeywords(
            profile,
            searchConfig,
            applyResults,
            resumeParseResult?.matchedSkills ?? [],
          ).join(', '),
        }))
        setMatchingPipeline(response.matchingPipeline ?? null)
        setActiveTab('results')
      })

      const jobIds = response.jobIds ?? []
      if (jobIds.length) {
        setApplications((current) => bumpApplicationsState(current, jobIds, applyResults.length ? applyResults : results))
        setAppliedToday((n) => n + appliedCount)
      }

      const decisionRows = [
        ...(response.tailoredApplications ?? []),
        ...(response.rejectedApplications ?? []),
      ]
      if (decisionRows.length) {
        setApplications((current) => {
          const safe = normalizeApplications(current)
          return rebuildApplicationsFromRows([...decisionRows, ...safe.all])
        })
      }
      const nextTailoredIds = (response.tailoredJobIds ?? [])
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id))
      if (nextTailoredIds.length) {
        setTailoredJobIds((current) => Array.from(new Set([...current, ...nextTailoredIds])))
      }

      pushNotice(
        response.message
          ?? `Auto apply: ${appliedCount} applied (≥${MATCH_POLICY.applyMin}%), ${tailoredCount} tailored, ${rejectedCount} rejected.`,
      )
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Auto apply failed. Check portals, search config, and backend service.'), 'error')
    } finally {
      window.clearInterval(progressTimer)
      setBusyAction('')
      window.setTimeout(() => setSearchProgress(null), 800)
    }
  }

  const handleAutoApplyToggle = async () => {
    const next = !automation.autoApply
    updateAutomation('autoApply', next)
    if (!ensureCanModify('Automation settings')) {
      return
    }
    try {
      await saveAutomationSettings(normalizeAutomationForSave({ ...automation, autoApply: next }))
      if (next) {
        await runAutoApplyAction()
      } else {
        pushNotice('Auto apply disabled.')
      }
    } catch {
      pushNotice('Failed to save automation settings.', 'error')
    }
  }

  useEffect(() => {
    if (!automation?.scheduleEnabled) {
      return undefined
    }
    const intervalMs = parseScheduleIntervalMs(searchConfig?.repeatEvery)
    if (!intervalMs) {
      return undefined
    }

    const timer = window.setInterval(() => {
      if (!profile?.resumeFileName || !(profile?.resumeSkills ?? []).length) {
        return
      }
      if (busyAction) {
        return
      }
      runAutoApplyAction()
    }, intervalMs)

    return () => window.clearInterval(timer)
  }, [
    automation?.scheduleEnabled,
    searchConfig?.repeatEvery,
    profile?.resumeFileName,
    profile?.resumeSkills,
    busyAction,
  ])

  const parseExcludeKeywords = (value) => (
    String(value ?? '')
      .split(',')
      .map((keyword) => keyword.trim())
      .filter(Boolean)
  )

  const commitExcludeKeywords = (draftValue = excludeKeywordsDraft, nextConfig = searchConfig) => {
    const excludeKeywords = parseExcludeKeywords(draftValue)
    const merged = { ...nextConfig, excludeKeywords }
    setExcludeKeywordsDraft(excludeKeywords.join(', '))
    setSearchConfig(merged)
    return merged
  }

  const runSearchAction = async (options = {}) => {
    if (!ensureCanModify('Search execution')) {
      return
    }

    if (!validateSearchConfig()) {
      return
    }

    const draftValue = options.excludeKeywordsDraft ?? excludeKeywordsDraft
    const baseConfig = options.searchConfig ?? searchConfig
    const nextSearchConfig = commitExcludeKeywords(draftValue, baseConfig)

    setBusyAction('runSearch')
    setSearchProgress({ active: true, message: `Searching ${portals.length || 4} portals…`, pct: 8 })
    const progressTimer = window.setInterval(() => {
      setSearchProgress((current) => (
        current?.active
          ? { ...current, pct: Math.min((current.pct ?? 0) + 12, 92) }
          : current
      ))
    }, 350)

    try {
      const employmentType = resolveEmploymentType(nextSearchConfig, profile)
      // Match routing policy: Results only keep ≤48h postings (postedWithin 1 or 2).
      const postedWithin = ['1', '2'].includes(String(nextSearchConfig.postedWithin))
        ? String(nextSearchConfig.postedWithin)
        : '2'
      const searchPayloadConfig = {
        ...nextSearchConfig,
        employmentType,
        postedWithin,
      }
      await persistSearchConfig(searchPayloadConfig)
      const response = await runJobSearch({
        titles: searchPayloadConfig.titles,
        requiredSkills: searchPayloadConfig.requiredSkills,
        optionalSkills: searchPayloadConfig.optionalSkills,
        location: searchPayloadConfig.location,
        radius: searchPayloadConfig.radius,
        filters: searchPayloadConfig.filters,
        excludeKeywords: searchPayloadConfig.excludeKeywords,
        employmentType,
        minMatchScore: searchPayloadConfig.minMatchScore ?? 70,
        postedWithin,
        experienceLevel: searchPayloadConfig.experienceLevel ?? 'Any',
        rateMin: searchPayloadConfig.rateMin ?? '',
        rateMax: searchPayloadConfig.rateMax ?? '',
        repeatEvery: searchPayloadConfig.repeatEvery ?? 'Once daily',
      })

      setSearchProgress({ active: true, message: `Found ${response.results?.length ?? 0} matching jobs!`, pct: 100 })

      startTransition(() => {
        const searchResults = sortJobsByOption(response.results ?? [], resultsFilter.sort)
        setResults(searchResults)
        setResultsFilter((current) => ({
          ...current,
          query: collectResultKeywords(
            profile,
            searchPayloadConfig,
            searchResults,
            resumeParseResult?.matchedSkills ?? [],
          ).join(', '),
        }))
        setMatchingPipeline(response.matchingPipeline ?? null)
        setActiveTab('results')
      })

      pushNotice(response.message ?? 'Search completed with fresh matches.')
    } catch (error) {
      pushNotice(error.message ?? 'Search failed. Verify the backend service and retry.', 'error')
    } finally {
      window.clearInterval(progressTimer)
      setBusyAction('')
      window.setTimeout(() => setSearchProgress(null), 700)
    }
  }

  const addPortalAction = async () => {
    if (!ensureCanModify('Portal updates')) {
      return
    }

    if (!portalDraft.name.trim() || !portalDraft.url.trim()) {
      pushNotice('Portal name and URL are required.', 'error')
      return
    }

    if (!isHttpUrl(portalDraft.url)) {
      pushNotice('Portal URL must be a valid http/https URL.', 'error')
      return
    }

    setBusyAction('addPortal')

    try {
      const created = await addPortalItem(portalDraft)
      const portal = created.portal ?? portalDraft
      setPortals((current) => [...current, { ...portal, status: portal.status ?? 'Active' }])
      setPortalDraft({ name: '', url: '' })
      pushNotice(created.message ?? 'Portal added to the automation queue.')
    } catch {
      pushNotice('Portal add failed. Check the backend service.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const addCarrierAction = async () => {
    if (!ensureCanModify('Carrier updates')) {
      return
    }

    if (!carrierDraft.name.trim() || !carrierDraft.url.trim()) {
      pushNotice('Carrier name and URL are required.', 'error')
      return
    }

    if (!isHttpUrl(carrierDraft.url)) {
      pushNotice('Carrier URL must be a valid http/https URL.', 'error')
      return
    }

    setBusyAction('addCarrier')

    try {
      const created = await addCarrierItem(carrierDraft)
      const carrier = created.carrier ?? carrierDraft
      setCarriers((current) => [...current, carrier])
      setCarrierDraft({ name: '', url: '' })
      pushNotice(created.message ?? 'Carrier page saved.')
    } catch {
      pushNotice('Carrier save failed. Check the backend service.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const applyPortalJobDescription = (jobId, payload) => {
    const description = String(payload?.description ?? '').trim()
    if (!description) {
      return ''
    }
    setJobDescriptionText(description)
    setAnalyzerDraft(description)
    setResults((current) => current.map((row) => (
      row.id === jobId
        ? {
            ...row,
            description,
            role: payload.role || row.role,
            sourceUrl: payload.sourceUrl || row.sourceUrl,
            descriptionQuality: payload.descriptionQuality || row.descriptionQuality,
          }
        : row
    )))
    return description
  }

  const fetchJobDescriptionFromPortal = async (jobId, { silent = false } = {}) => {
    if (!jobId) {
      return null
    }
    setBusyAction('fetchJd')
    try {
      const response = await refreshJobDescription(jobId)
      const description = applyPortalJobDescription(jobId, response)
      if (!silent) {
        pushNotice(
          response.message
            || (description
              ? 'Job description loaded from the portal website.'
              : 'Portal fetch returned no description.'),
          response.success && description ? 'info' : 'warning',
        )
      }
      return response
    } catch (error) {
      if (!silent) {
        pushNotice(getErrorMessage(error, 'Could not fetch the job description from the portal website.'), 'error')
      }
      return null
    } finally {
      setBusyAction((current) => (current === 'fetchJd' ? '' : current))
    }
  }

  const openJobInAnalyzer = async (job, { runAnalyze = true } = {}) => {
    if (!job?.id) {
      return
    }
    const initialDescription = String(job.description ?? '').trim()
    setAnalysisJobId(job.id)
    setJobDescriptionText(initialDescription)
    setAnalyzerDraft(initialDescription)
    setActiveTab('analyzer')
    setHasAnalyzed(false)

    // Always try to connect to the portal/vendor page and fill the Analyzer JD box.
    const refreshed = await fetchJobDescriptionFromPortal(job.id, { silent: true })
    const portalJd = String(refreshed?.description || initialDescription || '').trim()
    if (portalJd) {
      setJobDescriptionText(portalJd)
      setAnalyzerDraft(portalJd)
    }

    if (runAnalyze) {
      setBusyAction('analyze')
      try {
        const response = await analyzeJob({
          jobId: job.id,
          jobDescription: portalJd || undefined,
        })
        const analysis = normalizeAnalysisResult(response.analysis ?? response)
        setAnalysisResult(analysis)
        setHasAnalyzed(true)
        const fullJd = String(analysis.jobDescription || portalJd || '').trim()
        if (fullJd) {
          applyPortalJobDescription(job.id, { description: fullJd, role: job.role })
        }
        pushNotice(
          fullJd.length >= 180
            ? `Loaded portal job description for ${job.role} — ${analysis.score}% match.`
            : `Analyzer opened for ${job.role}. Use “Fetch JD from portal” if the description is incomplete.`,
        )
        try {
          const autofill = await previewApplicationAutofill(job.id, approvedAutofillKeys)
          setAutofillPreview(autofill)
        } catch {
          // optional
        }
      } catch {
        pushNotice('Opened Analyzer with portal description. CV analysis failed — try Analyze CV match again.', 'warning')
      } finally {
        setBusyAction('')
      }
    }
  }

  const analyzeAction = async (jobId = analysisJobId) => {
    if (!ensureCanModify('CV analysis')) {
      return
    }

    const description = jobDescriptionText.trim() || analyzerDraft.trim()
    if (!jobId && description.length < 20) {
      pushNotice('Select a job or paste a job description (20+ characters).', 'error')
      return
    }

    setBusyAction('analyze')

    try {
      const response = await analyzeJob({
        jobId: jobId || undefined,
        jobDescription: description || undefined,
      })
      const analysis = normalizeAnalysisResult(response.analysis ?? response)
      setAnalysisResult(analysis)
      setHasAnalyzed(true)
      if (jobId) {
        setAnalysisJobId(jobId)
      }
      if (analysis.jobDescription) {
        setJobDescriptionText(analysis.jobDescription)
        setAnalyzerDraft(analysis.jobDescription)
      }
      pushNotice(response.message ?? `CV analysis completed — ${analysis.score}% match.`)
      setActiveTab('analyzer')
      // Refresh reviewable autofill map for the selected posting.
      try {
        const autofill = await previewApplicationAutofill(jobId || analysisJobId || undefined, approvedAutofillKeys)
        setAutofillPreview(autofill)
      } catch {
        // Autofill is optional after analyze.
      }
    } catch {
      pushNotice('CV analysis failed. Check the backend service.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const tailorResumeAction = async () => {
    if (!ensureCanModify('CV tailoring')) {
      return
    }
    if (!analysisJobId) {
      pushNotice('Select a job reference in the Analyzer before tailoring.', 'error')
      return
    }
    if (!hasAnalyzed) {
      pushNotice('Run Analyze CV match first, then Tailor resume.', 'error')
      return
    }

    setBusyAction('tailor')

    try {
      const response = await tailorResumeForJob(analysisJobId, jobDescriptionText || analyzerDraft)
      const content = String(response.content ?? '').trim()
      if (!content) {
        throw new Error('The backend did not return tailored resume content.')
      }
      setTailoredResume({
        content: response.content,
        jobId: analysisJobId,
        score: response.tailoredScore ?? null,
      })
      setTailoredJobIds((current) => Array.from(new Set([...current, analysisJobId])))
      setShowTailoredPreview(true)
      try {
        await saveTailoredResume(analysisJobId, response.content)
      } catch {
        // Draft remains available even if immediate save fails.
      }
      if (response.analysis) {
        setAnalysisResult((current) => ({
          ...normalizeAnalysisResult(current),
          ...response.analysis,
          tailoredScore: response.tailoredScore ?? response.analysis.tailoredScore ?? null,
        }))
      } else if (response.tailoredScore != null) {
        setAnalysisResult((current) => ({
          ...normalizeAnalysisResult(current),
          tailoredScore: response.tailoredScore,
        }))
      }
      pushNotice(
        response.message
          ?? `Resume tailored with ${Array.isArray(response.jdPointers) ? response.jdPointers.length : 0} JD pointer(s) `
            + `(${response.tailoredScore ?? '—'}% estimated match).`,
      )
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Resume tailoring failed.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const saveTailoredResumeAction = async () => {
    if (!ensureCanModify('Save tailored resume')) {
      return
    }
    const jobId = tailoredResume.jobId || analysisJobId
    const content = String(tailoredResume.content ?? '').trim()
    if (!jobId) {
      pushNotice('Select a job before saving a tailored resume.', 'error')
      return
    }
    if (content.length < 20) {
      pushNotice('Tailor or paste at least 20 characters before saving.', 'error')
      return
    }

    setBusyAction('saveTailored')

    try {
      const response = await saveTailoredResume(jobId, content)
      setTailoredResume((current) => ({ ...current, jobId }))
      setTailoredJobIds((current) => Array.from(new Set([...current, jobId])))
      pushNotice(response.message ?? 'Tailored resume saved for this job.')
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Failed to save tailored resume.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const previewTailoredResumeAction = () => {
    if (!String(tailoredResume.content ?? '').trim()) {
      pushNotice('Tailor a resume (or Load saved) before previewing.', 'error')
      return
    }
    setShowTailoredPreview(true)
  }

  const downloadTailoredResumeAction = () => {
    const content = String(tailoredResume.content ?? '').trim()
    if (!content) {
      pushNotice('Tailor a resume before downloading.', 'error')
      return
    }
    const jobId = tailoredResume.jobId || analysisJobId
    const selectedJob = results.find((job) => job.id === jobId)
    const safeRole = (selectedJob?.role || `job-${jobId || 'draft'}`)
      .replace(/[^a-z0-9]+/gi, '-')
      .replace(/^-|-$/g, '')
      .toLowerCase()
    downloadTextFile(`tailored-resume-${safeRole || jobId || 'draft'}.txt`, tailoredResume.content)
    pushNotice('Tailored resume downloaded as .txt.')
  }

  const loadTailoredResumeAction = async (jobId = analysisJobId) => {
    if (!jobId) {
      pushNotice('Select a job reference to load its saved tailored resume.', 'error')
      return
    }

    setBusyAction('loadTailored')
    try {
      const response = await getTailoredResume(jobId)
      if (response.found && String(response.content ?? '').trim()) {
        setTailoredResume((current) => ({
          content: response.content,
          jobId,
          score: current.score,
        }))
        setTailoredJobIds((current) => Array.from(new Set([...current, jobId])))
        setShowTailoredPreview(true)
        setAnalysisJobId(jobId)
        pushNotice('Saved tailored resume loaded — you can edit, save, preview, or download.')
        return
      }
      pushNotice('No saved tailored resume exists for this job yet. Run Tailor resume first.', 'error')
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Could not load the saved tailored resume.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const copyTailoredResumeAction = async () => {
    const content = String(tailoredResume.content ?? '').trim()
    if (!content) {
      pushNotice('Nothing to copy — tailor or load a resume first.', 'error')
      return
    }
    try {
      await navigator.clipboard.writeText(content)
      pushNotice('Tailored resume copied to clipboard.')
    } catch {
      pushNotice('Clipboard copy failed. Select the text and copy manually.', 'error')
    }
  }

  const applyAction = async (jobIds, { openPortal = false, supervised = true, useTailoredResume = true } = {}) => {
    if (!ensureCanModify('Job applications')) {
      return
    }

    if (!jobIds.length) {
      pushNotice('Select at least one job before applying.', 'error')
      return
    }

    const freshJobIds = jobIds.filter((jobId) => {
      const job = results.find((item) => item.id === jobId)
      return isPostedWithin24Hours(job?.posted)
    })

    const staleSkipped = jobIds.length - freshJobIds.length
    if (!freshJobIds.length) {
      pushNotice('Only jobs posted within the last 24 or 48 hours are eligible for apply.', 'warning')
      return
    }
    if (staleSkipped > 0) {
      pushNotice(`Skipped ${staleSkipped} job(s) older than 48 hours.`, 'info')
    }

    const eligibleJobIds = freshJobIds.filter((jobId) => {
      const job = results.find((item) => item.id === jobId)
      const band = getMatchRouteBand(job?.match)
      if (band === 'reject') {
        return false
      }
      if (band === 'tailor') {
        const hasTailored = tailoredJobIds.includes(jobId)
          || (tailoredResume.jobId === jobId && String(tailoredResume.content ?? '').trim().length > 0)
        return hasTailored
      }
      return true
    })

    const blockedCount = freshJobIds.length - eligibleJobIds.length
    if (!eligibleJobIds.length) {
      pushNotice(
        `No eligible jobs to apply. Match routing: ≥${MATCH_POLICY.applyMin}% apply · ${MATCH_POLICY.tailorMin}–${MATCH_POLICY.applyMin - 1}% need Tailored CV · <${MATCH_POLICY.rejectBelow}% rejected.`,
        'warning',
      )
      return
    }
    if (blockedCount > 0) {
      pushNotice(
        `Skipped ${blockedCount} job(s) by match routing (below floor or tailor band without Tailored CV).`,
        'info',
      )
    }

    if (openPortal) {
      freshJobIds
        .map((jobId) => results.find((item) => item.id === jobId)?.sourceUrl)
        .filter(Boolean)
        .forEach((url) => window.open(url, '_blank', 'noopener,noreferrer'))
    }

    setBusyAction('apply')

    try {
      const response = await applyToJobs(eligibleJobIds, { supervised, useTailoredResume })
      const apiRows = response.applications || []
      setApplications((current) => bumpApplicationsState(current, eligibleJobIds, results, apiRows))
      setSelectedJobs([])
      if (response.tailoredJobIds?.length) {
        setTailoredJobIds((current) => Array.from(new Set([...current, ...response.tailoredJobIds.map(Number)])))
      }

      pushNotice(
        response.message
          || (useTailoredResume
            ? 'Background apply started with tailored CV when available.'
            : (response.supervised
              ? 'Background portal apply started.'
              : `${eligibleJobIds.length} application(s) tracked.`)),
      )

      const pendingIds = apiRows
        .filter((row) => ['queued', 'filling', 'needs_attention', 'awaiting_submit'].includes(row.attemptStatus))
        .map((row) => row.id)
        .filter(Boolean)

      const alreadyApplied = apiRows.filter(isAppliedApplicationRow)
      if (alreadyApplied.length) {
        setAppliedToday((n) => n + alreadyApplied.length)
        alreadyApplied.forEach((row) => {
          pushNotice(`Applied on ${row.portal || 'portal'}: ${row.role} @ ${row.company}.`)
        })
      }

      if (pendingIds.length) {
        const terminal = new Set(['applied', 'failed', 'manual', 'demo'])
        const startedAt = Date.now()
        const pollMs = 1500
        const maxMs = 10 * 60 * 1000

        const poll = async () => {
          let remaining = [...pendingIds]
          // Immediate status check so Results can flip to Applied quickly (demo / fast portals)
          await new Promise((resolve) => window.setTimeout(resolve, 400))
          while (remaining.length && Date.now() - startedAt < maxMs) {
            const nextRemaining = []
            for (const applicationId of remaining) {
              try {
                const statusRow = await getJobApplicationStatus(applicationId)
                setApplications((current) => mergeApplicationStatus(current, statusRow))
                if (statusRow.attemptStatus === 'needs_attention') {
                  pushNotice(statusRow.attemptDetail || 'Action needed in the portal browser window.', 'info')
                }
                if (isAppliedApplicationRow(statusRow)) {
                  setAppliedToday((n) => n + 1)
                  pushNotice(`Applied on ${statusRow.portal || 'portal'}: ${statusRow.role} @ ${statusRow.company}.`)
                } else if (statusRow.attemptStatus === 'manual') {
                  pushNotice(statusRow.attemptDetail || 'Tracked in background mode for manual completion.', 'info')
                } else if (statusRow.attemptStatus === 'failed') {
                  pushNotice(statusRow.attemptDetail || `Apply failed for ${statusRow.role}.`, 'error')
                }
                if (!terminal.has(statusRow.attemptStatus) && !isAppliedApplicationRow(statusRow)) {
                  nextRemaining.push(applicationId)
                }
              } catch {
                nextRemaining.push(applicationId)
              }
            }
            remaining = nextRemaining
            if (remaining.length) {
              await new Promise((resolve) => window.setTimeout(resolve, pollMs))
            }
          }
        }

        poll().catch(() => {})
      } else if (!response.supervised && !alreadyApplied.length) {
        setAppliedToday((n) => n + eligibleJobIds.length)
      }
    } catch (error) {
      pushNotice(getErrorMessage(error, 'Apply action failed. Check the backend service.'), 'error')
    } finally {
      setBusyAction('')
    }
  }

  const saveJobAction = async (jobId) => {
    setBusyAction(`save-${jobId}`)
    try {
      const response = await saveJobItem(jobId)
      setSavedJobs((current) =>
        response.saved
          ? [...current, jobId]
          : current.filter((id) => id !== jobId)
      )
      pushNotice(response.message ?? (response.saved ? 'Job saved to favorites.' : 'Job removed from saved list.'))
    } catch {
      // Optimistic local toggle if backend unavailable
      setSavedJobs((current) =>
        current.includes(jobId) ? current.filter((id) => id !== jobId) : [...current, jobId]
      )
      pushNotice(savedJobs.includes(jobId) ? 'Job removed from saved list.' : 'Job saved to favorites.')
    } finally {
      setBusyAction('')
    }
  }

  const removePortal = async (portal) => {
    if (!ensureCanModify('Portal updates')) {
      return
    }

    try {
      await deletePortalItem({ name: portal.name, url: portal.url })
      setPortals((current) => current.filter((item) => !(item.name === portal.name && item.url === portal.url)))
      pushNotice(`Portal '${portal.name}' removed.`)
    } catch {
      setPortals((current) => current.filter((item) => !(item.name === portal.name && item.url === portal.url)))
      pushNotice(`Portal '${portal.name}' removed locally.`)
    }
  }

  const removeCarrier = async (carrier) => {
    if (!ensureCanModify('Carrier updates')) {
      return
    }

    try {
      await deleteCarrierItem({ name: carrier.name, url: carrier.url })
      setCarriers((current) => current.filter((item) => !(item.name === carrier.name && item.url === carrier.url)))
      pushNotice(`Carrier '${carrier.name}' removed.`)
    } catch {
      setCarriers((current) => current.filter((item) => !(item.name === carrier.name && item.url === carrier.url)))
      pushNotice(`Carrier '${carrier.name}' removed locally.`)
    }
  }

  const previewPortalImport = async (file) => {
    const { rows } = await readImportFile(file)
    const validRows = rows.filter((row) => row?.name && row?.url)
    setPortalImportPreview(validRows)
    setPortalUploadName(file?.name ?? '')
    if (!validRows.length) {
      pushNotice('No rows with valid portal URLs found. Rows without http(s) links (e.g. APIs found) are ignored.', 'error')
      return
    }
    const skipped = rows.length - validRows.length
    pushNotice(
      skipped
        ? `Preview ready — ${validRows.length} portal row(s). Skipped ${skipped} row(s) without links.`
        : `Preview ready — ${validRows.length} portal row(s).`,
      'success',
    )
  }

  const confirmPortalImport = async () => {
    if (!portalImportPreview.length) {
      pushNotice('Preview an import before confirming.', 'error')
      return
    }
    if (!ensureCanModify('Portal import')) {
      return
    }

    setBusyAction('importPortals')
    try {
      const response = await importPortalItems(portalImportPreview)
      if (response.portals) {
        setPortals(response.portals)
      }
      setPortalImportPreview([])
      pushNotice(response.message ?? 'Portals imported.')
    } catch {
      pushNotice('Portal import failed.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const previewCarrierImport = async (file) => {
    const { rows } = await readImportFile(file)
    setCarrierImportPreview(rows)
    setCarrierUploadName(file?.name ?? '')
    pushNotice(rows.length ? `Preview ready — ${rows.length} carrier row(s).` : 'No valid carrier rows found.', rows.length ? 'success' : 'error')
  }

  const confirmCarrierImport = async () => {
    if (!carrierImportPreview.length) {
      pushNotice('Preview an import before confirming.', 'error')
      return
    }
    if (!ensureCanModify('Carrier import')) {
      return
    }

    setBusyAction('importCarriers')
    try {
      const response = await importCarrierItems(carrierImportPreview)
      if (response.carriers) {
        setCarriers(response.carriers)
      }
      setCarrierImportPreview([])
      pushNotice(response.message ?? 'Carrier pages imported.')
    } catch {
      pushNotice('Carrier import failed.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const runLinkedInSearchAction = async () => {
    setBusyAction('linkedinSearch')
    try {
      const response = await searchLinkedInJobs(linkedinFilters)
      setLinkedinRows(response.results ?? [])
      pushNotice(response.message ?? 'LinkedIn search refreshed.')
    } catch {
      pushNotice('LinkedIn search failed.', 'error')
    } finally {
      setBusyAction('')
    }
  }

  const linkedinApplyAction = async (job) => {
    if (!ensureCanModify('LinkedIn apply')) {
      return
    }

    try {
      const response = await applyLinkedInJob({
        role: job.role,
        company: job.company,
        easyApply: job.easyApply,
        linkedinUrl: job.linkedinUrl,
      })
      if (response.redirect && job.linkedinUrl) {
        window.open(job.linkedinUrl, '_blank', 'noopener,noreferrer')
      } else {
        setAppliedToday((n) => n + 1)
      }
      pushNotice(response.message ?? 'LinkedIn application processed.')
    } catch {
      if (job.linkedinUrl) {
        window.open(job.linkedinUrl, '_blank', 'noopener,noreferrer')
        pushNotice('Opened LinkedIn posting in a new tab.')
      } else {
        pushNotice('LinkedIn apply failed.', 'error')
      }
    }
  }

  return (
    <div className="page-stack ja-page">
      <section className="ja-module-banner glass-card">
        <div className="ja-module-header">
          <div className="ja-module-intro">
            <p className="fancy-eyebrow">
              <span className="fancy-eyebrow-dot" aria-hidden="true" />
              Job Automation Module
            </p>
            <h3 className="ja-title-fancy">Automate applications across job boards and LinkedIn.</h3>
            <div className="ja-feature-labels" aria-label="Module sections">
              {panelTabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.key}
                    type="button"
                    className={`fancy-label accent-${tab.accent}${activeTab === tab.key ? ' active' : ''}`}
                    onClick={() => setActiveTab(tab.key)}
                  >
                    <Icon size={13} aria-hidden="true" />
                    <span>{tab.shortLabel}</span>
                  </button>
                )
              })}
            </div>
          </div>
          <span className="ja-live-badge">● LIVE</span>
        </div>

        <nav className="ja-fancy-nav" role="tablist" aria-label="Job automation sections">
          {panelTabs.map((tab) => {
            const Icon = tab.icon
            const badge =
              tab.key === 'search' ? tabBadges.search
                : tab.key === 'results' ? tabBadges.results
                  : tab.key === 'linkedin' ? tabBadges.linkedin
                    : tab.key === 'tracker' ? tabBadges.tracker
                      : null
            const badgeClass =
              tab.key === 'results' ? ' green'
                : tab.key === 'tracker' ? ' red'
                  : ''

            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                className={`ja-fancy-nav-item accent-${tab.accent}${activeTab === tab.key ? ' active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                <span className="ja-fancy-nav-icon">
                  <Icon size={17} aria-hidden="true" />
                </span>
                <span className="ja-fancy-nav-copy">
                  <strong>{tab.label}</strong>
                  <small>{tab.hint}</small>
                </span>
                {badge != null && badge > 0 ? (
                  <span className={`tab-count-badge${badgeClass}`}>{badge}</span>
                ) : null}
              </button>
            )
          })}
        </nav>

        <section className="ja-wizard-shell" aria-label="Wizard flow">
          <div className="ja-wizard-header">
            <div>
              <p className="eyebrow">Wizard flow</p>
              <h4>{activeWizardTab.label} ({activeWizardIndex + 1}/{wizardTabs.length})</h4>
            </div>
            <div className="ja-wizard-controls">
              <button
                type="button"
                className="ghost-button"
                onClick={() => goWizardStep('prev')}
                disabled={activeWizardIndex === 0}
              >
                <ChevronLeft size={15} />
                Previous
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => goWizardStep('next')}
                disabled={activeWizardIndex === wizardTabs.length - 1}
              >
                Next
                <ChevronRight size={15} />
              </button>
            </div>
          </div>

          <div className="ja-wizard-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={wizardProgress}>
            <span style={{ width: `${wizardProgress}%` }} />
          </div>

          <div className="ja-wizard-steps">
            {wizardTabs.map((tab, index) => (
              <button
                key={`wizard-${tab.key}`}
                type="button"
                className={`ja-wizard-step${index === activeWizardIndex ? ' active' : ''}${index < activeWizardIndex ? ' done' : ''}`}
                onClick={() => setActiveTab(tab.key)}
              >
                <span className="ja-wizard-step-index">{index + 1}</span>
                <span>{tab.shortLabel}</span>
              </button>
            ))}
          </div>
        </section>
      </section>

      <section className="hero-panel">
        <div>
          <p className="eyebrow">Job Automation</p>
          <h3>Automate applications across job boards and LinkedIn.</h3>
          <p className="hero-copy">Resume optimization, portal scraping, and interview tracking in one workspace.</p>
        </div>
        <div className="hero-grid four-up">
          <div className="metric-tile accent-amber">
            <Briefcase size={18} />
            <strong>{appliedToday}</strong>
            <span>Applied today</span>
          </div>
          <div className="metric-tile accent-teal">
            <TrendingUp size={18} />
            <strong>{results.length}</strong>
            <span>New matches</span>
          </div>
          <div className="metric-tile accent-cobalt">
            <Send size={18} />
            <strong>{applications.stats.interviews}</strong>
            <span>Interviews</span>
          </div>
          <div className="metric-tile accent-amber">
            <Cpu size={18} />
            <strong>{avgMatchScore}%</strong>
            <span>Avg match score</span>
          </div>
        </div>
      </section>

      <ToastStack toasts={toasts} />

      {activeTab === 'profile' ? (
        <section className="page-stack dense">
          <section className="ja-profile-stats">
            <article className="ja-stat-card"><strong>{appliedToday}</strong><span>Applied Today</span></article>
            <article className="ja-stat-card"><strong>{results.length}</strong><span>New Matches</span></article>
            <article className="ja-stat-card"><strong>{applications.stats.interviews}</strong><span>Interviews</span></article>
            <article className="ja-stat-card"><strong>{avgMatchScore}%</strong><span>Avg Match Score</span></article>
          </section>
        <section className="ja-profile-layout dual-grid align-start">
          <div className="ja-profile-left page-stack dense">
            <article className="glass-card ja-resume-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Resume library</p>
                  <h4>Upload multiple CVs — Parse with AI one by one</h4>
                </div>
                {resumes.some((item) => item.isActive) ? (
                  <span className="chip-button static success">Active CV ready</span>
                ) : null}
              </div>

              <label className="ja-resume-upload-zone">
                <input
                  type="file"
                  className="ja-resume-file-input"
                  accept=".pdf,.doc,.docx,.txt"
                  multiple
                  onChange={(event) => {
                    handleResumeFileSelect(event.target.files)
                    event.target.value = ''
                  }}
                />
                <Upload size={32} className="ja-resume-upload-icon" aria-hidden="true" />
                <strong>Upload resumes</strong>
                <p>Select one or many — PDF, DOC, DOCX, TXT (up to 10MB each)</p>
              </label>

              {resumeQueue.length ? (
                <ul className="ja-resume-queue-list">
                  {resumeQueue.map((file, index) => (
                    <li key={`${file.name}-${index}`} className="ja-resume-queue-item">
                      <FileText size={16} aria-hidden="true" />
                      <span>{file.name}</span>
                      <button
                        className="ghost-button"
                        type="button"
                        aria-label={`Remove ${file.name} from queue`}
                        onClick={() => removeQueuedResume(index)}
                      >
                        <X size={14} />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : resumeFileName ? (
                <div className="ja-resume-file-item">
                  <FileText size={16} aria-hidden="true" />
                  <span>{resumeFileName}</span>
                </div>
              ) : (
                <p className="ja-resume-hint">No files staged — or pick an Active CV below to edit its isolated profile.</p>
              )}

              {parseProgress ? (
                <div className="ja-parse-progress" role="status">
                  <LoaderCircle size={16} className="spin" aria-hidden="true" />
                  <span>
                    Parsing {parseProgress.current} of {parseProgress.total}
                    {parseProgress.fileName ? ` — ${parseProgress.fileName}` : ''}
                  </span>
                </div>
              ) : null}

              <div className="button-row ja-resume-actions">
                <button className="primary-button" type="button" disabled={busyAction === 'parseResume'} onClick={parseResumeAction}>
                  <Cpu size={16} />
                  Parse with AI
                </button>
                <button className="ghost-button ja-resume-preview-btn" type="button" onClick={previewResumeAction}>
                  <Eye size={16} />
                  Preview
                </button>
              </div>
              <p className="support-copy">
                Parse with AI extracts contact details and skills for the Active CV, saves them automatically, and keeps you on Profile so you can review the filled fields. Queued files are processed sequentially; the last successful parse becomes Active.
              </p>
            </article>

            <article className="glass-card ja-resume-library">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Stored CVs</p>
                  <h4>
                    {resumes.length
                      ? `${resumes.length} CV${resumes.length === 1 ? '' : 's'} — switch Active to load that profile`
                      : 'No CVs yet'}
                  </h4>
                </div>
              </div>
              {resumes.length ? (
                <ul className="ja-resume-library-list">
                  {resumes.map((resume) => (
                    <li key={resume.id} className={`ja-resume-library-item${resume.isActive ? ' active' : ''}`}>
                      <div className="ja-resume-library-meta">
                        <FileText size={18} aria-hidden="true" />
                        <div>
                          <strong>{resume.fileName}</strong>
                          <span className="support-copy">
                            {resume.profileName ? `${resume.profileName} · ` : ''}
                            {resume.skills?.length ?? 0} skill(s)
                            {resume.mlScore != null ? ` · ${resume.mlScore}% fit` : ''}
                            {resume.experience ? ` · ${resume.experience}` : ''}
                          </span>
                        </div>
                      </div>
                      <div className="ja-resume-library-actions">
                        {resume.isActive ? (
                          <span className="chip-button static success">
                            <CheckCircle2 size={14} aria-hidden="true" />
                            Active
                          </span>
                        ) : (
                          <button
                            className="secondary-button"
                            type="button"
                            disabled={busyAction === `activateResume-${resume.id}`}
                            onClick={() => activateResumeAction(resume.id)}
                          >
                            Set active
                          </button>
                        )}
                        <button
                          className="ghost-button"
                          type="button"
                          aria-label={`Delete ${resume.fileName}`}
                          disabled={busyAction === `deleteResume-${resume.id}`}
                          onClick={() => deleteResumeAction(resume.id)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="support-copy">Upload and parse resumes to build your isolated CV library.</p>
              )}
            </article>

            {(profile.jobTitles ?? []).length || profile.resumeSummary || (profile.resumeSkills ?? []).length || resumeParseResult ? (
              <article className="glass-card ja-resume-parsed-panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Active CV parse</p>
                    <h4>{profile.resumeFileName || 'Parsed details for the Active CV only'}</h4>
                  </div>
                </div>
                {(profile.jobTitles ?? []).length ? (
                  <section className="ja-parsed-block">
                    <h5 className="ja-parsed-label">Present job titles</h5>
                    <div className="chip-wrap inset ja-title-chip-wrap">
                      {profile.jobTitles.map((title) => (
                        <span key={title} className="chip-button static soft">{title}</span>
                      ))}
                    </div>
                  </section>
                ) : null}

                {profile.resumeSummary ? (
                  <section className="ja-parsed-block">
                    <h5 className="ja-parsed-label">Resume summary</h5>
                    <div className="ja-resume-summary-box">{profile.resumeSummary}</div>
                  </section>
                ) : null}

                {(profile.resumeSkills ?? []).length ? (
                  <section className="ja-parsed-block">
                    <h5 className="ja-parsed-label">Parsed skills</h5>
                    <div className="chip-wrap inset ja-skill-chip-wrap">
                      {profile.resumeSkills.map((skill) => (
                        <span key={skill} className="chip-button static success">{skill}</span>
                      ))}
                    </div>
                  </section>
                ) : null}

                {resumeParseResult ? (
                  <section className="ja-parsed-block ja-parse-results">
                    <h5 className="ja-parsed-label">
                      AI parse results
                      {resumeParseResult.mlScore != null ? ` (${resumeParseResult.mlScore}% role fit)` : ''}
                    </h5>
                    {resumeParseResult.matchedSkills?.length ? (
                      <div className="chip-wrap inset">
                        {resumeParseResult.matchedSkills.map((skill) => (
                          <span key={skill} className="chip-button static success">{skill}</span>
                        ))}
                      </div>
                    ) : null}
                    {resumeParseResult.missingSkills?.length ? (
                      <p className="support-copy"><strong>Gaps:</strong> {resumeParseResult.missingSkills.join(', ')}</p>
                    ) : null}
                    {resumeParseResult.insights ? (
                      <p className="support-copy">{resumeParseResult.insights}</p>
                    ) : null}
                    {resumeParseResult.preview ? (
                      <div className="ja-resume-summary-box compact">{resumeParseResult.preview}…</div>
                    ) : null}
                  </section>
                ) : null}
              </article>
            ) : null}
          </div>

          <div className="ja-profile-right page-stack dense">
            <article className="glass-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Active profile</p>
                  <h4>
                    {profile.resumeFileName
                      ? `Editing “${profile.resumeFileName}”`
                      : 'Contact details for the Active CV'}
                  </h4>
                </div>
              </div>
              <p className="support-copy ja-profile-isolation-note">
                Contact details are stored on this CV’s snapshot. Parse with AI saves the profile automatically; use Save active profile only when you edit these fields. Switching Active reloads that CV only — other resumes stay unchanged.
              </p>
              <div className="form-grid two-columns">
                <label>Full name<input value={profile.name} onChange={(event) => updateProfile('name', event.target.value)} /></label>
                <label>Email<input value={profile.email} onChange={(event) => updateProfile('email', event.target.value)} /></label>
                <label>Phone<input value={profile.phone} onChange={(event) => updateProfile('phone', event.target.value)} /></label>
                <label>Location<input value={profile.location} onChange={(event) => updateProfile('location', event.target.value)} /></label>
                <label className="full-width">LinkedIn<input value={profile.linkedin} onChange={(event) => updateProfile('linkedin', event.target.value)} /></label>
              </div>
            </article>

            <div className="button-row">
              <button className="primary-button" type="button" disabled={busyAction === 'saveProfile'} onClick={saveProfileAction}>Save active profile</button>
              <button className="secondary-button" type="button" onClick={() => setActiveTab('search')}>Configure search</button>
            </div>
          </div>
        </section>
        </section>
      ) : null}

      {activeTab === 'search' ? (
        <section className="page-stack dense">
        <section className="dual-grid align-start">
          <article className="glass-card">
            <div className="section-heading inline-actions">
              <div>
                <p className="eyebrow">Search builder</p>
                <h4>Keywords, skills, and presets</h4>
              </div>
              <button className="secondary-button" type="button" onClick={addPresetSearchTitles}>Add preset titles</button>
            </div>
            <TagEditor
              label="Job titles"
              items={searchConfig.titles}
              placeholder="Add target job title"
              onAdd={(value) => addTag('titles', value)}
              onRemove={(value) => removeTag('titles', value)}
            />
            <TagEditor
              label="Required skills (AND)"
              items={searchConfig.requiredSkills}
              placeholder="Add must-have skill"
              onAdd={(value) => addTag('requiredSkills', value)}
              onRemove={(value) => removeTag('requiredSkills', value)}
            />
            <TagEditor
              label="Optional skills (OR)"
              items={searchConfig.optionalSkills}
              placeholder="Add optional skill"
              onAdd={(value) => addTag('optionalSkills', value)}
              onRemove={(value) => removeTag('optionalSkills', value)}
            />
          </article>

          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Work preferences</p>
                <h4>Active profile preferences used for search/apply</h4>
              </div>
            </div>
            <div className="form-grid two-columns">
              <label>
                Total experience
                <input
                  value={profile.experience ?? ''}
                  placeholder="e.g. 8 years"
                  onChange={(event) => updateProfile('experience', event.target.value)}
                />
              </label>
              <label>
                Employment type
                <select
                  value={effectiveEmploymentType || profile.employmentType || 'Both Contract & Full Time'}
                  onChange={(event) => {
                    const value = event.target.value
                    updateProfile('employmentType', value)
                    updateSearchConfig('employmentType', value)
                  }}
                >
                  {PROFILE_EMPLOYMENT_OPTIONS.map((type) => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </label>
              <label>Expected rate<input value={profile.rate} placeholder="$85/hr or $120,000/yr" onChange={(event) => updateProfile('rate', event.target.value)} /></label>
              <label>
                Work authorization
                <select value={profile.visa} onChange={(event) => updateProfile('visa', event.target.value)}>
                  {PROFILE_VISA_OPTIONS.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label className="full-width">
                Work mode preference
                <select value={profile.workMode} onChange={(event) => updateProfile('workMode', event.target.value)}>
                  {PROFILE_WORK_MODE_OPTIONS.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="button-row" style={{ marginTop: 12 }}>
              <button className="secondary-button" type="button" disabled={busyAction === 'saveProfile'} onClick={saveProfileAction}>
                Save active profile preferences
              </button>
            </div>
          </article>

          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Scope</p>
                <h4>Location, filters, and schedule</h4>
              </div>
            </div>
            <div className="form-grid two-columns">
              <label>Location<input value={searchConfig.location} onChange={(event) => updateSearchConfig('location', event.target.value)} /></label>
              <label>
                Radius
                <select value={searchConfig.radius} onChange={(event) => updateSearchConfig('radius', event.target.value)}>
                  {SEARCH_RADIUS_OPTIONS.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label>
                Job posted within
                <select
                  value={['1', '2'].includes(String(searchConfig.postedWithin)) ? String(searchConfig.postedWithin) : '2'}
                  onChange={(event) => updateSearchConfig('postedWithin', event.target.value)}
                >
                  {MATCH_POLICY.postedWindows.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Experience level
                <select value={searchConfig.experienceLevel ?? 'Any'} onChange={(event) => updateSearchConfig('experienceLevel', event.target.value)}>
                  {SEARCH_EXPERIENCE_OPTIONS.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <label>Rate min ($)<input value={searchConfig.rateMin ?? ''} placeholder="e.g. 70" onChange={(event) => updateSearchConfig('rateMin', event.target.value)} /></label>
              <label>Rate max ($)<input value={searchConfig.rateMax ?? ''} placeholder="e.g. 120" onChange={(event) => updateSearchConfig('rateMax', event.target.value)} /></label>
              <label>
                Match score (min {searchConfig.minMatchScore ?? 70}%)
                <input
                  type="range"
                  className="match-threshold-slider"
                  min="50"
                  max="95"
                  value={searchConfig.minMatchScore ?? 70}
                  onChange={(event) => updateSearchConfig('minMatchScore', Number(event.target.value))}
                />
              </label>
              <label>
                Search schedule
                <select
                  value={scheduleSelectValue}
                  onChange={(event) => {
                    const value = event.target.value
                    if (value === CUSTOM_SEARCH_SCHEDULE_OPTION) {
                      const minutes = customScheduleMinutes ?? DEFAULT_CUSTOM_SCHEDULE_MINUTES
                      updateSearchConfig('repeatEvery', `Custom: ${minutes} minutes`)
                      return
                    }
                    updateSearchConfig('repeatEvery', value)
                  }}
                >
                  {SEARCH_REPEAT_OPTIONS.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                  <option value={CUSTOM_SEARCH_SCHEDULE_OPTION}>Custom interval</option>
                </select>
              </label>
              {scheduleSelectValue === CUSTOM_SEARCH_SCHEDULE_OPTION ? (
                <label>
                  Custom interval (minutes)
                  <input
                    type="number"
                    min="5"
                    step="1"
                    value={customScheduleMinutes ?? DEFAULT_CUSTOM_SCHEDULE_MINUTES}
                    onChange={(event) => {
                      const nextMinutes = Math.max(5, Number(event.target.value) || DEFAULT_CUSTOM_SCHEDULE_MINUTES)
                      updateSearchConfig('repeatEvery', `Custom: ${nextMinutes} minutes`)
                    }}
                  />
                </label>
              ) : null}
              <label className="full-span">Advanced filters<input value={searchConfig.filters.join(', ')} onChange={(event) => updateSearchConfig('filters', event.target.value.split(',').map((item) => item.trim()).filter(Boolean))} /></label>
              <div className="full-span exclude-keywords-row">
                <label>
                  Exclude keywords
                  <input
                    value={excludeKeywordsDraft}
                    placeholder="e.g. Clearance, Security (comma-separated)"
                    onChange={(event) => setExcludeKeywordsDraft(event.target.value)}
                    onBlur={() => updateSearchConfig('excludeKeywords', parseExcludeKeywords(excludeKeywordsDraft))}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        runSearchAction()
                      }
                    }}
                  />
                </label>
                <button
                  className="primary-button exclude-keywords-search"
                  type="button"
                  disabled={busyAction === 'runSearch'}
                  onClick={runSearchAction}
                >
                  <Search size={16} />
                  Search
                </button>
              </div>
            </div>
            {searchProgress?.active ? (
              <div className="search-progress-panel">
                <strong>{searchProgress.message}</strong>
                <div className="search-progress-track">
                  <div className="search-progress-fill" style={{ width: `${searchProgress.pct}%` }} />
                </div>
              </div>
            ) : null}
            <div className="button-row">
              <button className="primary-button" type="button" disabled={busyAction === 'saveSearch'} onClick={saveSearchConfigAction}>Save search config</button>
              <button className="primary-button" type="button" disabled={busyAction === 'runSearch'} onClick={runSearchAction}>Run search now</button>
              <button className="secondary-button" type="button" onClick={() => setActiveTab('results')}>View results</button>
            </div>
          </article>
        </section>

        <AutomationSettingsPanel
          automation={automation}
          busyAction={busyAction}
          updateAutomation={updateAutomation}
          ensureCanModify={ensureCanModify}
          saveAutomationSettings={saveAutomationSettings}
          pushNotice={pushNotice}
          handleAutoApplyToggle={handleAutoApplyToggle}
          runAutoApplyAction={runAutoApplyAction}
        />
        </section>
      ) : null}

      {activeTab === 'portals' ? (
        <section className="dual-grid align-start">
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Configured portals</p>
                <h4>Excel upload and portal management</h4>
              </div>
            </div>
            <div className="attachment-dropzone compact-dropzone">
              <strong>Upload portal URLs via Excel</strong>
              <span>{portalUploadName || 'Stage a .xlsx or .csv with portal name + URL columns. Rows without links are skipped.'}</span>
              <div className="button-row">
                <label className="secondary-button file-trigger">
                  <Upload size={16} />
                  Upload file
                  <input
                    type="file"
                    accept=".csv,.xlsx,.txt"
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (file) {
                        previewPortalImport(file)
                      }
                    }}
                  />
                </label>
                <button className="secondary-button" type="button" onClick={confirmPortalImport} disabled={!portalImportPreview.length}>Confirm import</button>
              </div>
            </div>
            {portalImportPreview.length ? (
              <div className="nested-card page-stack dense">
                <strong>Import preview ({portalImportPreview.length} rows with valid URLs)</strong>
                {portalImportPreview.map((row, index) => (
                  <div key={`${row.name}-${row.url}-${index}`} className="list-card list-card-inline">
                    <div><strong>{row.name}</strong><p>{row.url}</p></div>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="card-list compact-list">
              {portals.map((portal) => (
                <div key={`${portal.name}-${portal.url}`} className="list-card list-card-inline">
                  <span className="portal-avatar">{getPortalInitials(portal.name)}</span>
                  <div>
                    <strong>{portal.name}</strong>
                    <p>{portal.url}</p>
                  </div>
                  <div className="button-row compact-actions">
                    <button
                      type="button"
                      className={`status-toggle${(portal.status ?? 'Active') === 'Active' ? ' active' : ' paused'}`}
                      onClick={() => togglePortalStatus(portal)}
                    >
                      {portal.status ?? 'Active'}
                    </button>
                    <button className="secondary-button icon-button" type="button" onClick={() => removePortal(portal)} aria-label={`Remove ${portal.name}`}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="form-grid two-columns compact-gap">
              <label>Portal name<input value={portalDraft.name} onChange={(event) => setPortalDraft((current) => ({ ...current, name: event.target.value }))} /></label>
              <label>Portal URL<input value={portalDraft.url} onChange={(event) => setPortalDraft((current) => ({ ...current, url: event.target.value }))} /></label>
            </div>
            <button className="primary-button" type="button" disabled={busyAction === 'addPortal'} onClick={addPortalAction}>Add portal</button>
          </article>

          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Carrier pages</p>
                <h4>Client career sites</h4>
              </div>
            </div>
            <div className="attachment-dropzone compact-dropzone">
              <strong>Upload career pages via Excel/CSV</strong>
              <span>{carrierUploadName || 'Stage a .xlsx or .csv source for batch ingestion.'}</span>
              <div className="button-row">
                <label className="secondary-button file-trigger">
                  <Upload size={16} />
                  Upload file
                  <input
                    type="file"
                    accept=".csv,.xlsx,.txt"
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (file) {
                        previewCarrierImport(file)
                      }
                    }}
                  />
                </label>
                <button className="secondary-button" type="button" onClick={confirmCarrierImport} disabled={!carrierImportPreview.length}>Confirm import</button>
              </div>
            </div>
            {carrierImportPreview.length ? (
              <div className="nested-card page-stack dense">
                <strong>Import preview ({carrierImportPreview.length} rows)</strong>
                {carrierImportPreview.map((row) => (
                  <div key={`${row.name}-${row.url}`} className="list-card list-card-inline">
                    <div><strong>{row.name}</strong><p>{row.url}</p></div>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="card-list compact-list">
              {carriers.map((carrier) => (
                <div key={`${carrier.name}-${carrier.url}`} className="list-card list-card-inline">
                  <span className="portal-avatar">{getPortalInitials(carrier.name)}</span>
                  <div>
                    <strong>{carrier.name}</strong>
                    <p>{carrier.url}</p>
                  </div>
                  <div className="button-row compact-actions">
                    <span className="monitoring-badge">{carrier.status ?? 'Monitoring'}</span>
                    <button className="secondary-button icon-button" type="button" onClick={() => removeCarrier(carrier)} aria-label={`Remove ${carrier.name}`}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="form-grid two-columns compact-gap">
              <label>Carrier name<input value={carrierDraft.name} onChange={(event) => setCarrierDraft((current) => ({ ...current, name: event.target.value }))} /></label>
              <label>Carrier URL<input value={carrierDraft.url} onChange={(event) => setCarrierDraft((current) => ({ ...current, url: event.target.value }))} /></label>
            </div>
            <button className="primary-button" type="button" disabled={busyAction === 'addCarrier'} onClick={addCarrierAction}>Add carrier</button>
          </article>
        </section>
      ) : null}

      {activeTab === 'results' ? (
        <section className="page-stack dense">
          <div className="section-heading inline-actions">
            <div>
              <p className="eyebrow">Matched roles</p>
              <h4>
                {filteredResults.length} qualified results
                {results.length && filteredResults.length !== results.length
                  ? ` · ${results.length} total`
                  : ''}
              </h4>
              <p className="support-copy" style={{ marginTop: 4 }}>
                Employment filter: <strong>{formatEmploymentTypeLabel(effectiveEmploymentType)}</strong>
                {' · '}only posts within the last 48 hours.
                {' · '}Match routing: ≥{MATCH_POLICY.applyMin}% apply · {MATCH_POLICY.tailorMin}–{MATCH_POLICY.applyMin - 1}% tailor · &lt;{MATCH_POLICY.rejectBelow}% reject.
                {' · '}Minimum match score is configured on Search.
              </p>
            </div>
            {filteredResults.length ? (
              <div className="button-row">
                <button className="secondary-button" type="button" onClick={() => setSelectedJobs(filteredResults.map((job) => job.id))}>Select all filtered</button>
                  <button className="primary-button" type="button" disabled={busyAction === 'apply'} onClick={() => applyAction(selectedJobs.length ? selectedJobs : filteredResults.map((job) => job.id), { openPortal: false, supervised: true })}>
                    <Send size={16} />
                    Apply selected ({selectedJobs.length || filteredResults.length})
                  </button>
              </div>
            ) : null}
          </div>

          {matchingPipeline ? (
            <article className={`ja-tracker-banner${matchingPipeline.llmUsed ? ' success' : ' warning'}`}>
              <div>
                <strong>
                  CV ↔ job matching pipeline
                  {' · '}
                  {formatPipelineMatchSource(matchingPipeline.matchSource, matchingPipeline.llmUsed)}
                </strong>
                <p>{matchingPipeline.message}</p>
                {matchingPipeline.embeddingModel ? (
                  <p className="support-copy" style={{ marginTop: 4 }}>
                    Embeddings: <strong>{matchingPipeline.embeddingModel.split('/').pop()}</strong>
                    {matchingPipeline.llmProvider && matchingPipeline.llmUsed
                      ? ` · LLM: ${matchingPipeline.llmProvider}`
                      : null}
                  </p>
                ) : null}
                {matchingPipeline.steps?.length ? (
                  <div className="chip-wrap inset" style={{ marginTop: 8 }}>
                    {matchingPipeline.steps.map((step) => (
                      <span key={step} className="chip-button static soft">{step.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                ) : null}
                {!matchingPipeline.llmUsed ? (
                  <p className="support-copy" style={{ marginTop: 8 }}>
                    Start <strong>Ollama</strong> with <code>ollama run mistral</code> (USE_LOCAL_LLM=true)
                    or add <strong>OPENAI_API_KEY</strong> to <code>backend/.env</code> for ranking explanations.
                  </p>
                ) : null}
              </div>
            </article>
          ) : null}

          <article className="glass-card">
            <div className="form-grid results-filter-grid">
              <label className="full-span">
                AI / resume search keywords
                <textarea
                  rows={3}
                  value={resultsFilter.query}
                  onChange={(event) => setResultsFilter((current) => ({ ...current, query: event.target.value }))}
                  placeholder="Java, Spring Boot, AWS"
                />
                <span className="support-copy">AI-parsed and search skills are displayed as comma-separated keywords. A result matches any keyword.</span>
              </label>
              <label>
                Employment type (from Search config)
                <input value={effectiveEmploymentType} disabled />
              </label>
              <label>
                Sort by
                <select value={resultsFilter.sort} onChange={(event) => setResultsFilter((current) => ({ ...current, sort: event.target.value }))}>
                  <option value="match">Match score</option>
                  <option value="recent">Most recent</option>
                  <option value="company">Company</option>
                  <option value="rate">Highest rate</option>
                </select>
              </label>
              <div className="full-span exclude-keywords-row">
                <label>
                  Exclude keywords
                  <input
                    value={resultsFilter.excludeKeywords.join(', ')}
                    placeholder="e.g. Clearance, Security"
                    onChange={(event) => setResultsFilter((current) => ({
                      ...current,
                      excludeKeywords: parseExcludeKeywords(event.target.value),
                    }))}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault()
                        const excludeKeywords = resultsFilter.excludeKeywords
                        setActiveTab('search')
                        runSearchAction({
                          excludeKeywordsDraft: excludeKeywords.join(', '),
                          searchConfig: { ...searchConfig, excludeKeywords },
                        })
                      }
                    }}
                  />
                </label>
                <button
                  className="primary-button exclude-keywords-search"
                  type="button"
                  disabled={busyAction === 'runSearch'}
                  onClick={() => {
                    const excludeKeywords = resultsFilter.excludeKeywords
                    setExcludeKeywordsDraft(excludeKeywords.join(', '))
                    setSearchConfig((current) => ({ ...current, excludeKeywords }))
                    setActiveTab('search')
                    runSearchAction({
                      excludeKeywordsDraft: excludeKeywords.join(', '),
                      searchConfig: { ...searchConfig, excludeKeywords },
                    })
                  }}
                >
                  <Search size={16} />
                  Search
                </button>
              </div>
            </div>
          </article>

          {!results.length ? (
            <article className="glass-card ja-tracker-empty">
              <Briefcase size={28} aria-hidden="true" />
              <strong>No search results yet</strong>
              <p>Run a job search to populate matched roles from Dice and your other configured portals.</p>
              <button className="primary-button" type="button" onClick={() => setActiveTab('search')}>
                <Search size={16} />
                Go to Job Search
              </button>
            </article>
          ) : !filteredResults.length ? (
            <article className="glass-card ja-tracker-empty">
              <Briefcase size={28} aria-hidden="true" />
              <strong>No roles match employment type / 48h policy</strong>
              <p>
                {results.length} result(s) were returned, but none match{' '}
                <strong>{effectiveEmploymentType}</strong> and the ≤48 hour match-routing window
                (or your active Results filters).
              </p>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setResultsFilter((current) => ({
                  ...current,
                  query: '',
                  excludeKeywords: [],
                }))}
              >
                Clear Results filters
              </button>
            </article>
          ) : (
            <div className="card-grid two-up">
              {filteredResults.map((job) => {
                const applyState = getResultApplyState(applications, job)
                const isApplied = Boolean(applyState?.applied)
                const isApplying = Boolean(applyState?.busy)
                const routeBand = getMatchRouteBand(job.match)
                const hasTailoredCv = tailoredJobIds.includes(job.id)
                  || (tailoredResume.jobId === job.id && String(tailoredResume.content ?? '').trim().length > 0)
                const showTailoredApply = hasTailoredCv && !isApplied && routeBand !== 'reject'
                return (
                <article key={job.id} className={`glass-card selectable${selectedJobs.includes(job.id) ? ' selected' : ''}${isApplied ? ' ja-result-applied' : ''}`}>
                  <div className="job-card-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedJobs.includes(job.id)}
                      onChange={() => toggleJob(job.id)}
                      aria-label={`Select ${job.role} at ${job.company}`}
                      disabled={isApplied}
                    />
                    <div style={{ flex: 1 }}>
                  <div className="module-header">
                    <div>
                      <h4>{job.role}{job.hot ? <span className="chip-button static hot" style={{ marginLeft: 8, fontSize: 11 }}>🔥 Hot</span> : null}</h4>
                      <p>{job.company} · {job.location}</p>
                      {job.portalName ? <p className="support-copy">Portal: {job.portalName}</p> : null}
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      {applyState ? (
                        <span className={`ja-tracker-status ${applyState.tone}`} style={{ marginBottom: 6, display: 'inline-flex' }}>
                          {applyState.label}
                        </span>
                      ) : null}
                      {routeBand === 'apply' ? (
                        <span className="chip-button static success" style={{ marginBottom: 6, display: 'inline-flex' }}>{getMatchRouteLabel(routeBand)}</span>
                      ) : routeBand === 'tailor' ? (
                        <span className="chip-button static soft" style={{ marginBottom: 6, display: 'inline-flex' }}>{getMatchRouteLabel(routeBand)}</span>
                      ) : (
                        <span className="chip-button static danger" style={{ marginBottom: 6, display: 'inline-flex' }}>{getMatchRouteLabel(routeBand)}</span>
                      )}
                      {hasTailoredCv ? (
                        <span className="chip-button static success" style={{ marginBottom: 6, marginLeft: 4, display: 'inline-flex' }}>Tailored CV ready</span>
                      ) : null}
                      <span className="metric-chip">{job.match}% match</span>
                      {job.matchSource ? (
                        <p className="support-copy" style={{ marginTop: 4, fontSize: 11 }}>
                          {formatMatchSource(job.matchSource)}
                        </p>
                      ) : null}
                      {job.rate ? <p style={{ fontSize: 12, fontWeight: 600, color: '#059669', marginTop: 4 }}>{job.rate}</p> : null}
                    </div>
                  </div>
                  {job.matchInsight ? (
                    <p className="support-copy" style={{ marginBottom: 8 }}>{job.matchInsight}</p>
                  ) : null}
                  <div className="chip-wrap inset">
                    <span className="chip-button static">{formatEmploymentTypeLabel(job.type)}</span>
                    <span className="chip-button static">{formatPostedAgeLabel(job.posted)}</span>
                    {job.portalName ? <span className="chip-button static soft">{job.portalName}</span> : null}
                    {isApplied ? <span className="chip-button static ja-applied-chip">Applied</span> : null}
                  </div>
                  {job.sourceUrl ? (
                    <a className="inline-link" href={job.sourceUrl} target="_blank" rel="noreferrer">View on {job.portalName ?? 'portal'}</a>
                  ) : null}
                  <div className="progress-track"><div className="progress-fill" style={{ width: `${job.match}%` }} /></div>
                  <div className="chip-wrap inset">
                    {job.skills.map((skill) => <span key={skill} className="chip-button static soft">{skill}</span>)}
                  </div>
                  <div className="button-row wrap-actions">
                    {routeBand === 'apply' ? (
                      <button
                        className={isApplied ? 'secondary-button' : 'primary-button'}
                        type="button"
                        disabled={busyAction === 'apply' || isApplied || isApplying}
                        title={
                          isApplied
                            ? `Already applied on ${job.portalName || 'portal'}`
                            : `Match ≥${MATCH_POLICY.applyMin}% — quick apply in background`
                        }
                        onClick={() => applyAction([job.id], { openPortal: false, supervised: true, useTailoredResume: hasTailoredCv })}
                      >
                        {isApplied ? (
                          <>
                            <CheckCircle2 size={16} />
                            Applied
                          </>
                        ) : isApplying ? (
                          <>
                            <LoaderCircle size={16} className="spin" />
                            Applying…
                          </>
                        ) : (
                          'Quick apply'
                        )}
                      </button>
                    ) : null}
                    {routeBand === 'tailor' && !hasTailoredCv && !isApplied ? (
                      <button
                        className="secondary-button"
                        type="button"
                        title="Match is in the tailor band — open Analyzer to update CV for this JD"
                        onClick={() => openJobInAnalyzer(job)}
                      >
                        <WandSparkles size={16} />
                        Tailor CV
                      </button>
                    ) : null}
                    {showTailoredApply ? (
                      <button
                        className="primary-button"
                        type="button"
                        disabled={busyAction === 'apply' || isApplying}
                        title="Apply using the Analyzer-updated tailored CV for this job description"
                        onClick={() => applyAction([job.id], { openPortal: false, supervised: true, useTailoredResume: true })}
                      >
                        {isApplying ? (
                          <>
                            <LoaderCircle size={16} className="spin" />
                            Applying…
                          </>
                        ) : (
                          <>
                            <WandSparkles size={16} />
                            Apply with Tailored CV
                          </>
                        )}
                      </button>
                    ) : null}
                    {routeBand === 'reject' && !isApplied ? (
                      <button className="secondary-button" type="button" disabled title={`Match below ${MATCH_POLICY.rejectBelow}% — rejected by routing policy`}>
                        Below match floor
                      </button>
                    ) : null}
                    <button className="secondary-button" type="button" onClick={() => openJobInAnalyzer(job)}>Analyze</button>
                    <button
                      className="secondary-button icon-button"
                      type="button"
                      disabled={busyAction === `save-${job.id}`}
                      onClick={() => saveJobAction(job.id)}
                      title={savedJobs.includes(job.id) ? 'Remove from saved' : 'Save to favorites'}
                      aria-label={savedJobs.includes(job.id) ? 'Remove from saved' : 'Save to favorites'}
                    >
                      {savedJobs.includes(job.id) ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                    </button>
                  </div>
                    </div>
                  </div>
                </article>
                )
              })}
            </div>
          )}
        </section>
      ) : null}

      {activeTab === 'analyzer' ? (
        <section className="page-stack dense analyzer-tab">
          <div className="dual-grid align-start">
          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Job Analyzer & Match Scores</p>
                <h4>Connect to the portal posting and score your CV against the live job description</h4>
              </div>
            </div>
            <label>
              Optional job reference
              <select
                value={analysisJobId ?? ''}
                onChange={async (event) => {
                  const id = event.target.value ? Number(event.target.value) : null
                  setAnalysisJobId(id)
                  setHasAnalyzed(false)
                  if (!id) {
                    return
                  }
                  const job = results.find((row) => row.id === id)
                  if (job?.description) {
                    setJobDescriptionText(job.description)
                    setAnalyzerDraft(job.description)
                  }
                  // Connect to the portal/vendor website and fill Job description.
                  await fetchJobDescriptionFromPortal(id)
                  try {
                    const saved = await getTailoredResume(id)
                    if (saved.found && String(saved.content ?? '').trim()) {
                      setTailoredResume((current) => ({
                        content: saved.content,
                        jobId: id,
                        score: current.jobId === id ? current.score : null,
                      }))
                      setTailoredJobIds((current) => Array.from(new Set([...current, id])))
                      pushNotice('Loaded saved tailored resume for this job.')
                    }
                  } catch {
                    // Non-blocking: job selection still works without a saved resume.
                  }
                }}
              >
                <option value="">Manual job description only</option>
                {results.map((job) => (
                  <option key={job.id} value={job.id}>{job.role} · {job.company}</option>
                ))}
              </select>
            </label>
            {selectedJob && analysisJobId ? (
              <div className="nested-card page-stack dense">
                <strong>{selectedJob.role}</strong>
                <p>{selectedJob.company} · {selectedJob.location}</p>
                {selectedJob.portalName ? (
                  <p className="support-copy">Portal: {selectedJob.portalName}</p>
                ) : null}
                {selectedJob.sourceUrl ? (
                  <a className="inline-link" href={selectedJob.sourceUrl} target="_blank" rel="noreferrer">
                    Open original posting
                  </a>
                ) : (
                  <p className="support-copy">No portal detail URL available for this result.</p>
                )}
                <div className="chip-wrap inset">
                  {(selectedJob.skills || []).map((skill) => <span key={skill} className="chip-button static soft">{skill}</span>)}
                  {String(jobDescriptionText || '').trim().length >= 180 ? (
                    <span className="chip-button static success">Full JD loaded</span>
                  ) : (
                    <span className="chip-button static soft">JD may be incomplete</span>
                  )}
                </div>
              </div>
            ) : null}
            <label>
              Job description
              <textarea
                className="job-description-area"
                rows={12}
                value={jobDescriptionText}
                onChange={(event) => {
                  setJobDescriptionText(event.target.value)
                  setAnalyzerDraft(event.target.value)
                }}
                placeholder="Select a scraped job to auto-fetch the portal JD, or paste the full job description here."
              />
            </label>
            <div className="button-row wrap-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={!analysisJobId || busyAction === 'fetchJd' || !selectedJob?.sourceUrl}
                onClick={() => fetchJobDescriptionFromPortal(analysisJobId)}
                title={selectedJob?.sourceUrl ? 'Fetch exact JD from the portal/vendor website' : 'Selected job has no portal URL'}
              >
                {busyAction === 'fetchJd' ? <LoaderCircle size={16} className="spin" /> : <Globe size={16} />}
                Fetch JD from portal
              </button>
              <button className="primary-button" type="button" disabled={busyAction === 'analyze'} onClick={() => analyzeAction(analysisJobId)}>
                <Cpu size={16} />
                Analyze CV match
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={busyAction === 'tailor' || !hasAnalyzed || !analysisJobId}
                onClick={tailorResumeAction}
                title={
                  !analysisJobId
                    ? 'Select a job reference first'
                    : hasAnalyzed
                      ? 'Generate a tailored resume for this analysis'
                      : 'Run CV analysis first'
                }
              >
                {busyAction === 'tailor' ? <LoaderCircle size={16} className="spin" /> : <WandSparkles size={16} />}
                Tailor resume
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={!String(tailoredResume.content ?? '').trim() || busyAction === 'saveTailored' || !(tailoredResume.jobId || analysisJobId)}
                onClick={saveTailoredResumeAction}
                title="Save the current tailored text for this job"
              >
                {busyAction === 'saveTailored' ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
                Save updated resume
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={!String(tailoredResume.content ?? '').trim()}
                onClick={previewTailoredResumeAction}
                title="Open full tailored CV preview"
              >
                <Eye size={16} />
                Preview tailored CV
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={!String(tailoredResume.content ?? '').trim()}
                onClick={downloadTailoredResumeAction}
                title="Download tailored resume as .txt"
              >
                <Download size={16} />
                Download tailored resume
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={!analysisJobId || busyAction === 'loadTailored'}
                onClick={() => loadTailoredResumeAction(analysisJobId)}
                title={analysisJobId ? 'Load the last saved tailored resume for this job' : 'Select a job reference first'}
              >
                {busyAction === 'loadTailored' ? <LoaderCircle size={16} className="spin" /> : <Upload size={16} />}
                Load saved tailored resume
              </button>
            </div>
            {String(tailoredResume.content ?? '').trim() ? (
              <div className="nested-card">
                <div className="section-heading dense">
                  <div>
                    <strong>Tailored resume draft {tailoredResume.score ? `(${tailoredResume.score}% match)` : ''}</strong>
                    <p className="support-copy">Edit below, then Save, Preview, or Download.</p>
                  </div>
                  <button className="secondary-button" type="button" onClick={previewTailoredResumeAction}>
                    <Eye size={16} />
                    Open preview
                  </button>
                </div>
                <textarea
                  className="code-block"
                  rows={14}
                  aria-label="Tailored resume content"
                  value={tailoredResume.content}
                  onChange={(event) => setTailoredResume((current) => ({ ...current, content: event.target.value }))}
                />
              </div>
            ) : null}
          </article>

          {showTailoredPreview && String(tailoredResume.content ?? '').trim() ? (
            <div
              className="analyzer-preview-overlay"
              role="dialog"
              aria-modal="true"
              aria-label="Tailored CV preview"
              onClick={(event) => {
                if (event.target === event.currentTarget) {
                  setShowTailoredPreview(false)
                }
              }}
            >
              <div className="analyzer-preview-panel">
                <div className="analyzer-preview-header">
                  <div>
                    <p className="eyebrow">Tailored CV</p>
                    <h4>
                      Preview
                      {tailoredResume.score ? ` · ${tailoredResume.score}% estimated match` : ''}
                    </h4>
                  </div>
                  <button
                    className="secondary-button icon-button"
                    type="button"
                    aria-label="Close preview"
                    onClick={() => setShowTailoredPreview(false)}
                  >
                    <X size={18} />
                  </button>
                </div>
                <textarea
                  className="code-block analyzer-preview-body"
                  rows={22}
                  aria-label="Tailored resume preview content"
                  value={tailoredResume.content}
                  onChange={(event) => setTailoredResume((current) => ({ ...current, content: event.target.value }))}
                />
                <div className="button-row wrap-actions analyzer-preview-actions">
                  <button className="secondary-button" type="button" onClick={copyTailoredResumeAction}>
                    <Copy size={16} />
                    Copy
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busyAction === 'saveTailored' || !(tailoredResume.jobId || analysisJobId)}
                    onClick={saveTailoredResumeAction}
                  >
                    <Save size={16} />
                    Save
                  </button>
                  <button className="secondary-button" type="button" onClick={downloadTailoredResumeAction}>
                    <Download size={16} />
                    Download
                  </button>
                  <button className="primary-button" type="button" onClick={() => setShowTailoredPreview(false)}>
                    Close
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Analysis result</p>
                <h4>{hasAnalyzed ? `${analysisResult.score}% match score${analysisResult.tailoredScore ? ` → ${analysisResult.tailoredScore}% tailored` : ''}` : 'Run analysis to see match insights'}</h4>
                {hasAnalyzed && (analysisResult.platform || analysisResult.matchSource) ? (
                  <p className="support-copy">
                    {analysisResult.platform ? `${analysisResult.platform} posting` : 'Job board'}
                    {analysisResult.matchSource ? ` · scored via ${analysisResult.matchSource}` : ''}
                    {analysisResult.sourceUrl ? (
                      <>
                        {' · '}
                        <a href={analysisResult.sourceUrl} target="_blank" rel="noopener noreferrer">Open original</a>
                      </>
                    ) : null}
                  </p>
                ) : null}
              </div>
            </div>
            {!hasAnalyzed ? (
              <div className="analyzer-placeholder">
                <Cpu size={42} />
                <strong>No analysis yet</strong>
                <p>Select a scraped job (or paste a full JD). Analyze loads the portal job description, then Tailor resume adds JD-aligned experience pointers without rewriting your employment history.</p>
              </div>
            ) : (
              <>
            <div className="analyzer-summary-tiles">
              <div className="analyzer-summary-tile matched">
                <strong>{analysisResult.hits.length}</strong>
                <span>Matched keywords</span>
              </div>
              <div className="analyzer-summary-tile missed">
                <strong>{(analysisResult.missingKeywords?.length || analysisResult.misses.length)}</strong>
                <span>Missing keywords</span>
              </div>
            </div>
            <div
              className="match-score-circle"
              style={{ '--pct': `${Math.round((analysisResult.score / 100) * 360)}deg` }}
            >
              <div><strong>{analysisResult.score}%</strong><span>match</span></div>
            </div>
            <p className="support-copy">{analysisResult.summary}</p>
            <div className="dual-grid analysis-grid">
              <div className="nested-card">
                <strong>Matched keywords ({analysisResult.hits.length})</strong>
                <div className="chip-wrap inset">
                  {analysisResult.hits.map((hit) => <span key={hit} className="chip-button static success">{hit}</span>)}
                </div>
              </div>
              <div className="nested-card">
                <strong>Missing keywords ({(analysisResult.missingKeywords?.length || analysisResult.misses.length)})</strong>
                <div className="chip-wrap inset">
                  {(analysisResult.missingKeywords?.length ? analysisResult.missingKeywords : analysisResult.misses).map((miss) => (
                    <span key={miss} className="chip-button static danger">{miss}</span>
                  ))}
                </div>
              </div>
            </div>
            {analysisResult.experienceMatch ? (
              <div className="nested-card" style={{ marginTop: 8 }}>
                <strong>Experience match</strong>
                <p style={{ fontSize: 12, color: '#4b5563', marginTop: 4 }}>{analysisResult.experienceMatch}</p>
              </div>
            ) : null}
            {analysisResult.titleMatch ? (
              <div className="nested-card" style={{ marginTop: 8 }}>
                <strong>Title alignment</strong>
                <p style={{ fontSize: 12, color: '#4b5563', marginTop: 4 }}>{analysisResult.titleMatch}</p>
              </div>
            ) : null}
            {analysisResult.skillGaps?.length ? (
              <div className="nested-card" style={{ marginTop: 8 }}>
                <strong>Skill gaps</strong>
                <div className="chip-wrap inset">
                  {analysisResult.skillGaps.map((gap) => <span key={gap} className="chip-button static danger">{gap}</span>)}
                </div>
              </div>
            ) : null}
            <div className="section-heading inline-actions" style={{ marginTop: 12 }}>
              <div>
                <strong>Resume tailor suggestions</strong>
                <p className="support-copy">Apply role-aligned tweaks without rewriting your employment history.</p>
              </div>
              <button className="secondary-button btn-sm" type="button" onClick={applyAllSuggestions}>Apply all suggestions</button>
            </div>
            <div className="card-list compact-list">
              {(analysisResult.recommendations ?? analysisResult.suggestions).map((item, idx) => (
                <div key={item} className="list-card">
                  <div>
                    <strong>Suggestion {idx + 1}{appliedSuggestions.includes(item) ? ' ✓' : ''}</strong>
                    <p>{item}</p>
                  </div>
                  <button
                    className="secondary-button btn-sm"
                    type="button"
                    style={{ flexShrink: 0 }}
                    onClick={() => applySuggestionToDraft(item)}
                  >
                    Apply
                  </button>
                </div>
              ))}
            </div>
              </>
            )}
          </article>
          </div>

          <article className="glass-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Application autofill</p>
                <h4>Reviewable field map for repeated applications</h4>
                <p className="support-copy">
                  Contact fields autofill by default. Work authorization and other sensitive answers stay locked until you approve them.
                </p>
              </div>
              <button
                className="secondary-button"
                type="button"
                disabled={busyAction === 'autofill'}
                onClick={() => loadAutofillPreviewAction()}
              >
                {busyAction === 'autofill' ? <LoaderCircle size={16} className="spin" /> : <FileText size={16} />}
                {autofillPreview ? 'Refresh autofill' : 'Build autofill preview'}
              </button>
            </div>
            {!autofillPreview ? (
              <div className="analyzer-placeholder">
                <FileText size={36} />
                <strong>No autofill map yet</strong>
                <p>Analyze a job or click Build autofill preview to populate fields from your profile.</p>
              </div>
            ) : (
              <>
                <div className="analyzer-summary-tiles">
                  <div className="analyzer-summary-tile matched">
                    <strong>{autofillPreview.autoFillCount ?? 0}</strong>
                    <span>Ready to fill</span>
                  </div>
                  <div className="analyzer-summary-tile missed">
                    <strong>{autofillPreview.reviewCount ?? 0}</strong>
                    <span>Needs review</span>
                  </div>
                </div>
                <p className="support-copy">{autofillPreview.message}</p>
                <div className="card-list compact-list autofill-field-list">
                  {(autofillPreview.fields || []).map((field) => (
                    <div key={field.key} className={`list-card autofill-field-row ${field.requiresReview ? 'needs-review' : ''}`}>
                      <div>
                        <strong>
                          {field.label}
                          {field.sensitive ? ' · sensitive' : ''}
                        </strong>
                        <p>{field.value}</p>
                        <span className={`autofill-status ${field.status}`}>
                          {field.status === 'approved' ? 'Approved for autofill' : 'Held for review'}
                        </span>
                      </div>
                      {field.requiresReview ? (
                        <button
                          className="secondary-button btn-sm"
                          type="button"
                          onClick={() => toggleAutofillApproval(field.key)}
                        >
                          {field.approved ? 'Revoke' : 'Approve'}
                        </button>
                      ) : (
                        <span className="chip-button static success">Auto</span>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
          </article>
        </section>
      ) : null}

      {activeTab === 'linkedin' ? (
        <section className="page-stack dense">
          <div className="linkedin-panel-header">
            <div>
              <strong>LinkedIn Job Search</strong>
              <p style={{ margin: '4px 0 0', fontSize: 12, opacity: 0.9 }}>Connected account · Easy Apply and filtered discovery</p>
            </div>
            <span className="linkedin-connected-badge">Connected</span>
          </div>
          <article className="glass-card">
            <div className="form-grid linkedin-filter-grid">
              <label>Search LinkedIn roles<input value={linkedinFilters.query} onChange={(event) => setLinkedinFilters((current) => ({ ...current, query: event.target.value }))} placeholder="Role, company, location" /></label>
              <label>Company<input value={linkedinFilters.company} onChange={(event) => setLinkedinFilters((current) => ({ ...current, company: event.target.value }))} placeholder="Filter by company" /></label>
              <label>
                Experience level
                <select value={linkedinFilters.experienceLevel} onChange={(event) => setLinkedinFilters((current) => ({ ...current, experienceLevel: event.target.value }))}>
                  {LINKEDIN_EXPERIENCE_LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>{level.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Sort by
                <select value={linkedinSort} onChange={(event) => setLinkedinSort(event.target.value)}>
                  {LINKEDIN_SORT_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Employment type
                <select value={linkedinFilters.employmentType} onChange={(event) => setLinkedinFilters((current) => ({ ...current, employmentType: event.target.value }))}>
                  <option value="all">All types</option>
                  {PROFILE_EMPLOYMENT_OPTIONS.map((type) => (
                    <option key={type} value={type.toLowerCase()}>{type}</option>
                  ))}
                </select>
              </label>
              <label>
                Date posted
                <select value={linkedinFilters.datePosted} onChange={(event) => setLinkedinFilters((current) => ({ ...current, datePosted: event.target.value }))}>
                  {LINKEDIN_DATE_POSTED.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <div className="toggle-stack">
                <AutomationToggle
                  label="Under 10 applicants"
                  hint="Show only roles with fewer than 10 applicants."
                  enabled={linkedinFilters.under10Applicants}
                  onToggle={() => setLinkedinFilters((current) => ({ ...current, under10Applicants: !current.under10Applicants }))}
                />
                <AutomationToggle
                  label="Easy Apply only"
                  hint="Filter to roles with one-click application."
                  enabled={linkedinFilters.easyApplyOnly}
                  onToggle={() => setLinkedinFilters((current) => ({ ...current, easyApplyOnly: !current.easyApplyOnly }))}
                />
              </div>
              <div className="button-row">
                <button className="primary-button" type="button" disabled={busyAction === 'linkedinSearch'} onClick={runLinkedInSearchAction}>Search LinkedIn</button>
              </div>
            </div>
          </article>
          <section className="card-grid three-up">
            {filteredLinkedin.map((job) => (
              <article key={`${job.role}-${job.company}`} className="glass-card">
                <div className="module-header">
                  <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span className="company-avatar">{getCompanyInitials(job.company)}</span>
                    <div>
                    <h4>{job.role}</h4>
                    <p>{job.company}</p>
                    </div>
                  </div>
                  {job.match != null ? <span className="metric-chip">{job.match}%</span> : null}
                </div>
                <div className="chip-wrap inset">
                  {job.type ? <span className="chip-button static">{job.type}</span> : null}
                  <span className="chip-button static">{job.location}</span>
                  {job.posted ? <span className="chip-button static">{job.posted}</span> : null}
                  {job.experienceLevel ? <span className="chip-button static soft">{job.experienceLevel}</span> : null}
                  {job.easyApply ? <span className="chip-button static success">Easy Apply</span> : null}
                </div>
                <p className="support-copy">{job.insight}</p>
                <div className="mini-stats">
                  <span>{job.applicants} applicants</span>
                </div>
                {job.match != null ? (
                  <div className="linkedin-match-bar" aria-hidden="true">
                    <div style={{ width: `${job.match}%` }} />
                  </div>
                ) : null}
                <div className="button-row wrap-actions">
                  <button
                    className="primary-button"
                    type="button"
                    onClick={() => linkedinApplyAction(job)}
                  >
                    {job.easyApply ? 'Easy Apply' : 'Apply on LinkedIn'}
                  </button>
                  {job.linkedinUrl ? (
                    <a className="secondary-button" href={job.linkedinUrl} target="_blank" rel="noreferrer">Open posting</a>
                  ) : null}
                  <button className="secondary-button" type="button" onClick={() => pushNotice(`${job.role} at ${job.company} saved from LinkedIn.`)}>
                    <Bookmark size={16} />
                    Save
                  </button>
                </div>
              </article>
            ))}
          </section>
        </section>
      ) : null}

      {activeTab === 'tracker' ? (
        <section className="ja-tracker-panel page-stack dense">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Application tracker</p>
              <h4>Monitor applications, interviews, and follow-ups</h4>
            </div>
            <button
              className="secondary-button"
              type="button"
              disabled={busyAction === 'refreshTracker'}
              onClick={refreshTrackerAction}
            >
              {busyAction === 'refreshTracker' ? <LoaderCircle size={16} className="spin" /> : <Search size={16} />}
              Refresh tracker
            </button>
          </div>

          <section className="ja-tracker-stats hero-grid four-up" aria-label="Tracker summary">
            <article className="metric-tile accent-cobalt">
              <Briefcase size={18} />
              <strong>{applications.stats.applied}</strong>
              <span>Total applied</span>
            </article>
            <article className="metric-tile accent-amber">
              <Search size={18} />
              <strong>{applications.stats.underReview ?? Math.max(applications.stats.applied - applications.stats.interviews - applications.stats.actionNeeded, 0)}</strong>
              <span>Under review</span>
            </article>
            <article className="metric-tile accent-teal">
              <Calendar size={18} />
              <strong>{applications.stats.interviews}</strong>
              <span>Interviews</span>
            </article>
            <article className="metric-tile accent-rose">
              <AlertCircle size={18} />
              <strong>{applications.stats.actionNeeded}</strong>
              <span>Action needed</span>
            </article>
          </section>

          <nav className="ja-tracker-subnav" role="tablist" aria-label="Tracker views">
            {trackerTabConfig.map((tab) => {
              const Icon = tab.icon
              const count =
                tab.key === 'all' ? applications.all.length
                  : tab.key === 'interviews' ? applications.interviews.length
                    : tab.key === 'actionNeeded' ? applications.actionNeeded.length
                      : null

              return (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={trackerTab === tab.key}
                  className={`ja-tracker-subnav-item${trackerTab === tab.key ? ' active' : ''}`}
                  onClick={() => setTrackerTab(tab.key)}
                >
                  <Icon size={15} aria-hidden="true" />
                  <span>{tab.label}</span>
                  {count != null ? <span className="ja-tracker-subnav-count">{count}</span> : null}
                </button>
              )
            })}
          </nav>

          {trackerTab !== 'stats' ? (
            <div className="ja-tracker-filters form-grid">
              <label>
                Search
                <input
                  value={trackerSearch}
                  onChange={(event) => setTrackerSearch(event.target.value)}
                  placeholder="Role, company, portal, status…"
                />
              </label>
              <label>
                Status
                <select value={trackerStatusFilter} onChange={(event) => setTrackerStatusFilter(event.target.value)}>
                  <option value="all">All statuses</option>
                  {TRACKER_STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
              </label>
              <label>
                Portal
                <select value={trackerPortalFilter} onChange={(event) => setTrackerPortalFilter(event.target.value)}>
                  <option value="all">All portals</option>
                  {trackerPortalOptions.map((portal) => (
                    <option key={portal} value={portal}>{portal}</option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}

          {trackerTab === 'stats' ? (
            <article className="glass-card ja-tracker-stats-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Performance metrics</p>
                  <h4>Application statistics</h4>
                </div>
              </div>
              <div className="ja-tracker-stat-grid">
                <article className="ja-tracker-stat-box accent-cobalt">
                  <strong>{applications.stats.responseRate ?? applications.stats.conversion}%</strong>
                  <span>Response rate</span>
                </article>
                <article className="ja-tracker-stat-box accent-teal">
                  <strong>{applications.stats.avgMatchScore ?? avgMatchScore}%</strong>
                  <span>Avg match score</span>
                </article>
                <article className="ja-tracker-stat-box accent-amber">
                  <strong>{applications.stats.avgResponseTime ?? '—'}</strong>
                  <span>Avg response time</span>
                </article>
                <article className="ja-tracker-stat-box accent-violet">
                  <strong className="metric-text">{applications.stats.bestPlatform ?? '—'}</strong>
                  <span>Best platform</span>
                </article>
                <article className="ja-tracker-stat-box accent-cobalt">
                  <strong>{applications.stats.totalTracked ?? applications.all.length}</strong>
                  <span>Total tracked</span>
                </article>
                <article className="ja-tracker-stat-box accent-rose">
                  <strong>{applications.stats.underReview ?? 0}</strong>
                  <span>Under review</span>
                </article>
              </div>
            </article>
          ) : (
            <>
              {trackerTab === 'interviews' ? (
                <div className="ja-tracker-banner success" role="status">
                  <Calendar size={18} aria-hidden="true" />
                  <div>
                    <strong>{applications.interviews.length} interview / offer row{applications.interviews.length === 1 ? '' : 's'}</strong>
                    <p>Update status to Interview or Offer when recruiters respond. Check email for calendar invites.</p>
                  </div>
                </div>
              ) : null}

              {trackerTab === 'actionNeeded' ? (
                <div className="ja-tracker-banner warning" role="status">
                  <AlertCircle size={18} aria-hidden="true" />
                  <div>
                    <strong>{applications.actionNeeded.length} application{applications.actionNeeded.length === 1 ? '' : 's'} need attention</strong>
                    <p>Includes Action Needed, Tailoring, and Failed rows — schedule a follow-up or update status.</p>
                  </div>
                </div>
              ) : null}

              {trackerTab === 'all' && applications.all.length ? (
                <div className="ja-tracker-inline-stats">
                  <article className="ja-stat-card">
                    <strong>{currentTrackerRows.length}</strong>
                    <span>Showing now</span>
                  </article>
                  <article className="ja-stat-card">
                    <strong>{applications.stats.totalTracked ?? applications.all.length}</strong>
                    <span>Total tracked</span>
                  </article>
                  <article className="ja-stat-card">
                    <strong>{applications.stats.responseRate ?? applications.stats.conversion}%</strong>
                    <span>Response rate</span>
                  </article>
                </div>
              ) : null}

              {currentTrackerRows.length === 0 ? (
                <article className="glass-card ja-tracker-empty">
                  <FileSearch size={28} aria-hidden="true" />
                  <h4>No applications in this view</h4>
                  <p>Adjust filters, refresh the tracker, or apply from Results / LinkedIn to populate rows.</p>
                </article>
              ) : (
                <div className="ja-tracker-list">
                  {currentTrackerRows.map((item) => {
                    const statusTone = getTrackerStatusTone(item.status)
                    const cardKey = item.id != null ? `app-${item.id}` : `${item.role}-${item.company}-${item.updated}`
                    return (
                      <article
                        key={cardKey}
                        className="ja-tracker-card glass-card"
                      >
                        <div className="ja-tracker-card-header">
                          <div className="ja-tracker-card-title">
                            <h4>{item.role}</h4>
                            <p>{item.company}</p>
                          </div>
                          <div className="ja-tracker-card-status-block">
                            <span className={`ja-tracker-status ${statusTone}`}>{item.status}</span>
                            <time className="ja-tracker-date">{item.date || item.updated}</time>
                          </div>
                        </div>

                        {item.stage ? <p className="ja-tracker-stage">{item.stage}</p> : null}
                        {item.attemptDetail ? <p className="ja-tracker-stage muted">{item.attemptDetail}</p> : null}

                        <div className="ja-tracker-meta">
                          {item.portal ? (
                            <span className="ja-tracker-pill portal">
                              <Globe size={12} aria-hidden="true" />
                              {item.portal}
                            </span>
                          ) : null}
                          {item.match != null ? (
                            <span className="ja-tracker-pill match">
                              <TrendingUp size={12} aria-hidden="true" />
                              {item.match}% match
                            </span>
                          ) : null}
                          {item.attemptStatus ? (
                            <span className="ja-tracker-pill portal">
                              {item.attemptStatus}
                            </span>
                          ) : null}
                        </div>

                        <label className="ja-tracker-status-select">
                          Update status
                          <select
                            value={item.status}
                            disabled={!item.id || String(busyAction).startsWith('status-')}
                            onChange={(event) => updateTrackerStatusAction(item, event.target.value)}
                          >
                            {TRACKER_STATUS_OPTIONS.map((status) => (
                              <option key={status} value={status}>{status}</option>
                            ))}
                          </select>
                        </label>

                        <div className="ja-tracker-footer">
                          <div className="ja-tracker-action-copy">
                            <span>Applied {item.date || item.updated}</span>
                            {item.action ? <span>{item.action}</span> : null}
                          </div>
                          <div className="button-row wrap-actions ja-tracker-actions">
                            <button
                              className="secondary-button"
                              type="button"
                              disabled={!item.id || busyAction === `followup-${item.id}`}
                              onClick={() => followUpAction(item)}
                            >
                              {busyAction === `followup-${item.id}` ? <LoaderCircle size={15} className="spin" /> : <MessageSquare size={15} />}
                              Follow up
                            </button>
                            {item.confirmationUrl ? (
                              <button className="secondary-button" type="button" onClick={() => openConfirmationAction(item)}>
                                <ExternalLink size={15} />
                                Confirmation
                              </button>
                            ) : null}
                            <button className="primary-button" type="button" onClick={() => viewPostingAction(item)}>
                              <ExternalLink size={15} />
                              View posting
                            </button>
                          </div>
                        </div>
                      </article>
                    )
                  })}
                </div>
              )}
            </>
          )}
        </section>
      ) : null}

      <section className="dual-grid">
        <article className="glass-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Job automation features</p>
              <h4>What you can do</h4>
            </div>
          </div>
          <ul className="check-list">
            <li>Manage your candidate profile with resume upload and AI parsing.</li>
            <li>Configure job search across multiple job boards and portals.</li>
            <li>Add and manage job portal credentials and automation settings.</li>
            <li>View and analyze job matches with automated scoring.</li>
            <li>Analyze your CV against job descriptions for fit scoring.</li>
            <li>Track LinkedIn jobs and application workflow status.</li>
            <li>Monitor applications, interviews, and follow-up actions.</li>
          </ul>
        </article>

        <article className="glass-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Automation best practices</p>
              <h4>Optimize your workflow</h4>
            </div>
          </div>
          <ul className="check-list">
            <li>Keep your resume updated and upload the active version regularly.</li>
            <li>Configure multiple job portals for maximum exposure and applications.</li>
            <li>Review AI-generated CV analysis and update your profile accordingly.</li>
            <li>Set realistic search criteria to avoid low-match applications.</li>
            <li>Track all applications and follow up within 3-5 days.</li>
            <li>Monitor interview pipeline and prepare for upcoming calls.</li>
            <li>Use automation settings to balance speed with quality matches.</li>
          </ul>
        </article>
      </section>
    </div>
  )
}