export const LINKEDIN_TABS = [
  { key: 'discover', label: 'Discover', icon: 'search' },
  { key: 'paste', label: 'Paste Profiles', icon: 'link' },
  { key: 'apis', label: 'API Sources', icon: 'api' },
  { key: 'outreach', label: 'AI Outreach', icon: 'message' },
  { key: 'tracker', label: 'Sequence Tracker', icon: 'timeline' },
  { key: 'settings', label: 'Settings', icon: 'settings' },
]

export const DEFAULT_TARGET_COMPANIES = [
  'TEKsystems',
  'Infosys BPM',
  'Robert Half',
  'Apex Group',
  'Cognizant',
  'TCS',
  'Wipro',
  'HCL Tech',
  'Capgemini',
  'Accenture',
  'Randstad',
  'Insight Global',
]

export const DEFAULT_TECH_KEYWORDS = [
  'Java',
  'Spring Boot',
  'Python',
  '.NET',
  'React',
  'AWS',
  'DevOps',
  'Salesforce',
  'SAP',
  'Data Engineer',
  'Full Stack',
  'Cybersecurity',
]

export const COMPANY_AVATAR_COLORS = {
  TEKsystems: ['#dbeafe', '#1e40af'],
  'Infosys BPM': ['#d1fae5', '#065f46'],
  Infosys: ['#d1fae5', '#065f46'],
  Cognizant: ['#fef3c7', '#92400e'],
  Wipro: ['#ede9fe', '#5b21b6'],
  TCS: ['#fee2e2', '#991b1b'],
  Capgemini: ['#e0f2fe', '#0369a1'],
  Accenture: ['#f0fdf4', '#166534'],
  'Robert Half': ['#fff7ed', '#c2410c'],
  'HCL Tech': ['#fdf4ff', '#7e22ce'],
}

export const MESSAGE_TYPE_PROMPTS = {
  connect: 'Write a LinkedIn connection request to a Java Technical Recruiter. Mention C2C availability and Spring Boot skills. Keep under 300 characters.',
  inmail: 'Write a LinkedIn InMail to a technical recruiter about a Senior Java Developer available for C2C contract roles.',
  followup: 'Write a polite 3-day follow-up LinkedIn message about a Java Developer who is still available.',
  hotlist: 'Write a hotlist pitch email for a bench Java developer with Spring Boot, AWS, immediate availability.',
  thankyou: 'Write a thank-you note after a recruiter connected and reviewed a candidate profile.',
  resume: 'Write a message submitting a Senior Java Developer resume for an open C2C requirement.',
}

export const MESSAGE_TYPE_SUBJECTS = {
  connect: 'Let us connect — Java Developer available C2C',
  inmail: 'Senior Java Developer available — C2C — Immediate start',
  followup: 'Following up — Java Developer still available',
  hotlist: 'Java Developer Hotlist — Available Now | C2C',
  thankyou: 'Thank you for connecting!',
  resume: 'Resume — Senior Java Developer | C2C | Immediate',
}

export const MESSAGE_TYPE_BODIES = {
  connect: `<p>Hi {{recruiter_name}},</p><p>I came across your profile and noticed your expertise in IT staffing at {{company}}. I am a Senior Java/Spring Boot Developer with 8 years of experience, actively available for C2C contract roles.</p><p>Would love to connect and explore any potential opportunities!</p><p>Best,<br>{{candidate_name}}</p>`,
  inmail: `<p>Hi {{recruiter_name}},</p><p>Hope you are having a great week! I wanted to reach out because I believe my background aligns well with the types of roles you typically fill at {{company}}.</p><p>I am a Senior Java Developer with expertise in {{tech_stack}}, immediately available for contract opportunities in {{location}}.</p><p>Would you be open to a quick 10-minute call? Happy to share my resume.</p><p>Best regards,<br>{{candidate_name}}</p>`,
  followup: `<p>Hi {{recruiter_name}},</p><p>Just following up on my earlier message. Our Java Developer remains available and is actively interviewing — wanted to touch base before this window closes.</p><p>Would love to hear if you have any matching C2C requirements.</p><p>{{candidate_name}}</p>`,
  hotlist: `<p>Hi {{recruiter_name}},</p><p>I am reaching out with a strong Java Developer currently on our bench:</p><ul><li>Skills: {{tech_stack}}</li><li>Experience: 8+ years</li><li>Location: {{location}}</li><li>Availability: Immediate</li><li>Rate: $85-90/hr C2C</li></ul><p>Would this profile be a fit for any of your open requirements?</p><p>{{candidate_name}} | {{company}}</p>`,
  thankyou: `<p>Hi {{recruiter_name}},</p><p>Thank you so much for connecting and taking the time to review our candidate's profile. We appreciate your responsiveness and look forward to working together!</p><p>Best,<br>{{candidate_name}}</p>`,
  resume: `<p>Hi {{recruiter_name}},</p><p>As discussed, please find attached the resume of our Senior Java Developer. Key highlights:</p><ul><li>8+ years in enterprise Java, Spring Boot, Microservices</li><li>Cloud experience: AWS, Docker, Kubernetes</li><li>Available immediately · C2C · {{location}}</li></ul><p>Please let me know if you need any additional information.</p><p>Best,<br>{{candidate_name}}</p>`,
}

export const MERGE_TAGS = [
  '{{recruiter_name}}',
  '{{company}}',
  '{{tech_stack}}',
  '{{candidate_name}}',
  '{{availability}}',
  '{{location}}',
  '{{rate}}',
]

export const OUTREACH_ANALYTICS = {
  openRate: 36,
  replyRate: 26,
  avgTouches: 4.2,
  avgReplyDays: '2.1d',
}

export const TOP_COMPANY_PERFORMANCE = [
  { company: 'TEKsystems', pct: 78 },
  { company: 'Infosys', pct: 62 },
  { company: 'Cognizant', pct: 54 },
  { company: 'Wipro', pct: 41 },
]

export const DEFAULT_URL_QUEUE = [
  { id: 'q1', url: 'linkedin.com/company/teksystems/people/', status: 'Queued' },
  { id: 'q2', url: 'linkedin.com/company/infosys/people/', status: 'Queued' },
  { id: 'q3', url: 'linkedin.com/company/wipro/people/', status: 'Pending' },
]

export function avatarColorsForCompany(company) {
  return COMPANY_AVATAR_COLORS[company] ?? ['#f3f4f6', '#374151']
}

export function buildSearchPreview(activeTechs) {
  const techs = Array.from(activeTechs)
  if (!techs.length) {
    return '"Recruiter"'
  }
  return `"Recruiter" AND (${techs.map((tech) => `"${tech}"`).join(' OR ')})`
}

export function filterRecruiters(recruiters, query) {
  const text = query.trim().toLowerCase()
  if (!text) {
    return recruiters
  }
  return recruiters.filter(
    (rec) =>
      rec.name.toLowerCase().includes(text) ||
      rec.company.toLowerCase().includes(text) ||
      (rec.techs ?? []).join(' ').toLowerCase().includes(text),
  )
}

export function sortRecruiters(recruiters, sortBy) {
  const list = [...recruiters]
  if (sortBy === 'conn') {
    list.sort((a, b) => String(a.conn).localeCompare(String(b.conn)))
  } else if (sortBy === 'company') {
    list.sort((a, b) => a.company.localeCompare(b.company))
  } else {
    list.sort((a, b) => (b.match ?? 0) - (a.match ?? 0))
  }
  return list
}

export function parseLinkedInPasteUrls(raw) {
  return Array.from(new Set(String(raw ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.includes('linkedin.com'))))
}

export function parseLinkedInCsvUrls(raw) {
  const matches = String(raw ?? '').match(/(?:https?:\/\/)?(?:[\w-]+\.)?linkedin\.com\/[^\s,"']+/gi) ?? []
  return Array.from(new Set(matches.map((value) => {
    const url = value.replace(/[)\].;]+$/, '')
    return /^https?:\/\//i.test(url) ? url : `https://${url}`
  })))
}

export function mergeCompanyLists(workspaceCompanies = []) {
  const seen = new Set()
  const merged = []
  ;[...DEFAULT_TARGET_COMPANIES, ...workspaceCompanies].forEach((company) => {
    if (!seen.has(company)) {
      seen.add(company)
      merged.push(company)
    }
  })
  return merged
}

export function mergeTechLists(workspaceTechs = []) {
  const seen = new Set()
  const merged = []
  ;[...DEFAULT_TECH_KEYWORDS, ...workspaceTechs].forEach((tech) => {
    if (!seen.has(tech)) {
      seen.add(tech)
      merged.push(tech)
    }
  })
  return merged
}

export function sequenceStatusClass(status) {
  if (status === 'sent' || status === 'replied') {
    return 'seq-sent'
  }
  if (status === 'pending') {
    return 'seq-pending'
  }
  if (status === 'scheduled') {
    return 'seq-scheduled'
  }
  return 'seq-pending'
}

export function formatApiUsageRow(row) {
  if (row.limit) {
    return `${row.used.toLocaleString()} / ${row.limit.toLocaleString()}`
  }
  return row.used.toLocaleString()
}

export const API_SOURCE_KEY_MAP = {
  'Apollo.io': 'apollo',
  'Hunter.io': 'hunter',
  RocketReach: 'rocketreach',
  Lusha: 'lusha',
}

export function apiKeyFieldForSource(sourceName) {
  return API_SOURCE_KEY_MAP[sourceName] ?? null
}

export function normalizeRecruiterIds(ids) {
  return Array.from(ids)
    .map((id) => (typeof id === 'number' ? id : Number.parseInt(String(id), 10)))
    .filter((id) => !Number.isNaN(id))
}

export function mergeRecruiters(existing = [], incoming = []) {
  const map = new Map(existing.map((rec) => [rec.id, rec]))
  incoming.forEach((rec) => {
    if (rec?.id != null) {
      map.set(rec.id, rec)
    }
  })
  return Array.from(map.values())
}

export function formatToneForApi(tone) {
  const labels = {
    professional: 'Professional',
    friendly: 'Friendly',
    concise: 'Concise (under 100 words)',
    enthusiastic: 'Enthusiastic',
  }
  return labels[tone] ?? tone
}

export function buildQuickConnectBody(rec) {
  const techs = (rec.techs ?? []).join(', ')
  return `<p>Hi ${rec.name},</p><p>I noticed your work in IT staffing at ${rec.company} and would love to connect. I have a Senior Java Developer with ${techs || '{{tech_stack}}'} expertise available immediately for C2C contract roles.</p><p>Would love to connect and share more details!</p><p>Best regards,<br>{{candidate_name}}</p>`
}

export function findRecruiterByName(recruiters, name) {
  return recruiters.find((rec) => rec.name === name)
}
